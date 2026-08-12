from __future__ import annotations

import io
import json
from collections import deque
from pathlib import Path

import pytest

from mettle.agentcore_gateway import AgentCoreGatewayError, AgentCoreWorkflowGateway
from mettle.workflow_registry import (
    CreateWorkflowRequest,
    ResumeWorkflowRequest,
    WorkflowConflict,
    WorkflowRegistry,
)


NOTICE = Path("examples/notices/failed-rough-in.txt").read_text(encoding="utf-8")
RUNTIME_ARN = (
    "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/MettleRecovery-example"
)


def create_payload() -> CreateWorkflowRequest:
    return CreateWorkflowRequest.model_validate(
        {
            "notice_text": NOTICE,
            "intake_provider": "local",
            "as_of": "2026-08-10",
            "roster": [
                {
                    "trade": "electrical",
                    "name": "Mike Alvarez",
                    "phone": "+13035550101",
                },
                {
                    "trade": "framing",
                    "name": "Jen Ortiz",
                    "phone": "+13035550102",
                },
                {
                    "trade": "mechanical",
                    "name": "Luis Vega",
                    "phone": "+13035550103",
                },
            ],
        }
    )


def interrupted_envelope():
    return WorkflowRegistry().create(
        create_payload(), idempotency_key="source_create_123"
    )[0]


class QueueClient:
    def __init__(self, results: list[dict | Exception]) -> None:
        self.results = deque(results)
        self.requests: list[dict] = []

    def invoke_agent_runtime(self, **kwargs):
        self.requests.append(kwargs)
        result = self.results.popleft()
        if isinstance(result, Exception):
            raise result
        return {
            "statusCode": 200,
            "response": io.BytesIO(json.dumps(result).encode("utf-8")),
        }


def success(envelope, *, replayed: bool = False) -> dict:
    return {
        "ok": True,
        "replayed": replayed,
        "workflow": envelope.model_dump(mode="json"),
    }


def test_create_keeps_agentcore_session_private_and_replays_without_second_spend() -> None:
    envelope = interrupted_envelope()
    client = QueueClient([success(envelope)])
    gateway = AgentCoreWorkflowGateway(client=client, runtime_arn=RUNTIME_ARN)

    first, replayed = gateway.create(create_payload(), idempotency_key="cloud_create_123")
    replay, was_replayed = gateway.create(
        create_payload(), idempotency_key="cloud_create_123"
    )

    assert replayed is False
    assert was_replayed is True
    assert replay == first
    assert len(client.requests) == 1
    request = client.requests[0]
    assert request["runtimeSessionId"].startswith("mettle-")
    assert len(request["runtimeSessionId"]) >= 33
    invocation = json.loads(request["payload"])
    assert invocation["operation"] == "start"
    assert invocation["idempotency_key"] == "cloud_create_123"
    assert "runtimeSessionId" not in json.dumps(first.model_dump(mode="json"))


def test_create_retry_after_transport_failure_reuses_the_same_agentcore_session() -> None:
    envelope = interrupted_envelope()
    client = QueueClient([RuntimeError("network down"), success(envelope, replayed=True)])
    gateway = AgentCoreWorkflowGateway(client=client, runtime_arn=RUNTIME_ARN)

    with pytest.raises(AgentCoreGatewayError, match="could not be reached"):
        gateway.create(create_payload(), idempotency_key="cloud_retry_123")
    result, replayed = gateway.create(
        create_payload(), idempotency_key="cloud_retry_123"
    )

    assert result.workflow_id == envelope.workflow_id
    assert replayed is True
    assert len(client.requests) == 2
    assert client.requests[0]["runtimeSessionId"] == client.requests[1]["runtimeSessionId"]


def test_changed_create_replay_is_rejected_before_agentcore_invocation() -> None:
    envelope = interrupted_envelope()
    client = QueueClient([success(envelope)])
    gateway = AgentCoreWorkflowGateway(client=client, runtime_arn=RUNTIME_ARN)
    gateway.create(create_payload(), idempotency_key="cloud_conflict_123")
    changed = create_payload().model_copy(
        update={"notice_text": NOTICE.replace("100 Demo Way", "200 Demo Way")}
    )

    with pytest.raises(WorkflowConflict, match="different workflow request"):
        gateway.create(changed, idempotency_key="cloud_conflict_123")

    assert len(client.requests) == 1


def test_resume_reuses_session_and_is_locally_idempotent() -> None:
    source = WorkflowRegistry()
    created, _ = source.create(create_payload(), idempotency_key="resume_source_123")
    interrupt = created.snapshot.interrupts[0]
    payload = ResumeWorkflowRequest(
        interrupt_id=interrupt.interrupt_id,
        decision="Use a wide photo showing equipment clearance with the panel open",
    )
    completed = source.resume(
        created.workflow_id,
        payload,
        idempotency_key="resume_source_decision_123",
    )
    client = QueueClient([success(created), success(completed)])
    gateway = AgentCoreWorkflowGateway(client=client, runtime_arn=RUNTIME_ARN)
    gateway.create(create_payload(), idempotency_key="cloud_resume_create_123")

    first = gateway.resume(
        created.workflow_id,
        payload,
        idempotency_key="cloud_resume_123",
    )
    replay = gateway.resume(
        created.workflow_id,
        payload,
        idempotency_key="cloud_resume_123",
    )

    assert first == replay
    assert first.snapshot.status == "completed"
    assert len(client.requests) == 2
    assert client.requests[0]["runtimeSessionId"] == client.requests[1]["runtimeSessionId"]


def test_runtime_error_is_mapped_without_exposing_untrusted_details() -> None:
    client = QueueClient(
        [{"ok": False, "error": {"code": "internal_error", "message": "secret"}}]
    )
    gateway = AgentCoreWorkflowGateway(client=client, runtime_arn=RUNTIME_ARN)

    with pytest.raises(AgentCoreGatewayError) as raised:
        gateway.create(create_payload(), idempotency_key="cloud_error_123")

    assert "secret" not in str(raised.value)
