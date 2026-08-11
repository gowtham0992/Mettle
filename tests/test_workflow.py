from datetime import date
from pathlib import Path

import pytest

from mettle.communication import RecordingMessenger, Recipient
from mettle.domain import Trade
from mettle.workflow import (
    RecoveryWorkflowSession,
    WorkflowConfigurationError,
    WorkflowStatus,
)


NOTICE = Path("examples/notices/failed-rough-in.txt").read_text(encoding="utf-8")
ROSTER = {
    Trade.ELECTRICAL: Recipient(name="Mike Alvarez", phone="+13035550101"),
    Trade.FRAMING: Recipient(name="Jen Ortiz", phone="+13035550102"),
    Trade.MECHANICAL: Recipient(name="Luis Vega", phone="+13035550103"),
}


def test_strands_workflow_coordinates_grounded_work_then_interrupts() -> None:
    messenger = RecordingMessenger()
    session = RecoveryWorkflowSession(
        notice_text=NOTICE,
        as_of=date(2026, 8, 10),
        roster=ROSTER,
        messenger=messenger,
    )

    snapshot = session.start()

    assert snapshot.status is WorkflowStatus.INTERRUPTED
    assert len(snapshot.interrupts) == 1
    assert snapshot.interrupts[0].name == "contractor-judgment"
    assert [item.citation_id for item in messenger.deliveries] == ["1", "2"]
    assert all("Notice:" in item.body for item in messenger.deliveries)
    assert all("Reinspection target:" in item.body for item in messenger.deliveries)


def test_strands_workflow_resumes_without_duplicate_outreach() -> None:
    messenger = RecordingMessenger()
    session = RecoveryWorkflowSession(
        notice_text=NOTICE,
        as_of=date(2026, 8, 10),
        roster=ROSTER,
        messenger=messenger,
    )
    interrupted = session.start()

    completed = session.resume(
        interrupt_id=interrupted.interrupts[0].interrupt_id,
        decision="Request a wide equipment-clearance photo with the access panel open.",
    )

    assert completed.status is WorkflowStatus.COMPLETED
    assert completed.contractor_decision.startswith("Request a wide")
    assert completed.interrupts == []
    assert len(messenger.deliveries) == 3
    assert messenger.deliveries[-1].recipient.name == "Luis Vega"
    assert "Contractor direction:" in messenger.deliveries[-1].body


def test_missing_trade_recipient_fails_before_any_message_is_recorded() -> None:
    messenger = RecordingMessenger()
    session = RecoveryWorkflowSession(
        notice_text=NOTICE,
        as_of=date(2026, 8, 10),
        roster={Trade.ELECTRICAL: ROSTER[Trade.ELECTRICAL]},
        messenger=messenger,
    )

    with pytest.raises(WorkflowConfigurationError, match="framing"):
        session.start()

    assert messenger.deliveries == ()


def test_notice_identifiers_are_not_used_as_delivery_identifiers() -> None:
    messenger = RecordingMessenger()
    notice = NOTICE.replace("CR-2026-0417", "Castle Pines / rough-in #41")
    session = RecoveryWorkflowSession(
        notice_text=notice,
        as_of=date(2026, 8, 10),
        roster=ROSTER,
        messenger=messenger,
    )

    snapshot = session.start()

    assert snapshot.status is WorkflowStatus.INTERRUPTED
    assert all("Castle Pines" not in item.message_id for item in messenger.deliveries)
    assert all("Castle Pines" not in item.idempotency_key for item in messenger.deliveries)
