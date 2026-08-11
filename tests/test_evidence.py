from mettle.domain import Citation, Trade
from mettle.evidence import EvidenceStatus, assess_sample


CITATION = Citation(
    citation_id="1",
    code_reference="NEC 110.26",
    notice_text="Maintain the required working clearance in front of the panel.",
    trade=Trade.ELECTRICAL,
    evidence_requirements=[
        "Wide photo showing the complete service panel area",
        "Photo with a tape measure showing the clearance",
    ],
)


def test_closeup_is_rejected_with_specific_missing_requirements() -> None:
    assessment = assess_sample(
        citation=CITATION,
        sample_id="panel_closeup_insufficient",
    )

    assert assessment.status is EvidenceStatus.REJECTED
    assert assessment.matched_requirements == []
    assert assessment.missing_requirements == CITATION.evidence_requirements
    assert "wider shot" in assessment.explanation.lower()


def test_wide_measured_photo_satisfies_notice_anchored_requirements() -> None:
    assessment = assess_sample(
        citation=CITATION,
        sample_id="panel_wide_measured",
    )

    assert assessment.status is EvidenceStatus.ACCEPTED
    assert assessment.missing_requirements == []
    assert assessment.matched_requirements == CITATION.evidence_requirements


def test_unrecognized_requirement_routes_to_manual_review() -> None:
    citation = CITATION.model_copy(
        update={"evidence_requirements": ["Inspector-specific commissioning record"]}
    )

    assessment = assess_sample(citation=citation, sample_id="panel_wide_measured")

    assert assessment.status is EvidenceStatus.MANUAL_REVIEW
    assert "cannot evaluate" in assessment.explanation.lower()
