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


def test_parse_representative_municipal_comments_derives_recovery_fields() -> None:
    notice = parse_notice(
        """
DOUGLAS COUNTY BUILDING DIVISION
INSPECTION CORRECTION NOTICE
Permit: DEMO-2026-0417
Inspection date: 08/07/2026
Property: 100 Demo Way, Castle Pines, CO
Corrections must be completed before reinspection on 08/17/2026.

Inspection comments:
1. NEC 110.26 — Maintain the required working clearance in front of the service panel.
2. IRC R602.6 — Protect bored framing members where the edge distance is less than required.
3. IMC 304.10 — Provide clearance and service access at the installed mechanical equipment.
"""
    )

    assert notice.notice_id == "DEMO-2026-0417"
    assert notice.issued_on == date(2026, 8, 7)
    assert notice.reinspection_due_on == date(2026, 8, 17)
    assert [citation.code_reference for citation in notice.citations] == [
        "NEC 110.26",
        "IRC R602.6",
        "IMC 304.10",
    ]
    assert [citation.trade for citation in notice.citations] == [
        Trade.ELECTRICAL,
        Trade.FRAMING,
        Trade.MECHANICAL,
    ]
    assert notice.citations[0].evidence_requirements == [
        "Wide photo showing the complete service panel area",
        "Photo with a tape measure showing the working clearance",
    ]
    assert notice.citations[2].evidence_requirements == []
    assert "does not state observable evidence requirements" in (
        notice.citations[2].ambiguity_reason or ""
    )


def test_parse_numbered_corrections_accepts_iso_dates_and_site_alias() -> None:
    notice = parse_notice(
        """
CORRECTION NOTICE #CN-82
Date issued: 2026-08-07
Reinspection required by: 2026-08-17
Site: 200 Example Street

Items requiring correction
1) [NEC 110.26] Maintain working clearance at the electrical panel.
2) IRC R602.6: Install protection plates at bored framing members.
"""
    )

    assert notice.notice_id == "CN-82"
    assert notice.property_label == "200 Example Street"
    assert len(notice.citations) == 2
    assert notice.citations[1].notice_text == (
        "Install protection plates at bored framing members."
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
