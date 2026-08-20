from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from mettle.automation import AutomationStatus, CampaignAutomation
from mettle import scheduler_runtime
from mettle.workflow_registry import CreateWorkflowRequest, WorkflowRegistry


NOTICE = Path("examples/notices/failed-rough-in.txt").read_text(encoding="utf-8")


def payload() -> CreateWorkflowRequest:
    return CreateWorkflowRequest.model_validate(
        {
            "notice_text": NOTICE,
            "intake_provider": "local",
            "as_of": "2026-08-10",
            "roster": [
                {"trade": "electrical", "name": "Mike", "phone": "+13035550101"},
                {"trade": "framing", "name": "Jen", "phone": "+13035550102"},
                {"trade": "mechanical", "name": "Luis", "phone": "+13035550103"},
            ],
        }
    )


class FakeGateway:
    def __init__(self, envelope, *, executed: bool) -> None:
        self.envelope = envelope
        self.executed = executed
        self.events = []

    def run_scheduled_check(self, event):
        self.events.append(event)
        return self.envelope, self.executed


def test_scheduler_handler_validates_event_and_returns_only_safe_reference(monkeypatch) -> None:
    envelope, _ = WorkflowRegistry().create(
        payload(), idempotency_key="scheduler_handler_source"
    )
    envelope.automation = CampaignAutomation(
        status=AutomationStatus.SCHEDULED,
        schedule_version=1,
        schedule_name="mettle-test-v1",
        next_check_at=datetime(2026, 8, 19, 18, 1, 30, tzinfo=UTC),
        logical_check_on=date(2026, 8, 14),
    )
    gateway = FakeGateway(envelope, executed=True)
    monkeypatch.setattr(scheduler_runtime, "configured_gateway", lambda: gateway)
    event = {
        "owner_hash": "a" * 64,
        "workflow_id": envelope.workflow_id,
        "schedule_name": "mettle-test-v1",
        "schedule_version": 1,
        "logical_check_on": "2026-08-14",
    }

    result = scheduler_runtime.handle_scheduled_check(event, None)

    assert result["ok"] is True
    assert result["executed"] is True
    assert result["automation_status"] == "scheduled"
    assert envelope.workflow_id not in str(result)
    assert len(gateway.events) == 1


def test_scheduler_handler_rejects_untrusted_or_extra_payload_fields(monkeypatch) -> None:
    monkeypatch.setattr(
        scheduler_runtime,
        "configured_gateway",
        lambda: pytest.fail("gateway must not be constructed for invalid input"),
    )

    with pytest.raises(ValueError, match="payload is invalid"):
        scheduler_runtime.handle_scheduled_check(
            {
                "owner_hash": "not-a-hash",
                "workflow_id": "workflow",
                "schedule_name": "mettle-test-v1",
                "schedule_version": 1,
                "logical_check_on": "2026-08-14",
                "phone": "+13035550101",
            },
            None,
        )
