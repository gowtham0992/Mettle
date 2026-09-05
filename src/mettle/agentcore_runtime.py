from __future__ import annotations

import base64
import logging
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from mettle.agents.bedrock import BedrockIntakeError
from mettle.agents.vision import BedrockVisionError
from mettle.photo_upload import PhotoUploadError, normalize_photo
from mettle.workflow import WorkflowConfigurationError
from mettle.workflow_registry import (
    ApprovePacketRequest,
    CreateWorkflowRequest,
    EvidenceSubmissionError,
    PacketNotApproved,
    PacketNotReady,
    PreparePacketRequest,
    ReviewEvidenceRequest,
    ReviewWorkflowRequest,
    RunNextCheckRequest,
    ResumeWorkflowRequest,
    SubmitEvidenceRequest,
    AgentCorePhotoEvidenceRequest,
    SubmitPhotoEvidenceRequest,
    WorkflowCapacityReached,
    WorkflowConflict,
    WorkflowNotFound,
    WorkflowRegistry,
)


LOGGER = logging.getLogger(__name__)


class _StartInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["start"]
    idempotency_key: str = Field(
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    payload: CreateWorkflowRequest


class _RestoreInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    operation: Literal["restore"]
    workflow_id: str = Field(min_length=1, max_length=64)
    checkpoint: dict[str, Any]


class _ResumeInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["resume"]
    idempotency_key: str = Field(
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    workflow_id: str = Field(min_length=1, max_length=64)
    payload: ResumeWorkflowRequest


class _ReviewInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["review"]
    idempotency_key: str = Field(
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    workflow_id: str = Field(min_length=1, max_length=64)
    payload: ReviewWorkflowRequest


class _SubmitEvidenceInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["submit_evidence"]
    idempotency_key: str = Field(
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    workflow_id: str = Field(min_length=1, max_length=64)
    payload: SubmitEvidenceRequest


class _SubmitPhotoEvidenceInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["submit_photo_evidence"]
    idempotency_key: str = Field(
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    workflow_id: str = Field(min_length=1, max_length=64)
    payload: AgentCorePhotoEvidenceRequest


class _PreparePacketInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["prepare_packet"]
    idempotency_key: str = Field(
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    workflow_id: str = Field(min_length=1, max_length=64)
    payload: PreparePacketRequest


class _ReviewEvidenceInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["review_evidence"]
    idempotency_key: str = Field(
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    workflow_id: str = Field(min_length=1, max_length=64)
    payload: ReviewEvidenceRequest


class _RunNextCheckInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["run_next_check"]
    idempotency_key: str = Field(
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    workflow_id: str = Field(min_length=1, max_length=64)
    payload: RunNextCheckRequest


class _ApprovePacketInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["approve_packet"]
    idempotency_key: str = Field(
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    workflow_id: str = Field(min_length=1, max_length=64)
    payload: ApprovePacketRequest


class _RenderPacketInvocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: Literal["render_packet"]
    workflow_id: str = Field(min_length=1, max_length=64)


AgentCoreInvocation = Annotated[
    _StartInvocation
    | _RestoreInvocation
    | _ResumeInvocation
    | _ReviewInvocation
    | _SubmitEvidenceInvocation
    | _SubmitPhotoEvidenceInvocation
    | _ReviewEvidenceInvocation
    | _RunNextCheckInvocation
    | _PreparePacketInvocation
    | _ApprovePacketInvocation
    | _RenderPacketInvocation,
    Field(discriminator="operation"),
]
INVOCATION_ADAPTER = TypeAdapter(AgentCoreInvocation)


def _session_reference(session_id: str) -> str:
    return sha256(session_id.encode("utf-8")).hexdigest()[:12]


def _error(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


class MettleAgentCoreRuntime:
    """Strict JSON boundary around one session-local Mettle workflow registry."""

    def __init__(
        self,
        *,
        workflows: WorkflowRegistry,
        evidence_dir: Path | None = None,
    ) -> None:
        self._workflows = workflows
        self._evidence_dir = evidence_dir or (
            Path(__file__).resolve().parent / "web" / "static" / "evidence"
        )

    def handle(self, payload: object, *, session_id: str) -> dict[str, Any]:
        session_reference = _session_reference(session_id)
        try:
            invocation = INVOCATION_ADAPTER.validate_python(payload)
        except ValidationError:
            LOGGER.warning(
                "agentcore_request_rejected session=%s reason=validation",
                session_reference,
            )
            return _error("invalid_request", "AgentCore request validation failed.")

        try:
            if isinstance(invocation, _RestoreInvocation):
                try:
                    envelope = self._workflows.restore_checkpoint(invocation.workflow_id, invocation.checkpoint)
                except (ValidationError, ValueError, TypeError, KeyError):
                    return _error("invalid_checkpoint", "Stored recovery checkpoint could not be restored.")
                operation = "restore"
                replayed = False
            elif isinstance(invocation, _StartInvocation):
                envelope, replayed = self._workflows.create(
                    invocation.payload,
                    idempotency_key=invocation.idempotency_key,
                )
                operation = "start"
            elif isinstance(invocation, _ResumeInvocation):
                envelope = self._workflows.resume(
                    invocation.workflow_id,
                    invocation.payload,
                    idempotency_key=invocation.idempotency_key,
                )
                replayed = False
                operation = "resume"
            elif isinstance(invocation, _ReviewInvocation):
                envelope = self._workflows.review(
                    invocation.workflow_id,
                    invocation.payload,
                    idempotency_key=invocation.idempotency_key,
                )
                replayed = False
                operation = "review"
            elif isinstance(invocation, _SubmitEvidenceInvocation):
                envelope = self._workflows.submit_evidence(
                    invocation.workflow_id,
                    invocation.payload,
                    idempotency_key=invocation.idempotency_key,
                )
                replayed = False
                operation = "submit_evidence"
            elif isinstance(invocation, _SubmitPhotoEvidenceInvocation):
                try:
                    encoded = base64.b64decode(
                        invocation.payload.image_base64,
                        validate=True,
                    )
                    image = normalize_photo(encoded)
                except (ValueError, PhotoUploadError) as exc:
                    raise EvidenceSubmissionError("uploaded photo is invalid") from exc
                envelope = self._workflows.submit_photo_evidence(
                    invocation.workflow_id,
                    SubmitPhotoEvidenceRequest(
                        citation_id=invocation.payload.citation_id
                    ),
                    image=image,
                    idempotency_key=invocation.idempotency_key,
                )
                replayed = False
                operation = "submit_photo_evidence"
            elif isinstance(invocation, _RunNextCheckInvocation):
                envelope = self._workflows.run_next_check(
                    invocation.workflow_id,
                    idempotency_key=invocation.idempotency_key,
                )
                replayed = False
                operation = "run_next_check"
            elif isinstance(invocation, _ReviewEvidenceInvocation):
                envelope = self._workflows.review_evidence(
                    invocation.workflow_id,
                    invocation.payload,
                    idempotency_key=invocation.idempotency_key,
                )
                replayed = False
                operation = "review_evidence"
            elif isinstance(invocation, _PreparePacketInvocation):
                envelope = self._workflows.prepare_packet(
                    invocation.workflow_id,
                    idempotency_key=invocation.idempotency_key,
                )
                replayed = False
                operation = "prepare_packet"
            elif isinstance(invocation, _ApprovePacketInvocation):
                envelope = self._workflows.approve_packet(
                    invocation.workflow_id,
                    invocation.payload,
                    idempotency_key=invocation.idempotency_key,
                )
                replayed = False
                operation = "approve_packet"
            else:
                pdf = self._workflows.render_packet(
                    invocation.workflow_id,
                    evidence_dir=self._evidence_dir,
                )
                if len(pdf) > 25_000_000:
                    return _error(
                        "packet_too_large",
                        "The rendered packet exceeds the AgentCore response limit.",
                    )
                LOGGER.info(
                    "agentcore_operation_completed session=%s operation=render_packet workflow=%s bytes=%s",
                    session_reference,
                    invocation.workflow_id,
                    len(pdf),
                )
                return {
                    "ok": True,
                    "content_type": "application/pdf",
                    "filename": "mettle-reinspection-packet.pdf",
                    "sha256": sha256(pdf).hexdigest(),
                    "body_base64": base64.b64encode(pdf).decode("ascii"),
                }
        except WorkflowNotFound as exc:
            return _error("workflow_not_found", str(exc))
        except WorkflowConflict as exc:
            return _error("workflow_conflict", str(exc))
        except WorkflowCapacityReached as exc:
            return _error("workflow_capacity_reached", str(exc))
        except WorkflowConfigurationError as exc:
            return _error("workflow_configuration_error", str(exc))
        except BedrockIntakeError as exc:
            LOGGER.warning(
                "agentcore_bedrock_failed session=%s",
                session_reference,
            )
            return _error("bedrock_intake_failed", str(exc))
        except BedrockVisionError as exc:
            LOGGER.warning("agentcore_vision_failed session=%s", session_reference)
            return _error("bedrock_vision_failed", str(exc))
        except EvidenceSubmissionError as exc:
            return _error("invalid_evidence_submission", str(exc))
        except PacketNotReady as exc:
            return _error("packet_not_ready", str(exc))
        except PacketNotApproved as exc:
            return _error("packet_not_approved", str(exc))
        except Exception:
            LOGGER.exception(
                "agentcore_operation_failed session=%s operation=%s",
                session_reference,
                invocation.operation,
            )
            return _error("internal_error", "Mettle could not complete the operation.")

        LOGGER.info(
            "agentcore_operation_completed session=%s operation=%s workflow=%s status=%s replayed=%s",
            session_reference,
            operation,
            envelope.workflow_id,
            envelope.snapshot.status,
            replayed,
        )
        return {
            "ok": True,
            "replayed": replayed,
            "workflow": envelope.model_dump(mode="json"),
            "checkpoint": self._workflows.checkpoint(envelope.workflow_id),
        }
