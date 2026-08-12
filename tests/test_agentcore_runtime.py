from pathlib import Path

from mettle.agentcore_runtime import MettleAgentCoreRuntime
from mettle.notice_parser import parse_notice
from mettle.workflow_registry import WorkflowRegistry


NOTICE = Path("examples/notices/failed-rough-in.txt").read_text(encoding="utf-8")


def workflow_payload(*, provider: str = "bedrock") -> dict:
    return {
        "notice_text": NOTICE,
        "intake_provider": provider,
        "as_of": "2026-08-10",
        "roster": [
            {"trade": "electrical", "name": "Mike Alvarez", "phone": "+13035550101"},
            {"trade": "framing", "name": "Jen Ortiz", "phone": "+13035550102"},
            {"trade": "mechanical", "name": "Luis Vega", "phone": "+13035550103"},
        ],
    }


def runtime() -> MettleAgentCoreRuntime:
    return MettleAgentCoreRuntime(
        workflows=WorkflowRegistry(bedrock_intake=parse_notice)
    )


def test_agentcore_session_starts_then_resumes_the_same_strands_graph() -> None:
    subject = runtime()
    started = subject.handle(
        {
            "operation": "start",
            "idempotency_key": "agentcore_start_123",
            "payload": workflow_payload(),
        },
        session_id="session-123456789012345678901234567890123",
    )

    assert started["ok"] is True
    workflow = started["workflow"]
    assert workflow["intake_provider"] == "bedrock"
    assert workflow["snapshot"]["status"] == "interrupted"
    assert len(workflow["snapshot"]["deliveries"]) == 2

    resumed = subject.handle(
        {
            "operation": "resume",
            "idempotency_key": "agentcore_resume_123",
            "workflow_id": workflow["workflow_id"],
            "payload": {
                "interrupt_id": workflow["snapshot"]["interrupts"][0]["interrupt_id"],
                "decision": "Request a wide equipment-clearance photo with the access panel open.",
            },
        },
        session_id="session-123456789012345678901234567890123",
    )

    assert resumed["ok"] is True
    assert resumed["workflow"]["snapshot"]["status"] == "completed"
    assert len(resumed["workflow"]["snapshot"]["deliveries"]) == 3


def test_agentcore_start_replay_does_not_repeat_paid_intake() -> None:
    calls: list[str] = []

    def intake(text: str):
        calls.append(text)
        return parse_notice(text)

    subject = MettleAgentCoreRuntime(
        workflows=WorkflowRegistry(bedrock_intake=intake)
    )
    request = {
        "operation": "start",
        "idempotency_key": "agentcore_replay_123",
        "payload": workflow_payload(),
    }

    first = subject.handle(request, session_id="session-123456789012345678901234567890123")
    replay = subject.handle(request, session_id="session-123456789012345678901234567890123")

    assert first["replayed"] is False
    assert replay["replayed"] is True
    assert replay["workflow"] == first["workflow"]
    assert calls == [NOTICE]


def test_agentcore_boundary_rejects_unknown_fields_without_echoing_input() -> None:
    response = runtime().handle(
        {
            "operation": "start",
            "idempotency_key": "agentcore_invalid_123",
            "payload": workflow_payload(),
            "aws_profile": "admin",
        },
        session_id="session-123456789012345678901234567890123",
    )

    assert response == {
        "ok": False,
        "error": {
            "code": "invalid_request",
            "message": "AgentCore request validation failed.",
        },
    }


def test_agentcore_boundary_returns_quiet_error_for_unknown_workflow() -> None:
    response = runtime().handle(
        {
            "operation": "resume",
            "idempotency_key": "agentcore_missing_123",
            "workflow_id": "not-a-workflow",
            "payload": {
                "interrupt_id": "not-an-interrupt",
                "decision": "Use a wide clearance photo",
            },
        },
        session_id="session-123456789012345678901234567890123",
    )

    assert response == {
        "ok": False,
        "error": {"code": "workflow_not_found", "message": "workflow does not exist"},
    }
