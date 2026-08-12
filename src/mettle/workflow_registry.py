from __future__ import annotations

from collections.abc import Callable
from datetime import date
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from secrets import token_urlsafe
from threading import Lock

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mettle.communication import Recipient, RecordingMessenger
from mettle.domain import InspectionNotice, Trade
from mettle.evidence import EvidenceAssessment, EvidenceSampleNotFound, assess_sample
from mettle.packet import PacketRecord, PacketStatus, render_packet_pdf
from mettle.workflow import (
    RecoveryWorkflowSession,
    WorkflowConfigurationError,
    WorkflowSnapshot,
    WorkflowStateError,
)


NoticeExtractor = Callable[[str], InspectionNotice]
PhotoAssessor = Callable[..., EvidenceAssessment]


class WorkflowNotFound(RuntimeError):
    """Raised when a workflow identifier is unknown to this process."""


class WorkflowConflict(RuntimeError):
    """Raised when a replay changes the payload or the workflow state."""


class WorkflowCapacityReached(RuntimeError):
    """Raised when the bounded local registry is full."""


class EvidenceSubmissionError(RuntimeError):
    """Raised when evidence cannot be assessed for the selected workflow."""


class PacketNotReady(RuntimeError):
    """Raised when a packet cannot be prepared from incomplete evidence."""


class PacketNotApproved(RuntimeError):
    """Raised when a packet operation requires final contractor approval."""


class IntakeProvider(StrEnum):
    LOCAL = "local"
    BEDROCK = "bedrock"


class WorkflowRosterEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    trade: Trade
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")


class CreateWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    notice_text: str = Field(min_length=1, max_length=100_000)
    intake_provider: IntakeProvider = IntakeProvider.LOCAL
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


class SubmitEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    citation_id: str = Field(min_length=1, max_length=50)
    sample_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9_]+$",
    )


class SubmitPhotoEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    citation_id: str = Field(min_length=1, max_length=50)


class AgentCorePhotoEvidenceRequest(SubmitPhotoEvidenceRequest):
    image_base64: str = Field(min_length=4, max_length=6_700_000)


class PreparePacketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ApprovePacketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    approval_id: str = Field(min_length=1, max_length=64)
    decision: str = Field(min_length=3, max_length=500)


class WorkflowEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    intake_provider: IntakeProvider
    snapshot: WorkflowSnapshot
    evidence: list[EvidenceAssessment] = Field(default_factory=list)
    packet: PacketRecord | None = None


class _WorkflowEntry:
    def __init__(
        self,
        session: RecoveryWorkflowSession,
        snapshot: WorkflowSnapshot,
        intake_provider: IntakeProvider,
    ) -> None:
        self.session = session
        self.snapshot = snapshot
        self.intake_provider = intake_provider
        self.lock = Lock()
        self.resume_replays: dict[str, tuple[str, WorkflowEnvelope]] = {}
        self.evidence: list[EvidenceAssessment] = []
        self.evidence_replays: dict[str, tuple[str, WorkflowEnvelope]] = {}
        self.uploaded_photos: dict[str, bytes] = {}
        self.packet: PacketRecord | None = None
        self.packet_prepare_replays: dict[str, WorkflowEnvelope] = {}
        self.packet_approval_replays: dict[str, tuple[str, WorkflowEnvelope]] = {}


def _fingerprint(model: BaseModel) -> str:
    canonical = model.model_dump_json(exclude_none=False)
    return sha256(canonical.encode("utf-8")).hexdigest()


