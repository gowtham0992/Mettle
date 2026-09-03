from __future__ import annotations

from copy import deepcopy

from botocore.exceptions import ClientError

from mettle.demo_sessions import DynamoDemoSessions


class FakeDynamoTable:
    def __init__(self) -> None:
        self.items: dict[str, dict] = {}

    def get_item(self, *, Key, ConsistentRead=False):
        assert ConsistentRead is True
        item = self.items.get(Key["pk"])
        return {"Item": deepcopy(item)} if item is not None else {}

    def put_item(
        self,
        *,
        Item,
        ConditionExpression,
        ExpressionAttributeNames=None,
        ExpressionAttributeValues=None,
    ):
        current = self.items.get(Item["pk"])
        if ConditionExpression == "attribute_not_exists(pk)":
            valid = current is None
        else:
            valid = current is not None and current["version"] == ExpressionAttributeValues[":expected"]
        if not valid:
            raise ClientError(
                {"Error": {"Code": "ConditionalCheckFailedException", "Message": "conflict"}},
                "PutItem",
            )
        self.items[Item["pk"]] = deepcopy(Item)


def test_durable_demo_session_survives_a_new_manager_instance() -> None:
    table = FakeDynamoTable()
    first_runtime = DynamoDemoSessions(table=table, clock=lambda: 1_000)
    second_runtime = DynamoDemoSessions(table=table, clock=lambda: 1_001)

    first_runtime.resolve_judgment(
        "browser-a", "route-review", decision="Approve routes with a wide mechanical photo"
    )
    advanced = first_runtime.advance("browser-a", idempotency_key="advance_once_123")
    restored = second_runtime.snapshot("browser-a")
    other_browser = second_runtime.snapshot("browser-b")

    assert advanced.scenario_step == restored.scenario_step == 1
    assert restored.metrics == advanced.metrics
    assert other_browser.scenario_step == 0
    assert table.items["demo#browser-a"]["expires_at"] == 8_200


def test_durable_demo_advance_is_idempotent_after_runtime_restart() -> None:
    table = FakeDynamoTable()
    first_runtime = DynamoDemoSessions(table=table)
    second_runtime = DynamoDemoSessions(table=table)

    first_runtime.resolve_judgment(
        "browser-a", "route-review", decision="Approve routes with a wide mechanical photo"
    )
    first = first_runtime.advance("browser-a", idempotency_key="same_action_123")
    replay = second_runtime.advance("browser-a", idempotency_key="same_action_123")

    assert replay.scenario_step == first.scenario_step == 1
    assert replay.metrics == first.metrics
