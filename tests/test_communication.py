from datetime import date
from hashlib import sha256

import pytest
from pydantic import ValidationError

from mettle.communication import (
    DeliveryConflict,
    DeliveryProviderError,
    DeliveryStatus,
    OutboundMessage,
    RecordingMessenger,
    Recipient,
    SnsMessenger,
)


def message(*, body: str = "Please send the two notice-required photos.") -> OutboundMessage:
    return OutboundMessage(
        message_id="msg-c1-initial",
        notice_id="CR-2026-0417",
        citation_id="1",
        recipient=Recipient(name="Mike Alvarez", phone="+13035550101"),
        body=body,
        idempotency_key="CR-2026-0417:c1:initial",
        scheduled_on=date(2026, 8, 10),
    )


def test_recording_messenger_replay_has_one_delivery() -> None:
    messenger = RecordingMessenger()

    first = messenger.send(message())
    replay = messenger.send(message())

    assert replay == first
    assert len(messenger.deliveries) == 1
    assert messenger.deliveries[0].attempt_count == 1


def test_recording_messenger_rejects_changed_payload_for_same_key() -> None:
    messenger = RecordingMessenger()
    messenger.send(message())

    with pytest.raises(DeliveryConflict, match="idempotency key"):
        messenger.send(message(body="A changed instruction must not replace the first send."))


def test_outbound_boundary_rejects_invalid_phone_and_oversized_body() -> None:
    with pytest.raises(ValidationError, match="phone"):
        Recipient(name="Untrusted recipient", phone="303-555-0101")

    with pytest.raises(ValidationError, match="body"):
        message(body="x" * 1001)


class FakeSnsClient:
    def __init__(self, response: dict | None = None) -> None:
        self.response = response or {"MessageId": "sns-message-123"}
        self.requests: list[dict] = []

    def publish(self, **kwargs):
        self.requests.append(kwargs)
        return self.response


def live_messenger(client: FakeSnsClient) -> SnsMessenger:
    allowed = sha256(message().recipient.phone.encode("utf-8")).hexdigest()
    return SnsMessenger(client=client, allowed_destination_sha256=allowed)


def test_sns_messenger_sends_one_transactional_message_and_replays_receipt() -> None:
    client = FakeSnsClient()
    messenger = live_messenger(client)

    first = messenger.send(message())
    replay = messenger.send(message())

    assert replay == first
    assert first.status is DeliveryStatus.SENT
    assert first.provider_message_id == "sns-message-123"
    assert len(client.requests) == 1
    assert client.requests[0] == {
        "PhoneNumber": "+13035550101",
        "Message": "Please send the two notice-required photos.",
        "MessageAttributes": {
            "AWS.SNS.SMS.SMSType": {
                "DataType": "String",
                "StringValue": "Transactional",
            }
        },
    }


def test_sns_messenger_rejects_every_destination_except_demo_allowlist() -> None:
    client = FakeSnsClient()
    messenger = live_messenger(client)
    changed = message().model_copy(
        update={"recipient": Recipient(name="Other", phone="+13035550199")}
    )

    delivery = messenger.send(changed)

    assert client.requests == []
    assert delivery.status is DeliveryStatus.RECORDED
    assert delivery.provider_message_id is None


def test_sns_messenger_fails_closed_without_provider_receipt() -> None:
    client = FakeSnsClient(response={"ResponseMetadata": {"HTTPStatusCode": 200}})

    with pytest.raises(DeliveryProviderError, match="message identifier"):
        live_messenger(client).send(message())


def test_sns_messenger_rejects_invalid_destination_digest() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        SnsMessenger(client=FakeSnsClient(), allowed_destination_sha256="not-a-hash")
