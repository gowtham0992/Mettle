from __future__ import annotations

from datetime import date
from enum import StrEnum
from hashlib import sha256
from hmac import compare_digest
from threading import Lock
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeliveryConflict(RuntimeError):
    """Raised when an idempotency key is replayed with a changed message."""


class DeliveryProviderError(RuntimeError):
    """Raised when the provider does not return a usable delivery receipt."""


class DeliveryStatus(StrEnum):
    RECORDED = "recorded"
    SENT = "sent"


class Recipient(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("recipient name must contain visible characters")
        return normalized


class OutboundMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    message_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9:_-]+$")
    notice_id: str = Field(min_length=1, max_length=100)
    citation_id: str = Field(min_length=1, max_length=50)
    recipient: Recipient
    body: str = Field(min_length=1, max_length=1000)
    idempotency_key: str = Field(
        min_length=8,
        max_length=160,
        pattern=r"^[A-Za-z0-9:._-]+$",
    )
    scheduled_on: date

    @field_validator("body")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("message body must contain visible characters")
        return normalized


class RecordedDelivery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    message_id: str
    notice_id: str
    citation_id: str
    recipient: Recipient
    body: str
    idempotency_key: str
    scheduled_on: date
    attempt_count: int = Field(ge=1)
    status: DeliveryStatus = DeliveryStatus.RECORDED
    provider_message_id: str | None = Field(default=None, max_length=160)


class Messenger(Protocol):
    def send(self, message: OutboundMessage) -> RecordedDelivery: ...


class SnsClient(Protocol):
    def publish(self, **kwargs: Any) -> dict[str, Any]: ...


class RecordingMessenger:
    """Thread-safe delivery fake with the same retry contract as a live adapter."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._messages: dict[str, OutboundMessage] = {}
        self._deliveries: dict[str, RecordedDelivery] = {}
        self._delivery_log: list[RecordedDelivery] = []

    @property
    def deliveries(self) -> tuple[RecordedDelivery, ...]:
        with self._lock:
            return tuple(self._delivery_log)

    def send(self, message: OutboundMessage) -> RecordedDelivery:
        with self._lock:
            existing_message = self._messages.get(message.idempotency_key)
            if existing_message is not None:
                if existing_message != message:
                    raise DeliveryConflict(
                        "idempotency key was already used for a different message"
                    )
                return self._deliveries[message.idempotency_key]

            delivery = RecordedDelivery(
                **message.model_dump(),
                attempt_count=1,
            )
            self._messages[message.idempotency_key] = message
            self._deliveries[message.idempotency_key] = delivery
            self._delivery_log.append(delivery)
            return delivery


class SnsMessenger:
    """One-way, allowlisted transactional SMS adapter for a bounded demo.

    Amazon SNS does not expose an idempotency key for direct SMS publishes, so
    this adapter serializes sends and retains successful receipts for the life
    of the AgentCore session. The destination allowlist is a SHA-256 digest so
    a personal demo number never needs to live in source or runtime settings.
    """

    def __init__(
        self,
        *,
        client: SnsClient,
        allowed_destination_sha256: str,
    ) -> None:
        normalized_hash = allowed_destination_sha256.strip().lower()
        if len(normalized_hash) != 64 or any(
            character not in "0123456789abcdef" for character in normalized_hash
        ):
            raise ValueError("allowed destination must be a SHA-256 hex digest")
        self._client = client
        self._allowed_destination_sha256 = normalized_hash
        self._lock = Lock()
        self._messages: dict[str, OutboundMessage] = {}
        self._deliveries: dict[str, RecordedDelivery] = {}
        self._fallback = RecordingMessenger()

    def send(self, message: OutboundMessage) -> RecordedDelivery:
        destination_hash = sha256(message.recipient.phone.encode("utf-8")).hexdigest()
        if not compare_digest(destination_hash, self._allowed_destination_sha256):
            return self._fallback.send(message)

        with self._lock:
            existing_message = self._messages.get(message.idempotency_key)
            if existing_message is not None:
                if existing_message != message:
                    raise DeliveryConflict(
                        "idempotency key was already used for a different message"
                    )
                return self._deliveries[message.idempotency_key]

            response = self._client.publish(
                PhoneNumber=message.recipient.phone,
                Message=message.body,
                MessageAttributes={
                    "AWS.SNS.SMS.SMSType": {
                        "DataType": "String",
                        "StringValue": "Transactional",
                    }
                },
            )
            provider_message_id = response.get("MessageId")
            if not isinstance(provider_message_id, str) or not provider_message_id:
                raise DeliveryProviderError(
                    "Amazon SNS did not return a delivery message identifier"
                )
            delivery = RecordedDelivery(
                **message.model_dump(),
                attempt_count=1,
                status=DeliveryStatus.SENT,
                provider_message_id=provider_message_id,
            )
            self._messages[message.idempotency_key] = message
            self._deliveries[message.idempotency_key] = delivery
            return delivery
