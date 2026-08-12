from __future__ import annotations

import io
import json
from collections import deque
from pathlib import Path

import pytest
from botocore.exceptions import ClientError

from mettle.durable_agentcore_gateway import DurableAgentCoreWorkflowGateway
from mettle.request_identity import (
    AuthenticationRequired,
    reset_principal,
    set_principal,
)
from mettle.workflow_registry import CreateWorkflowRequest, WorkflowNotFound, WorkflowRegistry


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


def gateway(table: MemoryTable, client: QueueClient) -> DurableAgentCoreWorkflowGateway:
    return DurableAgentCoreWorkflowGateway(
        client=client,
        runtime_arn=RUNTIME_ARN,
        table=table,
        packet_bucket=UnusedBucket(),
    )


def created_result() -> dict:
    envelope, _ = WorkflowRegistry().create(payload(), idempotency_key="source_create_123")
    return {"ok": True, "replayed": False, "workflow": envelope.model_dump(mode="json")}


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
