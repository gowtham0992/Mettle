from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mettle.domain import Citation


class EvidenceSampleNotFound(ValueError):
    """Raised when a local evidence fixture is not in the trusted catalog."""


class EvidenceStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"


class EvidenceReviewDisposition(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"


class EvidenceAgentStep(BaseModel):
    """A safe, high-level trace of the evidence agent's bounded work."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    step: str = Field(min_length=1, max_length=80)
    status: str = Field(pattern=r"^(completed|interrupted)$")
    detail: str = Field(min_length=1, max_length=240)


class ContractorEvidenceRecord(BaseModel):
    """A human-reviewed source record, never a model certification."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    route: Literal["document_evidence", "physical_reinspection"]
    reference: str = Field(min_length=3, max_length=240)
    reviewer: str = Field(min_length=3, max_length=120)
    reviewed_on: date
    details: str = Field(min_length=20, max_length=4000)
    confirmed: bool = Field(strict=True)

    @model_validator(mode="after")
    def validate_record(self):
        if not self.confirmed:
            raise ValueError("contractor review must be explicitly confirmed")
        for name, minimum in (("reference", 3), ("reviewer", 3), ("details", 20)):
            normalized = " ".join(getattr(self, name).split())
            if len(normalized) < minimum:
                raise ValueError(f"{name} must contain meaningful text")
            object.__setattr__(self, name, normalized)
        return self


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
    agent_run: list[EvidenceAgentStep] = Field(default_factory=list)
    automated_status: EvidenceStatus | None = None
    contractor_decision: str | None = Field(default=None, max_length=500)
    contractor_record: ContractorEvidenceRecord | None = None


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
    "framing_plates_complete": _EvidenceSample(
        image_url="/static/evidence/framing-plates-visible-v2.png",
        capabilities=frozenset(
            {
                "close_view",
                "protection_plate_visible",
                "wide_view",
                "wall_location_visible",
            }
        ),
    ),
    "mechanical_access_wide": _EvidenceSample(
        image_url="/static/evidence/mechanical-access-wide.png",
        capabilities=frozenset(
            {
                "wide_view",
                "clearance_visible",
                "equipment_clearance_visible",
                "access_panel_open",
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
    if "equipment clearance" in normalized:
        capabilities.add("equipment_clearance_visible")
    if "access panel open" in normalized or "open access panel" in normalized:
        capabilities.add("access_panel_open")
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
            "This photo is missing visible proof of: "
            + "; ".join(missing)
            + ". Ask the trade for a replacement photo that shows each missing item."
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
