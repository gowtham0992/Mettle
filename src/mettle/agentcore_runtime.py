from __future__ import annotations

import logging
from hashlib import sha256
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from mettle.agents.bedrock import BedrockIntakeError
from mettle.workflow import WorkflowConfigurationError
from mettle.workflow_registry import (
    CreateWorkflowRequest,
    ResumeWorkflowRequest,
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


AgentCoreInvocation = Annotated[
    _StartInvocation | _ResumeInvocation,
    Field(discriminator="operation"),
]
INVOCATION_ADAPTER = TypeAdapter(AgentCoreInvocation)


def _session_reference(session_id: str) -> str:
    return sha256(session_id.encode("utf-8")).hexdigest()[:12]


def _error(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


class MettleAgentCoreRuntime:
    """Strict JSON boundary around one session-local Mettle workflow registry."""

    def __init__(self, *, workflows: WorkflowRegistry) -> None:
        self._workflows = workflows

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
            if isinstance(invocation, _StartInvocation):
                envelope, replayed = self._workflows.create(
                    invocation.payload,
                    idempotency_key=invocation.idempotency_key,
                )
                operation = "start"
            else:
                envelope = self._workflows.resume(
                    invocation.workflow_id,
                    invocation.payload,
                    idempotency_key=invocation.idempotency_key,
                )
                replayed = False
                operation = "resume"
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
        }
