from datetime import date

import pytest

from mettle.campaign import build_campaign_plan, next_campaign_check
from mettle.domain import JudgmentKind, Priority
from mettle.notice_parser import parse_notice


NOTICE = """
NOTICE ID: TEST-CAMPAIGN
ISSUED: 2026-08-01
REINSPECTION DEADLINE: 2026-08-10
PROPERTY: Synthetic property

CITATION READY
CODE: NEC 110.26
TRADE: Electrical
FINDING: Maintain working clearance at the panel.
EVIDENCE: Wide panel photo; clearance measurement photo
END CITATION

CITATION JUDGMENT
CODE: LOCAL 1
FINDING: Correct the listed installation.
END CITATION
"""


def test_campaign_escalates_as_deadline_approaches() -> None:
    notice = parse_notice(NOTICE)

    routine = build_campaign_plan(notice, as_of=date(2026, 8, 1))
    critical = build_campaign_plan(notice, as_of=date(2026, 8, 9))

    assert routine.priority is Priority.ROUTINE
    assert routine.actions[0].due_on == date(2026, 8, 3)
    assert routine.actions[0].message.startswith("Please review")

    assert critical.priority is Priority.CRITICAL
    assert critical.actions[0].due_on == date(2026, 8, 9)
    assert critical.actions[0].message.startswith("Deadline-critical")
    assert any(
        judgment.kind is JudgmentKind.DEADLINE_TRADEOFF
        for judgment in critical.judgments
    )


def test_campaign_never_turns_ambiguous_citation_into_trade_instruction() -> None:
    notice = parse_notice(NOTICE)
    plan = build_campaign_plan(notice, as_of=date(2026, 8, 5))

    assert [action.citation_id for action in plan.actions] == ["READY"]
    judgment = next(
        item for item in plan.judgments if item.citation_id == "JUDGMENT"
    )
    assert judgment.kind is JudgmentKind.CODE_INTERPRETATION
    assert "recognized trade" in judgment.reason
    assert "evidence requirements" in judgment.reason


def test_next_campaign_check_moves_between_meaningful_deadline_thresholds() -> None:
    deadline = date(2026, 8, 17)

    assert next_campaign_check(date(2026, 8, 10), deadline) == date(2026, 8, 14)
    assert next_campaign_check(date(2026, 8, 14), deadline) == date(2026, 8, 15)
    assert next_campaign_check(date(2026, 8, 15), deadline) == date(2026, 8, 16)
    assert next_campaign_check(date(2026, 8, 16), deadline) == deadline
    with pytest.raises(ValueError, match="deadline has been reached"):
        next_campaign_check(deadline, deadline)
