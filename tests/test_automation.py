from __future__ import annotations

import json
from datetime import UTC, date, datetime

from botocore.exceptions import ClientError

from mettle.automation import (
    AutomationStatus,
    CampaignAutomation,
    EventBridgeCampaignScheduler,
    ScheduledCheckEvent,
)


def not_found(operation: str) -> ClientError:
    return ClientError(
        {"Error": {"Code": "ResourceNotFoundException", "Message": "missing"}},
        operation,
    )


class FakeSchedulerClient:
    def __init__(self) -> None:
        self.created: list[dict] = []
        self.updated: list[dict] = []
        self.deleted: list[dict] = []

    def create_schedule(self, **kwargs):
        self.created.append(kwargs)
        return {"ScheduleArn": "arn:aws:scheduler:us-east-1:123:schedule/mettle/name"}

    def update_schedule(self, **kwargs):
        self.updated.append(kwargs)
        raise not_found("UpdateSchedule")

    def delete_schedule(self, **kwargs):
        self.deleted.append(kwargs)
        return {}


def scheduler(client: FakeSchedulerClient) -> EventBridgeCampaignScheduler:
    return EventBridgeCampaignScheduler(
        client=client,
        target_arn="arn:aws:lambda:us-east-1:123456789012:function:mettle-scheduler",
        execution_role_arn="arn:aws:iam::123456789012:role/MettleSchedulerInvoke",
        schedule_group="mettle-recovery",
        dlq_arn="arn:aws:sqs:us-east-1:123456789012:mettle-scheduler-dlq",
        demo_delay_seconds=90,
        clock=lambda: datetime(2026, 8, 19, 18, 0, tzinfo=UTC),
    )


def test_eventbridge_schedule_is_exact_ephemeral_and_contains_no_phone_or_session() -> None:
    client = FakeSchedulerClient()

    automation = scheduler(client).schedule(
        owner_hash="a" * 64,
        workflow_id="workflow-safe-123",
        logical_check_on=date(2026, 8, 14),
        schedule_version=1,
        previous=None,
    )

    assert automation.status is AutomationStatus.SCHEDULED
    assert automation.next_check_at == datetime(2026, 8, 19, 18, 1, 30, tzinfo=UTC)
    assert automation.accelerated_demo_clock is True
    assert len(client.created) == 1
    request = client.created[0]
    assert request["FlexibleTimeWindow"] == {"Mode": "OFF"}
    assert request["ActionAfterCompletion"] == "DELETE"
    assert request["ScheduleExpression"] == "at(2026-08-19T18:01:30)"
    payload = json.loads(request["Target"]["Input"])
    assert ScheduledCheckEvent.model_validate(payload).logical_check_on == date(2026, 8, 14)
    assert "phone" not in request["Target"]["Input"].lower()
    assert "session" not in request["Target"]["Input"].lower()


def test_reschedule_cancels_only_the_previous_deterministic_schedule() -> None:
    client = FakeSchedulerClient()
    previous = CampaignAutomation(
        status=AutomationStatus.SCHEDULED,
        schedule_version=1,
        schedule_name="mettle-old-v1",
        next_check_at=datetime(2026, 8, 19, 17, 0, tzinfo=UTC),
        logical_check_on=date(2026, 8, 14),
        accelerated_demo_clock=True,
    )

    result = scheduler(client).schedule(
        owner_hash="b" * 64,
        workflow_id="workflow-safe-123",
        logical_check_on=date(2026, 8, 15),
        schedule_version=2,
        previous=previous,
    )

    assert client.deleted == [
        {"Name": "mettle-old-v1", "GroupName": "mettle-recovery"}
    ]
    assert result.schedule_name != previous.schedule_name
    assert result.schedule_name.endswith("-v2")


def test_scheduled_event_derives_stable_bounded_idempotency_key() -> None:
    event = ScheduledCheckEvent(
        owner_hash="c" * 64,
        workflow_id="workflow-safe-123",
        schedule_name="mettle-safe-v7",
        schedule_version=7,
        logical_check_on=date(2026, 8, 16),
    )

    assert event.idempotency_key.startswith("scheduled_7_20260816_")
    assert len(event.idempotency_key) <= 64
