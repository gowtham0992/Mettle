from datetime import date
from pathlib import Path
import pytest

from mettle.communication import RecordingMessenger, Recipient
from mettle.domain import Trade
from mettle.workflow import RecoveryCheckpoint, RecoveryWorkflowSession, CorrectionReview, ReviewedCitation
from mettle.workflow import WorkflowStateError


def fresh_session():
    return RecoveryWorkflowSession(
        notice_text=Path("examples/notices/failed-rough-in.txt").read_text(),
        as_of=date(2026, 8, 10),
        roster={trade: Recipient(name=trade.value, phone="+13035550100") for trade in (Trade.ELECTRICAL, Trade.FRAMING, Trade.MECHANICAL)},
        messenger=RecordingMessenger(),
    )


def restore(session):
    messenger = RecordingMessenger()
    saved = RecoveryCheckpoint.model_validate_json(session.checkpoint().model_dump_json())
    return RecoveryWorkflowSession.restore(saved, messenger=messenger), messenger


def test_cold_restore_keeps_review_and_judgment_gates_without_replaying_outreach():
    original = fresh_session()
    first = original.start()
    restored, messenger = restore(original)
    assert messenger.deliveries == ()
    reviewed = restored.review(
        interrupt_id=first.interrupts[0].interrupt_id,
        review=CorrectionReview(citations=tuple(ReviewedCitation(
            citation_id=c.citation_id, trade=c.trade, closure_route=c.closure_route,
            evidence_requirements=tuple(c.evidence_requirements or ["Contractor must define required access proof"]),
        ) for c in first.notice.citations)),
    )
    prior = list(reviewed.deliveries)
    resumed, second_messenger = restore(restored)
    assert second_messenger.deliveries == ()
    if reviewed.interrupts:
        finished = resumed.resume(interrupt_id=reviewed.interrupts[0].interrupt_id, decision="Show the equipment access area in a wide photo")
    else:
        finished = resumed._snapshot()
    assert finished.deliveries[:len(prior)] == prior
    cold, third_messenger = restore(resumed)
    chased = cold.run_next_check(accepted_citation_ids={"1"})
    assert all(item.citation_id != "1" for item in third_messenger.deliveries)
    assert chased.notice == finished.notice
    assert chased.plan.as_of > finished.plan.as_of


def test_checkpoint_from_another_sdk_version_is_not_silently_replayed():
    session = fresh_session()
    session.start()
    checkpoint = session.checkpoint().model_copy(update={"strands_version": "incompatible"})
    messenger = RecordingMessenger()
    with pytest.raises(WorkflowStateError, match="original Strands"):
        RecoveryWorkflowSession.restore(checkpoint, messenger=messenger)
    assert messenger.deliveries == ()
