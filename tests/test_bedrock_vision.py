from types import SimpleNamespace

import pytest
import mettle.agents.vision as vision_module

from mettle.agents.vision import (
    BedrockVisionError,
    BedrockVisionSettings,
    MettleVisionModel,
    VisibleEvidenceFindings,
    assess_visible_evidence_with_agent,
    assess_photo_with_bedrock,
    create_vision_model,
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


def _finding(requirement: str, verdict: str, observation: str):
    return {"requirement": requirement, "verdict": verdict, "observation": observation}


def _run_agent(
    findings,
    capture=None,
    *,
    image_relevance="relevant",
    image_summary="The cited job-site subject and work area are visible.",
):
    def assessor(**kwargs):
        if capture is not None:
            capture.update(kwargs)
        return VisibleEvidenceFindings.model_validate(
            {
                "image_relevance": image_relevance,
                "image_summary": image_summary,
                "findings": findings,
            }
        )
    return assessor


def test_vision_accepts_only_when_every_notice_requirement_is_visibly_shown() -> None:
    findings = [
        _finding(CITATION.evidence_requirements[0], "shown", "The full panel and surrounding work area are visible."),
        _finding(CITATION.evidence_requirements[1], "shown", "A tape measure is visible across the clearance."),
    ]
    captured = {}
    model = object()

    result = assess_photo_with_bedrock(
        citation=CITATION,
        image=b"safe-jpeg",
        assessment_id="evidence-1",
        model_factory=lambda _settings: model,
        agent_assessor=_run_agent(findings, captured),
    )

    assert result.status is EvidenceStatus.ACCEPTED
    assert result.matched_requirements == CITATION.evidence_requirements
    assert captured["image"] == b"safe-jpeg"
    assert captured["model"] is model
    assert "Authority text:" in captured["prompt"]
    assert "not_relevant" in captured["prompt"]
    assert result.agent_run[1].step == "Inspect visible evidence"


def test_vision_rejects_unrelated_image_even_if_requirement_findings_claim_shown() -> None:
    findings = [
        _finding(CITATION.evidence_requirements[0], "shown", "A rectangular object is visible."),
        _finding(CITATION.evidence_requirements[1], "shown", "A long narrow object is visible."),
    ]

    def unrelated_assessor(**_kwargs):
        return SimpleNamespace(
            image_relevance="not_relevant",
            image_summary="A vacation landscape with no electrical panel or job-site work area.",
            findings=_run_agent(findings)().findings,
        )

    result = assess_photo_with_bedrock(
        citation=CITATION,
        image=b"normalized-unrelated-jpeg",
        assessment_id="evidence-unrelated",
        model_factory=lambda _settings: object(),
        agent_assessor=unrelated_assessor,
    )

    assert result.status is EvidenceStatus.REJECTED
    assert result.matched_requirements == []
    assert result.missing_requirements == CITATION.evidence_requirements
    assert "unrelated" in result.explanation.lower()


def test_vision_routes_uncertain_scene_identity_to_contractor_review() -> None:
    findings = [
        _finding(CITATION.evidence_requirements[0], "uncertain", "The image is tightly cropped."),
        _finding(CITATION.evidence_requirements[1], "uncertain", "No readable scale is visible."),
    ]

    result = assess_photo_with_bedrock(
        citation=CITATION,
        image=b"normalized-ambiguous-jpeg",
        assessment_id="evidence-ambiguous-scene",
        model_factory=lambda _settings: object(),
        agent_assessor=_run_agent(
            findings,
            image_relevance="uncertain",
            image_summary="A cropped surface that cannot be tied to the cited panel area.",
        ),
    )

    assert result.status is EvidenceStatus.MANUAL_REVIEW
    assert result.matched_requirements == []
    assert result.missing_requirements == CITATION.evidence_requirements
    assert "contractor review" in result.explanation.lower()


def test_vision_rejects_with_specific_rerequest_when_an_item_is_not_shown() -> None:
    findings = [
        _finding(CITATION.evidence_requirements[0], "shown", "The panel area is visible."),
        _finding(CITATION.evidence_requirements[1], "not_shown", "Send a wider photo with the tape measure markings readable."),
    ]

    result = assess_photo_with_bedrock(
        citation=CITATION,
        image=b"safe-jpeg",
        assessment_id="evidence-2",
        model_factory=lambda _settings: object(),
        agent_assessor=_run_agent(findings),
    )

    assert result.status is EvidenceStatus.REJECTED
    assert result.missing_requirements == [CITATION.evidence_requirements[1]]
    assert "tape measure markings" in result.explanation


def test_vision_routes_uncertainty_to_the_contractor() -> None:
    findings = [
        _finding(CITATION.evidence_requirements[0], "shown", "The panel area is visible."),
        _finding(CITATION.evidence_requirements[1], "uncertain", "The measurement markings are blurred."),
    ]

    result = assess_photo_with_bedrock(
        citation=CITATION,
        image=b"safe-jpeg",
        assessment_id="evidence-3",
        model_factory=lambda _settings: object(),
        agent_assessor=_run_agent(findings),
    )

    assert result.status is EvidenceStatus.MANUAL_REVIEW
    assert "contractor review" in result.explanation.lower()
    assert result.agent_run[-1].status == "interrupted"


def test_vision_fails_closed_if_model_changes_or_omits_requirements() -> None:
    findings = [
        _finding(CITATION.evidence_requirements[0], "shown", "Visible."),
    ]

    with pytest.raises(BedrockVisionError, match="every notice requirement"):
        assess_photo_with_bedrock(
            citation=CITATION,
            image=b"safe-jpeg",
            assessment_id="evidence-4",
            model_factory=lambda _settings: object(),
            agent_assessor=_run_agent(findings),
        )


def test_vision_settings_reject_more_expensive_or_text_only_models() -> None:
    with pytest.raises(ValueError, match="Nova Lite"):
        BedrockVisionSettings(model_id="anthropic.claude-sonnet-4-20250514-v1:0")


def test_vision_model_uses_non_streaming_converse_to_preserve_least_privilege(monkeypatch) -> None:
    captured = {}

    class FakeModel:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(vision_module, "MettleVisionModel", FakeModel)
    create_vision_model(BedrockVisionSettings())

    assert captured["streaming"] is False
    assert captured["model_id"] == "amazon.nova-lite-v1:0"


def test_evidence_agent_receives_multimodal_prompt_and_structured_contract(monkeypatch) -> None:
    captured = {}

    class FakeAgent:
        def __init__(self, **kwargs):
            captured["agent"] = kwargs

        def structured_output(self, output_model, prompt):
            captured["output_model"] = output_model
            captured["prompt"] = prompt
            return VisibleEvidenceFindings.model_validate({
                "image_relevance": "relevant",
                "image_summary": "The electrical panel and surrounding work area are visible.",
                "findings": [
                    _finding(CITATION.evidence_requirements[0], "shown", "Visible."),
                    _finding(CITATION.evidence_requirements[1], "shown", "Visible."),
                ]
            })

    monkeypatch.setattr(vision_module, "Agent", FakeAgent)
    result = assess_visible_evidence_with_agent(
        model="bounded-model",
        image=b"normalized-jpeg",
        prompt="Inspect grounded requirements",
    )

    assert captured["agent"]["name"] == "mettle-evidence"
    assert captured["agent"]["model"] == "bounded-model"
    assert captured["output_model"] is VisibleEvidenceFindings
    assert captured["prompt"][0]["image"]["source"]["bytes"] == b"normalized-jpeg"
    assert result.image_relevance == "relevant"
    assert result.findings[0].verdict == "shown"