class WorkflowRegistry:
    """Bounded, process-local owner for stateful Strands workflow sessions."""

    def __init__(
        self,
        *,
        capacity: int = 50,
        bedrock_intake: NoticeExtractor | None = None,
        photo_assessor: PhotoAssessor | None = None,
    ) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._bedrock_intake = bedrock_intake
        self._photo_assessor = photo_assessor
        self._lock = Lock()
        self._entries: dict[str, _WorkflowEntry] = {}
        self._create_replays: dict[str, tuple[str, str, WorkflowEnvelope]] = {}

    @property
    def bedrock_enabled(self) -> bool:
        return self._bedrock_intake is not None

    @property
    def vision_enabled(self) -> bool:
        return self._photo_assessor is not None

    @staticmethod
    def _effective_citation(entry: _WorkflowEntry, citation_id: str):
        notice = entry.snapshot.notice
        if notice is None:
            raise EvidenceSubmissionError("workflow notice is not available")
        citation = next(
            (item for item in notice.citations if item.citation_id == citation_id),
            None,
        )
        if citation is None:
            raise EvidenceSubmissionError("citation does not belong to this workflow")
        if not citation.evidence_requirements and entry.snapshot.contractor_decision:
            return citation.model_copy(
                update={"evidence_requirements": [entry.snapshot.contractor_decision]}
            )
        return citation

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
                existing_fingerprint, workflow_id, envelope = replay
                if existing_fingerprint != fingerprint:
                    raise WorkflowConflict(
                        "idempotency key was already used with a different workflow request"
                    )
                return envelope.model_copy(deep=True), True

            if len(self._entries) >= self._capacity:
                raise WorkflowCapacityReached("local workflow capacity has been reached")

            roster = {
                item.trade: Recipient(name=item.name, phone=item.phone)
                for item in payload.roster
            }
            notice_extractor: NoticeExtractor | None = None
            if payload.intake_provider is IntakeProvider.BEDROCK:
                notice_extractor = self._bedrock_intake
                if notice_extractor is None:
                    raise WorkflowConfigurationError(
                        "live Bedrock intake is not enabled on this server"
                    )
            session = RecoveryWorkflowSession(
                notice_text=payload.notice_text,
                as_of=payload.as_of,
                roster=roster,
                messenger=RecordingMessenger(),
                **({"notice_extractor": notice_extractor} if notice_extractor else {}),
            )
            snapshot = session.start()
            workflow_id = token_urlsafe(12)
            self._entries[workflow_id] = _WorkflowEntry(
                session,
                snapshot,
                payload.intake_provider,
            )
            envelope = self._envelope(workflow_id, self._entries[workflow_id])
            self._create_replays[idempotency_key] = (
                fingerprint,
                workflow_id,
                envelope,
            )
            return envelope, False

    def get(self, workflow_id: str) -> WorkflowEnvelope:
        with self._lock:
            entry = self._entries.get(workflow_id)
            if entry is None:
                raise WorkflowNotFound("workflow does not exist")
            return self._envelope(workflow_id, entry)

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
                existing_fingerprint, envelope = replay
                if existing_fingerprint != fingerprint:
                    raise WorkflowConflict(
                        "idempotency key was already used with a different resume request"
                    )
                return envelope.model_copy(deep=True)

            try:
                snapshot = entry.session.resume(
                    interrupt_id=payload.interrupt_id,
                    decision=payload.decision,
                )
            except WorkflowStateError as exc:
                raise WorkflowConflict(str(exc)) from exc
            entry.snapshot = snapshot
            envelope = self._envelope(workflow_id, entry)
            entry.resume_replays[idempotency_key] = (fingerprint, envelope)
            return envelope

    def submit_evidence(
        self,
        workflow_id: str,
        payload: SubmitEvidenceRequest,
        *,
        idempotency_key: str,
    ) -> WorkflowEnvelope:
        with self._lock:
            entry = self._entries.get(workflow_id)
        if entry is None:
            raise WorkflowNotFound("workflow does not exist")

        fingerprint = _fingerprint(payload)
        with entry.lock:
            replay = entry.evidence_replays.get(idempotency_key)
            if replay is not None:
                existing_fingerprint, envelope = replay
                if existing_fingerprint != fingerprint:
                    raise WorkflowConflict(
                        "idempotency key was already used with different evidence"
                    )
                return envelope.model_copy(deep=True)

            effective_citation = self._effective_citation(entry, payload.citation_id)
            try:
                assessment = assess_sample(
                    citation=effective_citation,
                    sample_id=payload.sample_id,
                    assessment_id=f"evidence-{token_urlsafe(9)}",
                )
            except EvidenceSampleNotFound as exc:
                raise EvidenceSubmissionError(str(exc)) from exc
            entry.evidence.append(assessment)
            envelope = self._envelope(workflow_id, entry)
            entry.evidence_replays[idempotency_key] = (fingerprint, envelope)
            return envelope

    def submit_photo_evidence(
        self,
        workflow_id: str,
        payload: SubmitPhotoEvidenceRequest,
        *,
        image: bytes,
        idempotency_key: str,
    ) -> WorkflowEnvelope:
        with self._lock:
            entry = self._entries.get(workflow_id)
        if entry is None:
            raise WorkflowNotFound("workflow does not exist")
        if self._photo_assessor is None:
            raise WorkflowConfigurationError("live photo assessment is not enabled")

        fingerprint = sha256(
            payload.model_dump_json().encode("utf-8") + b"\0" + image
        ).hexdigest()
        with entry.lock:
            replay = entry.evidence_replays.get(idempotency_key)
            if replay is not None:
                existing_fingerprint, envelope = replay
                if existing_fingerprint != fingerprint:
                    raise WorkflowConflict(
                        "idempotency key was already used with different evidence"
                    )
                return envelope.model_copy(deep=True)

            citation = self._effective_citation(entry, payload.citation_id)
            assessment_id = f"evidence-{token_urlsafe(9)}"
            assessment = self._photo_assessor(
                citation=citation,
                image=image,
                assessment_id=assessment_id,
            )
            entry.evidence.append(assessment)
            entry.uploaded_photos[assessment_id] = bytes(image)
            envelope = self._envelope(workflow_id, entry)
            entry.evidence_replays[idempotency_key] = (fingerprint, envelope)
            return envelope

    def prepare_packet(
        self,
        workflow_id: str,
        *,
        idempotency_key: str,
    ) -> WorkflowEnvelope:
        with self._lock:
            entry = self._entries.get(workflow_id)
        if entry is None:
            raise WorkflowNotFound("workflow does not exist")
        with entry.lock:
            replay = entry.packet_prepare_replays.get(idempotency_key)
            if replay is not None:
                return replay.model_copy(deep=True)
            if entry.packet is not None:
                raise WorkflowConflict("packet has already been prepared")
            notice = entry.snapshot.notice
            plan = entry.snapshot.plan
            if notice is None or plan is None:
                raise PacketNotReady("workflow notice and plan are not available")
            latest = {item.citation_id: item for item in entry.evidence}
            missing = [
                citation.citation_id
                for citation in notice.citations
                if latest.get(citation.citation_id) is None
                or latest[citation.citation_id].status.value != "accepted"
            ]
            if missing:
                raise PacketNotReady(
                    f"accepted evidence is required for citation(s): {', '.join(missing)}"
                )
            entry.packet = PacketRecord(
                packet_id=f"packet-{token_urlsafe(9)}",
                status=PacketStatus.AWAITING_APPROVAL,
                prepared_on=plan.as_of,
                citations_total=len(notice.citations),
                citations_ready=len(notice.citations),
                approval_id=f"approval-{token_urlsafe(9)}",
            )
            envelope = self._envelope(workflow_id, entry)
            entry.packet_prepare_replays[idempotency_key] = envelope
            return envelope

    def approve_packet(
        self,
        workflow_id: str,
        payload: ApprovePacketRequest,
        *,
        idempotency_key: str,
    ) -> WorkflowEnvelope:
        with self._lock:
            entry = self._entries.get(workflow_id)
        if entry is None:
            raise WorkflowNotFound("workflow does not exist")
        fingerprint = _fingerprint(payload)
        with entry.lock:
            replay = entry.packet_approval_replays.get(idempotency_key)
            if replay is not None:
                existing_fingerprint, envelope = replay
                if existing_fingerprint != fingerprint:
                    raise WorkflowConflict(
                        "idempotency key was already used with a different approval"
                    )
                return envelope.model_copy(deep=True)
            packet = entry.packet
            if packet is None:
                raise PacketNotReady("packet has not been prepared")
            if packet.status is not PacketStatus.AWAITING_APPROVAL:
                raise WorkflowConflict("packet is not awaiting approval")
            if payload.approval_id != packet.approval_id:
                raise WorkflowConflict("approval does not belong to this packet")
            decision = " ".join(payload.decision.split())
            entry.packet = packet.model_copy(
                update={
                    "status": PacketStatus.APPROVED,
                    "approval_decision": decision,
                }
            )
            envelope = self._envelope(workflow_id, entry)
            entry.packet_approval_replays[idempotency_key] = (
                fingerprint,
                envelope,
            )
            return envelope

    def render_packet(self, workflow_id: str, *, evidence_dir: Path) -> bytes:
        with self._lock:
            entry = self._entries.get(workflow_id)
        if entry is None:
            raise WorkflowNotFound("workflow does not exist")
        with entry.lock:
            notice = entry.snapshot.notice
            plan = entry.snapshot.plan
            packet = entry.packet
            if packet is None or packet.status is not PacketStatus.APPROVED:
                raise PacketNotApproved(
                    "contractor approval is required before download"
                )
            if notice is None or plan is None:
                raise PacketNotReady("workflow notice and plan are not available")
            return render_packet_pdf(
                notice=notice,
                plan=plan,
                evidence=[item.model_copy(deep=True) for item in entry.evidence],
                deliveries=list(entry.snapshot.deliveries),
                packet=packet,
                evidence_dir=evidence_dir,
                uploaded_photos=dict(entry.uploaded_photos),
            )

    @staticmethod
    def _envelope(workflow_id: str, entry: _WorkflowEntry) -> WorkflowEnvelope:
        return WorkflowEnvelope(
            workflow_id=workflow_id,
            intake_provider=entry.intake_provider,
            snapshot=entry.snapshot.model_copy(deep=True),
            evidence=[item.model_copy(deep=True) for item in entry.evidence],
            packet=entry.packet.model_copy(deep=True) if entry.packet else None,
        )
