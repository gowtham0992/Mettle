from __future__ import annotations

import io
import json
from collections import deque
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest
from botocore.exceptions import ClientError

from mettle.automation import AutomationStatus, CampaignAutomation, ScheduledCheckEvent
from mettle.durable_agentcore_gateway import DurableAgentCoreWorkflowGateway
from mettle.request_identity import (
    AuthenticationRequired,
    reset_principal,
    set_principal,
)
from mettle.workflow_registry import (
    CreateWorkflowRequest,
    ReviewWorkflowRequest,
    WorkflowNotFound,
    WorkflowRegistry,
)


NOTICE = Path("examples/notices/failed-rough-in.txt").read_text(encoding="utf-8")
RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/MettleRecovery-test"


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


def conditional_failure() -> ClientError:
    return ClientError(
        {"Error": {"Code": "ConditionalCheckFailedException", "Message": "condition"}},
        "PutItem",
    )


class MemoryTable:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def put_item(self, *, Item, ConditionExpression=None, ExpressionAttributeValues=None):
        current = self.items.get(Item["pk"])
        if ConditionExpression == "attribute_not_exists(pk)" and current is not None:
            raise conditional_failure()
        if current is not None and "session_id = :session_id" in (ConditionExpression or ""):
            if current.get("session_id") != ExpressionAttributeValues[":session_id"]:
                raise conditional_failure()
        self.items[Item["pk"]] = dict(Item)

    def get_item(self, *, Key, ConsistentRead):
        item = self.items.get(Key["pk"])
        return {"Item": dict(item)} if item else {}

    def update_item(
        self,
        *,
        Key,
        UpdateExpression,
        ExpressionAttributeValues,
        ExpressionAttributeNames=None,
        ConditionExpression=None,
    ):
        item = self.items.get(Key["pk"])
        if item is None:
            raise conditional_failure()
        if "#status" in UpdateExpression:
            item["status"] = ExpressionAttributeValues[":completed"]
            item["envelope"] = ExpressionAttributeValues[":envelope"]
            item["expires_at"] = ExpressionAttributeValues[":expires_at"]
            if ":workflow_id" in ExpressionAttributeValues:
                item["workflow_id"] = ExpressionAttributeValues[":workflow_id"]
            return {}
        if UpdateExpression.startswith("SET lock_token"):
            now = ExpressionAttributeValues[":now"]
            if item.get("lock_token") is not None and item.get("lock_until", 0) >= now:
                raise conditional_failure()
            item["lock_token"] = ExpressionAttributeValues[":token"]
            item["lock_until"] = ExpressionAttributeValues[":until"]
            return {}
        if UpdateExpression.startswith("SET envelope"):
            if item.get("lock_token") != ExpressionAttributeValues[":token"]:
                raise conditional_failure()
            item["envelope"] = ExpressionAttributeValues[":envelope"]
            item["expires_at"] = ExpressionAttributeValues[":expires_at"]
            item.pop("lock_token", None)
            item.pop("lock_until", None)
            item.pop("packet_key", None)
            return {}
        if UpdateExpression == "REMOVE lock_token, lock_until":
            if item.get("lock_token") != ExpressionAttributeValues[":token"]:
                raise conditional_failure()
            item.pop("lock_token", None)
            item.pop("lock_until", None)
            return {}
        raise AssertionError(f"unexpected update: {UpdateExpression}")


class QueueClient:
    def __init__(self, results: list[dict]) -> None:
        self.results = deque(results)
        self.requests: list[dict] = []

    def invoke_agent_runtime(self, **kwargs):
        self.requests.append(kwargs)
        return {
            "statusCode": 200,
            "response": io.BytesIO(json.dumps(self.results.popleft()).encode("utf-8")),
        }


class UnusedBucket:
    pass


def gateway(
    table: MemoryTable,
    client: QueueClient,
    *,
    campaign_scheduler=None,
) -> DurableAgentCoreWorkflowGateway:
    return DurableAgentCoreWorkflowGateway(
        client=client,
        runtime_arn=RUNTIME_ARN,
        table=table,
        packet_bucket=UnusedBucket(),
        campaign_scheduler=campaign_scheduler,
    )


def created_result() -> dict:
    envelope, _ = WorkflowRegistry().create(payload(), idempotency_key="source_create_123")
    return {"ok": True, "replayed": False, "workflow": envelope.model_dump(mode="json")}


