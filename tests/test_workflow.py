from datetime import date
from pathlib import Path

import pytest

from mettle.communication import RecordingMessenger, Recipient
from mettle.domain import ClosureRoute, Trade
from mettle.notice_parser import parse_notice
from mettle.workflow import (
    RecoveryWorkflowSession,
    CorrectionReview,
    ReviewedCitation,
    WorkflowConfigurationError,
    WorkflowStatus,
)


NOTICE = Path("examples/notices/failed-rough-in.txt").read_text(encoding="utf-8")
ROSTER = {
    Trade.ELECTRICAL: Recipient(name="Mike Alvarez", phone="+13035550101"),
    Trade.FRAMING: Recipient(name="Jen Ortiz", phone="+13035550102"),
    Trade.MECHANICAL: Recipient(name="Luis Vega", phone="+13035550103"),
}


def approve_corrections(session, snapshot):
    return session.review(
        interrupt_id=snapshot.interrupts[0].interrupt_id,
        review=CorrectionReview(
            citations=tuple(
                ReviewedCitation(
                    citation_id=citation.citation_id,
                    trade=citation.trade,
                    closure_route=ClosureRoute.PHOTO_EVIDENCE,
                    evidence_requirements=tuple(
                        citation.evidence_requirements
                        or ["Wide photo showing the completed correction and its location"]
                    ),
                )
                for citation in snapshot.notice.citations
            )
        ),
    )


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
    assert snapshot.interrupts[0].name == "correction-review"
    assert messenger.deliveries == ()

    completed = approve_corrections(session, snapshot)

    assert completed.status is WorkflowStatus.COMPLETED
    assert [item.citation_id for item in messenger.deliveries] == ["1", "2", "3"]
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

    completed = approve_corrections(session, interrupted)

    assert completed.status is WorkflowStatus.COMPLETED
    assert completed.contractor_decision is None
    assert completed.interrupts == []
    assert len(messenger.deliveries) == 3
    assert messenger.deliveries[-1].recipient.name == "Luis Vega"
    assert "Wide photo showing the completed correction" in messenger.deliveries[-1].body


def test_missing_trade_recipient_fails_before_any_message_is_recorded() -> None:
    messenger = RecordingMessenger()
    session = RecoveryWorkflowSession(
        notice_text=NOTICE,
        as_of=date(2026, 8, 10),
        roster={Trade.ELECTRICAL: ROSTER[Trade.ELECTRICAL]},
        messenger=messenger,
    )

    started = session.start()
    with pytest.raises(WorkflowConfigurationError, match="framing"):
        approve_corrections(session, started)

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


def test_strands_workflow_uses_injected_intake_without_changing_later_nodes() -> None:
    extracted: list[str] = []

    def intake(text: str):
        extracted.append(text)
        return parse_notice(text)

    messenger = RecordingMessenger()
    session = RecoveryWorkflowSession(
        notice_text=NOTICE,
        as_of=date(2026, 8, 10),
        roster=ROSTER,
        messenger=messenger,
        notice_extractor=intake,
    )

    snapshot = session.start()

    assert extracted == [NOTICE]
    assert snapshot.status is WorkflowStatus.INTERRUPTED
    assert messenger.deliveries == ()
    approve_corrections(session, snapshot)
    assert [item.citation_id for item in messenger.deliveries] == ["1", "2", "3"]


def _completed_session() -> tuple[RecoveryWorkflowSession, RecordingMessenger]:
    messenger = RecordingMessenger()
    session = RecoveryWorkflowSession(
        notice_text=NOTICE,
        as_of=date(2026, 8, 10),
        roster=ROSTER,
        messenger=messenger,
    )
    interrupted = session.start()
    approve_corrections(session, interrupted)
    return session, messenger


def test_chase_graph_replans_open_citations_at_the_next_checkpoint() -> None:
    session, messenger = _completed_session()

    snapshot = session.run_next_check(
        accepted_citation_ids={"1"},
        evidence_feedback={"2": "The close photo did not show the corrected wall location."},
    )

    assert snapshot.status is WorkflowStatus.COMPLETED
    assert snapshot.plan.as_of == date(2026, 8, 14)
    assert snapshot.plan.priority.value == "urgent"
    assert [item.citation_id for item in snapshot.plan.actions] == ["2", "3"]
    assert len(messenger.deliveries) == 5
    assert [item.citation_id for item in messenger.deliveries[-2:]] == ["2", "3"]
    assert all(item.scheduled_on == date(2026, 8, 14) for item in messenger.deliveries[-2:])
    assert "corrected wall location" in messenger.deliveries[-2].body


def test_chase_graph_interrupts_only_at_deadline_tradeoff() -> None:
    session, messenger = _completed_session()
    first = session.run_next_check(accepted_citation_ids=set())
    assert first.status is WorkflowStatus.COMPLETED

    critical = session.run_next_check(accepted_citation_ids={"1"})

    assert critical.status is WorkflowStatus.INTERRUPTED
    assert critical.plan.as_of == date(2026, 8, 15)
    assert critical.interrupts[0].name == "deadline-tradeoff"
    assert critical.interrupts[0].reason["open_citation_ids"] == ["2", "3"]
    assert len(messenger.deliveries) == 8

    resumed = session.resume(
        interrupt_id=critical.interrupts[0].interrupt_id,
        decision="Keep the current reinspection date and continue critical follow-ups.",
    )
    assert resumed.status is WorkflowStatus.COMPLETED
    assert resumed.deadline_decision.startswith("Keep the current")


def test_chase_graph_stops_all_outreach_when_every_citation_is_accepted() -> None:
    session, messenger = _completed_session()
    initial_count = len(messenger.deliveries)

    snapshot = session.run_next_check(accepted_citation_ids={"1", "2", "3"})

    assert snapshot.status is WorkflowStatus.COMPLETED
    assert snapshot.plan.actions == []
    assert snapshot.interrupts == []
    assert len(messenger.deliveries) == initial_count
