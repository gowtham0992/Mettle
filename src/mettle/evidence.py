from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from mettle.domain import Citation


class EvidenceSampleNotFound(ValueError):
    """Raised when a local evidence fixture is not in the trusted catalog."""


class EvidenceStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"


class EvidenceAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    assessment_id: str
    citation_id: str
    sample_id: str
    image_url: str
    status: EvidenceStatus
    observed_capabilities: list[str] = Field(default_factory=list)
    matched_requirements: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    explanation: str


@dataclass(frozen=True)
class _EvidenceSample:
    image_url: str
    capabilities: frozenset[str]


_SAMPLES = {
    "panel_closeup_insufficient": _EvidenceSample(
        image_url="/static/evidence/panel-closeup-insufficient.png",
        capabilities=frozenset({"panel_visible", "close_view"}),
    ),
    "panel_wide_measured": _EvidenceSample(
        image_url="/static/evidence/panel-wide-measured.png",
        capabilities=frozenset(
            {
                "panel_visible",
                "wide_view",
                "panel_area_visible",
                "scale_visible",
                "clearance_visible",
            }
        ),
    ),
}


def _required_capabilities(requirement: str) -> frozenset[str]:
    normalized = " ".join(requirement.lower().split())
    capabilities: set[str] = set()
    if "wide photo" in normalized or "wide shot" in normalized:
        capabilities.add("wide_view")
    if "service panel area" in normalized or "complete panel area" in normalized:
        capabilities.add("panel_area_visible")
    if "tape measure" in normalized or "measurement" in normalized:
        capabilities.add("scale_visible")
    if "clearance" in normalized:
        capabilities.add("clearance_visible")
    if "close photo" in normalized or "close-up" in normalized:
        capabilities.add("close_view")
    if "protection plate" in normalized:
        capabilities.add("protection_plate_visible")
    if "wall location" in normalized:
        capabilities.add("wall_location_visible")
    return frozenset(capabilities)


def assess_sample(
    *,
    citation: Citation,
    sample_id: str,
    assessment_id: str | None = None,
) -> EvidenceAssessment:
    """Assess a trusted local fixture against requirements quoted by the notice."""
    sample = _SAMPLES.get(sample_id)
    if sample is None:
        raise EvidenceSampleNotFound("evidence sample is not available")

    matched: list[str] = []
    missing: list[str] = []
    unknown: list[str] = []
    for requirement in citation.evidence_requirements:
        required = _required_capabilities(requirement)
        if not required:
            unknown.append(requirement)
        elif required.issubset(sample.capabilities):
            matched.append(requirement)
        else:
            missing.append(requirement)

    if not citation.evidence_requirements or unknown:
        status = EvidenceStatus.MANUAL_REVIEW
        missing.extend(unknown or ["The notice does not define observable evidence."])
        explanation = (
            "Mettle cannot evaluate one or more notice requirements with the local "
            "rule adapter. Contractor review is required."
        )
    elif missing:
        status = EvidenceStatus.REJECTED
        explanation = (
            "This photo does not prove the notice requirements. Ask for a wider shot "
            "that shows the full panel area and a visible tape measure for clearance."
        )
    else:
        status = EvidenceStatus.ACCEPTED
        explanation = (
            "The photo shows every observable element requested by the notice. "
            "Acceptance records evidence sufficiency, not code compliance."
        )

    return EvidenceAssessment(
        assessment_id=assessment_id or f"assessment-{citation.citation_id}-{sample_id}",
        citation_id=citation.citation_id,
        sample_id=sample_id,
        image_url=sample.image_url,
        status=status,
        observed_capabilities=sorted(sample.capabilities),
        matched_requirements=matched,
        missing_requirements=missing,
        explanation=explanation,
    )