def review_request(envelope) -> ReviewWorkflowRequest:
    return ReviewWorkflowRequest.model_validate(
        {
            "interrupt_id": envelope.snapshot.interrupts[0].interrupt_id,
            "citations": [
                {
                    "citation_id": citation.citation_id,
                    "trade": (
                        citation.trade.value
                        if citation.trade.value != "unknown"
                        else "mechanical"
                    ),
                    "closure_route": citation.closure_route.value,
                    "evidence_requirements": citation.evidence_requirements
                    or ["Wide photo showing the completed correction and its location"],
                }
                for citation in envelope.snapshot.notice.citations
            ],
        }
    )


class FakeCampaignScheduler:
    def __init__(self) -> None:
        self.scheduled: list[dict] = []
        self.cancelled: list[CampaignAutomation | None] = []

    def schedule(self, **kwargs) -> CampaignAutomation:
        self.scheduled.append(kwargs)
        return CampaignAutomation(
            status=AutomationStatus.SCHEDULED,
            schedule_version=kwargs["schedule_version"],
            schedule_name=f"mettle-test-v{kwargs['schedule_version']}",
            next_check_at=datetime(2026, 8, 19, 18, kwargs["schedule_version"], tzinfo=UTC),
            logical_check_on=kwargs["logical_check_on"],
            accelerated_demo_clock=True,
        )

    def cancel(self, automation) -> None:
        self.cancelled.append(automation)


def test_live_gateway_fails_closed_without_verified_subject() -> None:
    with pytest.raises(AuthenticationRequired):
        gateway(MemoryTable(), QueueClient([])).get("workflow")


def test_workflow_survives_gateway_recreation_and_is_owner_scoped() -> None:
    table = MemoryTable()
    client = QueueClient([created_result()])
    first_gateway = gateway(table, client)
    alice = set_principal("cognito-alice")
    try:
        created, replayed = first_gateway.create(payload(), idempotency_key="public_create_123")
        restored = gateway(table, client).get(created.workflow_id)
    finally:
        reset_principal(alice)

    assert replayed is False
    assert restored == created
    assert len(client.requests) == 1

    bob = set_principal("cognito-bob")
    try:
        with pytest.raises(WorkflowNotFound):
            gateway(table, client).get(created.workflow_id)
    finally:
        reset_principal(bob)


def test_create_retry_reuses_stored_result_without_second_agentcore_spend() -> None:
    table = MemoryTable()
    client = QueueClient([created_result()])
    owner = set_principal("cognito-alice")
    try:
        first, _ = gateway(table, client).create(payload(), idempotency_key="public_replay_123")
        replay, replayed = gateway(table, client).create(
            payload(), idempotency_key="public_replay_123"
        )
    finally:
        reset_principal(owner)

    assert replayed is True
    assert replay == first
    assert len(client.requests) == 1


def test_review_schedules_checkpoint_and_stale_event_cannot_advance_twice() -> None:
    source = WorkflowRegistry()
    created, _ = source.create(payload(), idempotency_key="source_schedule_create")
    review = review_request(created)
    reviewed = source.review(
        created.workflow_id,
        review,
        idempotency_key="source_schedule_review",
    )
    checked = source.run_next_check(
        created.workflow_id,
        idempotency_key="source_schedule_check",
    )
    client = QueueClient(
        [
            {"ok": True, "workflow": created.model_dump(mode="json")},
            {"ok": True, "workflow": reviewed.model_dump(mode="json")},
            {"ok": True, "workflow": checked.model_dump(mode="json")},
        ]
    )
    table = MemoryTable()
    scheduler = FakeCampaignScheduler()
    durable = gateway(table, client, campaign_scheduler=scheduler)
    principal = "cognito-alice"
    token = set_principal(principal)
    try:
        cloud_created, _ = durable.create(
            payload(), idempotency_key="public_schedule_create"
        )
        cloud_reviewed = durable.review(
            cloud_created.workflow_id,
            review,
            idempotency_key="public_schedule_review",
        )
    finally:
        reset_principal(token)

    first_automation = cloud_reviewed.automation
    assert first_automation is not None
    assert first_automation.status is AutomationStatus.SCHEDULED
    assert first_automation.logical_check_on.isoformat() == "2026-08-14"
    event = ScheduledCheckEvent(
        owner_hash=sha256(principal.encode("utf-8")).hexdigest(),
        workflow_id=cloud_created.workflow_id,
        schedule_name=first_automation.schedule_name,
        schedule_version=first_automation.schedule_version,
        logical_check_on=first_automation.logical_check_on,
    )

    advanced, executed = durable.run_scheduled_check(event)
    stale, stale_executed = durable.run_scheduled_check(event)

    assert executed is True
    assert advanced.snapshot.plan.as_of.isoformat() == "2026-08-14"
    assert advanced.automation.schedule_version == 2
    assert advanced.automation.logical_check_on.isoformat() == "2026-08-15"
    assert stale_executed is False
    assert stale == advanced
    assert len(client.requests) == 3
