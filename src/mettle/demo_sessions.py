from __future__ import annotations

import time
from collections.abc import Callable
from threading import Lock
from typing import Any, TypeVar

from botocore.exceptions import ClientError

from mettle.demo import DemoCampaign, DemoConflict, DemoStore, DemoStoreState


DEMO_SESSION_TTL_SECONDS = 2 * 60 * 60
MAX_DYNAMO_RETRIES = 4
Result = TypeVar("Result")


def _is_conditional_failure(exc: ClientError) -> bool:
    return exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"


class InMemoryDemoSessions:
    """Process-local session isolation used by development and tests."""

    def __init__(self, *, first_store: DemoStore | None = None) -> None:
        self._lock = Lock()
        self._stores: dict[str, DemoStore] = {}
        self._first_store = first_store

    def _store(self, session_key: str) -> DemoStore:
        with self._lock:
            store = self._stores.get(session_key)
            if store is None:
                store = self._first_store or DemoStore()
                self._first_store = None
                self._stores[session_key] = store
            return store

    def snapshot(self, session_key: str) -> DemoCampaign:
        return self._store(session_key).snapshot()

    def advance(self, session_key: str, *, idempotency_key: str) -> DemoCampaign:
        return self._store(session_key).advance(idempotency_key=idempotency_key)

    def reset(self, session_key: str) -> DemoCampaign:
        return self._store(session_key).reset()

    def resolve_judgment(
        self, session_key: str, judgment_id: str, *, decision: str
    ) -> DemoCampaign:
        return self._store(session_key).resolve_judgment(judgment_id, decision=decision)

    def render_packet(self, session_key: str, *, evidence_dir: Any) -> bytes:
        return self._store(session_key).render_packet(evidence_dir=evidence_dir)


class DynamoDemoSessions:
    """Durable browser-session state with optimistic concurrency in DynamoDB."""

    def __init__(self, *, table: Any, clock: Callable[[], float] = time.time) -> None:
        self._table = table
        self._clock = clock

    def _key(self, session_key: str) -> str:
        return f"demo#{session_key}"

    def _expires_at(self) -> int:
        return int(self._clock()) + DEMO_SESSION_TTL_SECONDS

    def _load(self, session_key: str) -> tuple[DemoStore, int, bool]:
        response = self._table.get_item(
            Key={"pk": self._key(session_key)},
            ConsistentRead=True,
        )
        item = response.get("Item")
        if not isinstance(item, dict):
            return DemoStore(), 0, False
        state = DemoStoreState.model_validate(item.get("state"))
        return DemoStore.from_state(state), int(item.get("version", 0)), True

    def _save(
        self,
        session_key: str,
        store: DemoStore,
        *,
        version: int,
        exists: bool,
    ) -> None:
        item = {
            "pk": self._key(session_key),
            "kind": "guided_demo_session",
            "version": version + 1,
            "state": store.dump_state().model_dump(mode="json"),
            "expires_at": self._expires_at(),
        }
        if not exists:
            self._table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(pk)",
            )
            return
        self._table.put_item(
            Item=item,
            ConditionExpression="#version = :expected",
            ExpressionAttributeNames={"#version": "version"},
            ExpressionAttributeValues={":expected": version},
        )

    def _mutate(
        self,
        session_key: str,
        operation: Callable[[DemoStore], Result],
    ) -> Result:
        for _attempt in range(MAX_DYNAMO_RETRIES):
            store, version, exists = self._load(session_key)
            result = operation(store)
            try:
                self._save(session_key, store, version=version, exists=exists)
                return result
            except ClientError as exc:
                if not _is_conditional_failure(exc):
                    raise
        raise DemoConflict("this demo session changed concurrently; retry the action")

    def snapshot(self, session_key: str) -> DemoCampaign:
        store, _version, exists = self._load(session_key)
        if exists:
            return store.snapshot()
        return self._mutate(session_key, lambda item: item.snapshot())

    def advance(self, session_key: str, *, idempotency_key: str) -> DemoCampaign:
        return self._mutate(
            session_key,
            lambda store: store.advance(idempotency_key=idempotency_key),
        )

    def reset(self, session_key: str) -> DemoCampaign:
        return self._mutate(session_key, lambda store: store.reset())

    def resolve_judgment(
        self, session_key: str, judgment_id: str, *, decision: str
    ) -> DemoCampaign:
        return self._mutate(
            session_key,
            lambda store: store.resolve_judgment(judgment_id, decision=decision),
        )

    def render_packet(self, session_key: str, *, evidence_dir: Any) -> bytes:
        store, _version, _exists = self._load(session_key)
        return store.render_packet(evidence_dir=evidence_dir)
