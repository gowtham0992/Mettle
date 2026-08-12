import pytest

from mettle.agents.vision import (
    BedrockVisionError,
    BedrockVisionSettings,
    assess_photo_with_bedrock,
)
from mettle.domain import Citation, Trade
from mettle.evidence import EvidenceStatus


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


class FakeClient:
    def __init__(self, findings):
        self.findings = findings
        self.request = None

    def converse(self, **kwargs):
        self.request = kwargs
        return {
            "output": {"message": {"content": [{"toolUse": {
                "name": "record_visible_evidence",
                "input": {"findings": self.findings},
            }}]}}
        }


def _finding(requirement: str, verdict: str, observation: str):
    return {"requirement": requirement, "verdict": verdict, "observation": observation}


def test_vision_accepts_only_when_every_notice_requirement_is_visibly_shown() -> None:
    fake = FakeClient([
        _finding(CITATION.evidence_requirements[0], "shown", "The full panel and surrounding work area are visible."),
        _finding(CITATION.evidence_requirements[1], "shown", "A tape measure is visible across the clearance."),
    ])

    result = assess_photo_with_bedrock(
        citation=CITATION,
        image=b"safe-jpeg",
        assessment_id="evidence-1",
        client_factory=lambda _settings: fake,
    )

    assert result.status is EvidenceStatus.ACCEPTED
    assert result.matched_requirements == CITATION.evidence_requirements
    assert fake.request["messages"][0]["content"][0]["image"]["source"]["bytes"] == b"safe-jpeg"
    assert fake.request["toolConfig"]["toolChoice"] == {"tool": {"name": "record_visible_evidence"}}


def test_vision_rejects_with_specific_rerequest_when_an_item_is_not_shown() -> None:
    fake = FakeClient([
        _finding(CITATION.evidence_requirements[0], "shown", "The panel area is visible."),
        _finding(CITATION.evidence_requirements[1], "not_shown", "Send a wider photo with the tape measure markings readable."),
    ])

    result = assess_photo_with_bedrock(
        citation=CITATION,
        image=b"safe-jpeg",
        assessment_id="evidence-2",
        client_factory=lambda _settings: fake,
    )

    assert result.status is EvidenceStatus.REJECTED
    assert result.missing_requirements == [CITATION.evidence_requirements[1]]
    assert "tape measure markings" in result.explanation


def test_vision_routes_uncertainty_to_the_contractor() -> None:
    fake = FakeClient([
        _finding(CITATION.evidence_requirements[0], "shown", "The panel area is visible."),
        _finding(CITATION.evidence_requirements[1], "uncertain", "The measurement markings are blurred."),
    ])

    result = assess_photo_with_bedrock(
        citation=CITATION,
        image=b"safe-jpeg",
        assessment_id="evidence-3",
        client_factory=lambda _settings: fake,
    )

    assert result.status is EvidenceStatus.MANUAL_REVIEW
    assert "contractor review" in result.explanation.lower()


def test_vision_fails_closed_if_model_changes_or_omits_requirements() -> None:
    fake = FakeClient([
        _finding(CITATION.evidence_requirements[0], "shown", "Visible."),
    ])

    with pytest.raises(BedrockVisionError, match="every notice requirement"):
        assess_photo_with_bedrock(
            citation=CITATION,
            image=b"safe-jpeg",
            assessment_id="evidence-4",
            client_factory=lambda _settings: fake,
        )


def test_vision_settings_reject_more_expensive_or_text_only_models() -> None:
    with pytest.raises(ValueError, match="Nova Lite"):
        BedrockVisionSettings(model_id="anthropic.claude-sonnet-4-20250514-v1:0")
