from datetime import date

import pytest
from pydantic import ValidationError

from mettle.communication import (
    DeliveryConflict,
    OutboundMessage,
    RecordingMessenger,
    Recipient,
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
