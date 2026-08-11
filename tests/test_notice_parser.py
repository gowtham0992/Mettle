from datetime import date

import pytest

from mettle.domain import Trade
from mettle.notice_parser import NoticeParseError, parse_notice


def test_parse_notice_preserves_citation_language_and_evidence() -> None:
    notice = parse_notice(
        """
NOTICE ID: TEST-1
ISSUED: 2026-08-01
REINSPECTION DEADLINE: 2026-08-10
PROPERTY: Synthetic property

CITATION A
CODE: NEC 110.26
TRADE: Electrical
FINDING: Maintain the required working clearance in front of the service panel.
EVIDENCE: Wide photo of panel; tape-measure photo of clearance
END CITATION
"""
    )

    assert notice.notice_id == "TEST-1"
    assert notice.reinspection_due_on == date(2026, 8, 10)
    assert notice.citations[0].trade is Trade.ELECTRICAL
    assert notice.citations[0].notice_text == (
        "Maintain the required working clearance in front of the service panel."
    )
    assert notice.citations[0].evidence_requirements == [
        "Wide photo of panel",
        "tape-measure photo of clearance",
    ]


def test_parse_notice_routes_missing_evidence_to_ambiguity() -> None:
    notice = parse_notice(
        """
NOTICE ID: TEST-2
ISSUED: 2026-08-01
REINSPECTION DEADLINE: 2026-08-10
PROPERTY: Synthetic property

CITATION B
CODE: IMC 304.10
TRADE: Mechanical
FINDING: Provide service access at the equipment.
END CITATION
"""
    )

    citation = notice.citations[0]
    assert citation.evidence_requirements == []
    assert citation.ambiguity_reason == (
        "the notice does not state observable evidence requirements"
    )


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "notice is empty"),
        (
            "NOTICE ID: X\nISSUED: 2026-08-01",
            "missing notice fields",
        ),
        (
            """
NOTICE ID: X
ISSUED: 2026-08-10
REINSPECTION DEADLINE: 2026-08-01
PROPERTY: Synthetic
CITATION 1
CODE: X
FINDING: X
END CITATION
""",
            "cannot precede",
        ),
    ],
)
def test_parse_notice_rejects_unsafe_or_incomplete_input(text: str, message: str) -> None:
    with pytest.raises(NoticeParseError, match=message):
        parse_notice(text)
