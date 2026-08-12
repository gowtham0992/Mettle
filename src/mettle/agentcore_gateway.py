from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from threading import Lock
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from mettle.agentcore_client import AgentCoreDataClient, invoke_json
from mettle.agents.bedrock import BedrockIntakeError
from mettle.workflow import WorkflowConfigurationError
from mettle.workflow_registry import (
    CreateWorkflowRequest,
    ResumeWorkflowRequest,
    WorkflowCapacityReached,
    WorkflowConflict,
    WorkflowEnvelope,
    WorkflowNotFound,
)


class AgentCoreGatewayError(RuntimeError):
    """Raised when the deployed runtime cannot complete a valid operation."""


@dataclass
class _CreateAttempt:
    fingerprint: str
    session_id: str
    envelope: WorkflowEnvelope | None = None


@dataclass
class _CloudWorkflow:
    session_id: str
    envelope: WorkflowEnvelope
    resume_replays: dict[str, tuple[str, WorkflowEnvelope]] = field(default_factory=dict)


def _fingerprint(model: BaseModel) -> str:
    canonical = model.model_dump_json(exclude_none=False)
    return sha256(canonical.encode("utf-8")).hexdigest()


class AgentCoreWorkflowGateway:
    """Bounded server-side owner for deployed AgentCore workflow sessions.

    The lock deliberately spans each network invocation. This local demo has one
    operator, and serializing calls prevents concurrent retries from spending
    twice or advancing the same stateful AgentCore session out of order.
    """

    def __init__(
        self,
        *,
        client: AgentCoreDataClient,
        runtime_arn: str,
        capacity: int = 50,
    ) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        if not runtime_arn.startswith("arn:aws:bedrock-agentcore:"):
            raise ValueError("runtime_arn must be an Amazon Bedrock AgentCore ARN")
        self._client = client
        self._runtime_arn = runtime_arn
        self._capacity = capacity
        self._lock = Lock()
        self._create_attempts: dict[str, _CreateAttempt] = {}
        self._workflows: dict[str, _CloudWorkflow] = {}

    def create(
        self,
        payload: CreateWorkflowRequest,
        *,
        idempotency_key: str,
    ) -> tuple[WorkflowEnvelope, bool]:
        fingerprint = _fingerprint(payload)
        with self._lock:
            attempt = self._create_attempts.get(idempotency_key)
            if attempt is not None and attempt.fingerprint != fingerprint:
                raise WorkflowConflict(
                    "idempotency key was already used with a different workflow request"
                )
            if attempt is not None and attempt.envelope is not None:
                return attempt.envelope.model_copy(deep=True), True
            if attempt is None:
                if len(self._create_attempts) >= self._capacity:
                    raise WorkflowCapacityReached(
                        "AgentCore workflow capacity has been reached"
                    )
                attempt = _CreateAttempt(
                    fingerprint=fingerprint,
                    session_id=f"mettle-{uuid4().hex}",
                )
                self._create_attempts[idempotency_key] = attempt

            result = self._invoke(
                session_id=attempt.session_id,
                payload={
                    "operation": "start",
                    "idempotency_key": idempotency_key,
                    "payload": payload.model_dump(mode="json"),
                },
            )
            envelope = self._parse_result(result)
            existing = self._workflows.get(envelope.workflow_id)
            if existing is not None and existing.session_id != attempt.session_id:
                raise AgentCoreGatewayError(
                    "AgentCore returned a workflow identifier owned by another session"
                )
            attempt.envelope = envelope
            self._workflows[envelope.workflow_id] = _CloudWorkflow(
                session_id=attempt.session_id,
                envelope=envelope,
            )
            return envelope.model_copy(deep=True), bool(result.get("replayed"))

    def get(self, workflow_id: str) -> WorkflowEnvelope:
        with self._lock:
            workflow = self._workflows.get(workflow_id)
            if workflow is None:
                raise WorkflowNotFound("AgentCore workflow does not exist on this server")
            return workflow.envelope.model_copy(deep=True)

    def resume(
        self,
        workflow_id: str,
        payload: ResumeWorkflowRequest,
        *,
        idempotency_key: str,
    ) -> WorkflowEnvelope:
        fingerprint = _fingerprint(payload)
        with self._lock:
            workflow = self._workflows.get(workflow_id)
            if workflow is None:
                raise WorkflowNotFound("AgentCore workflow does not exist on this server")
            replay = workflow.resume_replays.get(idempotency_key)
            if replay is not None:
                existing_fingerprint, envelope = replay
                if existing_fingerprint != fingerprint:
                    raise WorkflowConflict(
                        "idempotency key was already used with a different resume request"
                    )
                return envelope.model_copy(deep=True)

            result = self._invoke(
                session_id=workflow.session_id,
                payload={
                    "operation": "resume",
                    "idempotency_key": idempotency_key,
                    "workflow_id": workflow_id,
                    "payload": payload.model_dump(mode="json"),
                },
            )
            envelope = self._parse_result(result)
            if envelope.workflow_id != workflow_id:
                raise AgentCoreGatewayError(
                    "AgentCore returned a different workflow identifier on resume"
                )
            workflow.envelope = envelope
            workflow.resume_replays[idempotency_key] = (fingerprint, envelope)
            return envelope.model_copy(deep=True)

    def _invoke(self, *, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return invoke_json(
                self._client,
                runtime_arn=self._runtime_arn,
                session_id=session_id,
                payload=payload,
            )
        except Exception as exc:
            raise AgentCoreGatewayError(
                "AgentCore could not be reached with the current server configuration"
            ) from exc

    @staticmethod
    def _parse_result(result: dict[str, Any]) -> WorkflowEnvelope:
        if result.get("ok") is True:
            try:
                return WorkflowEnvelope.model_validate(result.get("workflow"))
            except ValidationError as exc:
                raise AgentCoreGatewayError(
                    "AgentCore returned an invalid Mettle workflow"
                ) from exc

        error = result.get("error")
        code = error.get("code") if isinstance(error, dict) else None
        message = error.get("message") if isinstance(error, dict) else None
        safe_message = message if isinstance(message, str) else "AgentCore operation failed"
        if code == "workflow_not_found":
            raise WorkflowNotFound(safe_message)
        if code == "workflow_conflict":
            raise WorkflowConflict(safe_message)
        if code == "workflow_capacity_reached":
            raise WorkflowCapacityReached(safe_message)
        if code in {"invalid_request", "workflow_configuration_error"}:
            raise WorkflowConfigurationError(safe_message)
        if code == "bedrock_intake_failed":
            raise BedrockIntakeError(safe_message)
        raise AgentCoreGatewayError("AgentCore could not complete the operation")
