from datetime import date

import pytest

import mettle.agents.intake as intake
from mettle.domain import Citation, InspectionNotice, Trade


SOURCE = """Contractor-supplied setup details
Permit: SYNTHETIC-REVIEW-0906
Property: Redacted test job
Inspection date: 2026-09-05
Reinspection deadline: 2026-09-12

Original report
SYNTHETIC REVIEW ONLY — NOT A REAL JOB
Inspection correction comments:
1. Remove stored materials from in front of the electrical panel. Provide a wide photograph showing the clear working space.
2. Install protective plates where the framing was bored near the stud edge. Provide a photograph showing each corrected location.
"""


def extract(monkeypatch, source=SOURCE):
    class FakeAgent:
        def structured_output(self, *_args):
            return InspectionNotice(
                notice_id="CITATION 1", property_label="Invented job",
                issued_on=date(2026, 9, 1), reinspection_due_on=date(2026, 9, 20),
                citations=[Citation(
                    citation_id="2", code_reference="NEC 110.3(B)",
                    notice_text="Install protective plates where the framing was bored near the stud edge. Provide a photograph showing each corrected location.",
                    trade=Trade.FRAMING, evidence_requirements=[],
                )],
            )
    monkeypatch.setattr(intake, "create_intake_agent", lambda **_: FakeAgent())
    return intake.extract_notice_with_agent(source)


def test_numbered_source_preserves_every_correction(monkeypatch):
    result = extract(monkeypatch)
    assert [c.citation_id for c in result.citations] == ["1", "2"]
    assert result.citations[0].notice_text.startswith("Remove stored materials")


def test_source_headers_override_model_inventions(monkeypatch):
    result = extract(monkeypatch)
    assert (result.notice_id, result.property_label) == ("SYNTHETIC-REVIEW-0906", "Redacted test job")
    assert (result.issued_on, result.reinspection_due_on) == (date(2026, 9, 5), date(2026, 9, 12))


def test_absent_codes_are_not_invented(monkeypatch):
    assert all(c.code_reference == "Not stated in notice" for c in extract(monkeypatch).citations)


def test_document_as_a_verb_does_not_override_explicit_photo_proof(monkeypatch):
    source = SOURCE.split("Original report")[0] + "1. Document the installed metal protection plate. Provide a close photograph showing the plate attached to the wood stud."
    result = extract(monkeypatch, source)
    assert result.citations[0].closure_route == "photo_evidence"
    assert result.citations[0].evidence_requirements == ["Provide a close photograph showing the plate attached to the wood stud."]


def test_explicit_photo_requirements_survive_model_omission(monkeypatch):
    result = extract(monkeypatch)
    assert result.citations[-1].evidence_requirements == ["Provide a photograph showing each corrected location."]
    assert "does not state observable" not in (result.citations[-1].ambiguity_reason or "")


def test_unsegmentable_source_fails_closed(monkeypatch):
    with pytest.raises(ValueError):
        extract(monkeypatch, "Unstructured text without identifiable corrections or job details")


def test_labeled_evidence_is_retained_without_code_based_defaults(monkeypatch):
    headers = SOURCE.split("Original report")[0]
    result = extract(monkeypatch, headers + """CITATION A
CODE: NEC 110.26
TRADE: electrical
FINDING: Clear the panel area.
EVIDENCE: Wide photo showing the clear floor; Close photo of the panel
END CITATION
CITATION B
CODE: IRC R602.6
TRADE: framing
FINDING: Protect bored studs.
END CITATION
""")
    assert [c.citation_id for c in result.citations] == ["A", "B"]
    assert result.citations[0].evidence_requirements == [
        "Wide photo showing the clear floor", "Close photo of the panel",
    ]
    assert result.citations[1].evidence_requirements == []


@pytest.mark.parametrize("instruction, route", [
    ("Provide the manufacturer document.", "document_evidence"),
    ("On-site inspector verification is required.", "physical_reinspection"),
])
def test_non_photo_proof_keeps_required_method(monkeypatch, instruction, route):
    result = extract(monkeypatch, SOURCE.split("Original report")[0] +
                     "1. Correct the equipment installation. " + instruction)
    assert result.citations[0].evidence_requirements == [instruction]
    assert result.citations[0].closure_route == route
