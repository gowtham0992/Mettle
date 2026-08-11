from __future__ import annotations

from datetime import date
from hashlib import sha256
from secrets import token_urlsafe
from threading import Lock

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mettle.communication import Recipient, RecordingMessenger
from mettle.domain import Trade
from mettle.workflow import (
    RecoveryWorkflowSession,
    WorkflowSnapshot,
    WorkflowStateError,
)


class WorkflowNotFound(RuntimeError):
    """Raised when a workflow identifier is unknown to this process."""


class WorkflowConflict(RuntimeError):
    """Raised when a replay changes the payload or the workflow state."""


class WorkflowCapacityReached(RuntimeError):
    """Raised when the bounded local registry is full."""


class WorkflowRosterEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    trade: Trade
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")


class CreateWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    notice_text: str = Field(min_length=1, max_length=100_000)
    as_of: date
    roster: tuple[WorkflowRosterEntry, ...] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def validate_roster(self) -> CreateWorkflowRequest:
        trades = [entry.trade for entry in self.roster]
        if len(trades) != len(set(trades)):
            raise ValueError("roster may contain only one recipient per trade")
        if not self.notice_text.strip():
            raise ValueError("notice_text must contain visible characters")
        return self


class ResumeWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    interrupt_id: str = Field(min_length=1, max_length=240)
    decision: str = Field(min_length=3, max_length=500)


class WorkflowEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    snapshot: WorkflowSnapshot


class _WorkflowEntry:
    def __init__(self, session: RecoveryWorkflowSession, snapshot: WorkflowSnapshot) -> None:
        self.session = session
        self.snapshot = snapshot
        self.lock = Lock()
        self.resume_replays: dict[str, tuple[str, WorkflowSnapshot]] = {}


def _fingerprint(model: BaseModel) -> str:
    canonical = model.model_dump_json(exclude_none=False)
    return sha256(canonical.encode("utf-8")).hexdigest()


class WorkflowRegistry:
    """Bounded, process-local owner for stateful Strands workflow sessions."""

    def __init__(self, *, capacity: int = 50) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._lock = Lock()
        self._entries: dict[str, _WorkflowEntry] = {}
        self._create_replays: dict[str, tuple[str, str]] = {}

    def create(
        self,
        payload: CreateWorkflowRequest,
        *,
        idempotency_key: str,
    ) -> tuple[WorkflowEnvelope, bool]:
        fingerprint = _fingerprint(payload)
        with self._lock:
            replay = self._create_replays.get(idempotency_key)
            if replay is not None:
                existing_fingerprint, workflow_id = replay
                if existing_fingerprint != fingerprint:
                    raise WorkflowConflict(
                        "idempotency key was already used with a different workflow request"
                    )
                entry = self._entries[workflow_id]
                return self._envelope(workflow_id, entry.snapshot), True

            if len(self._entries) >= self._capacity:
                raise WorkflowCapacityReached("local workflow capacity has been reached")

            roster = {
                item.trade: Recipient(name=item.name, phone=item.phone)
                for item in payload.roster
            }
            session = RecoveryWorkflowSession(
                notice_text=payload.notice_text,
                as_of=payload.as_of,
                roster=roster,
                messenger=RecordingMessenger(),
            )
            snapshot = session.start()
            workflow_id = token_urlsafe(12)
            self._entries[workflow_id] = _WorkflowEntry(session, snapshot)
            self._create_replays[idempotency_key] = (fingerprint, workflow_id)
            return self._envelope(workflow_id, snapshot), False

    def get(self, workflow_id: str) -> WorkflowEnvelope:
        with self._lock:
            entry = self._entries.get(workflow_id)
            if entry is None:
                raise WorkflowNotFound("workflow does not exist")
            return self._envelope(workflow_id, entry.snapshot)

    def resume(
        self,
        workflow_id: str,
        payload: ResumeWorkflowRequest,
        *,
        idempotency_key: str,
    ) -> WorkflowEnvelope:
        with self._lock:
            entry = self._entries.get(workflow_id)
        if entry is None:
            raise WorkflowNotFound("workflow does not exist")

        fingerprint = _fingerprint(payload)
        with entry.lock:
            replay = entry.resume_replays.get(idempotency_key)
            if replay is not None:
                existing_fingerprint, snapshot = replay
                if existing_fingerprint != fingerprint:
                    raise WorkflowConflict(
                        "idempotency key was already used with a different resume request"
                    )
                return self._envelope(workflow_id, snapshot)

            try:
                snapshot = entry.session.resume(
                    interrupt_id=payload.interrupt_id,
                    decision=payload.decision,
                )
            except WorkflowStateError as exc:
                raise WorkflowConflict(str(exc)) from exc
            entry.snapshot = snapshot
            entry.resume_replays[idempotency_key] = (fingerprint, snapshot)
            return self._envelope(workflow_id, snapshot)

    @staticmethod
    def _envelope(workflow_id: str, snapshot: WorkflowSnapshot) -> WorkflowEnvelope:
        return WorkflowEnvelope(
            workflow_id=workflow_id,
            snapshot=snapshot.model_copy(deep=True),
        )
