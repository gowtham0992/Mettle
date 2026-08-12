from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Trade(StrEnum):
    ELECTRICAL = "electrical"
    FRAMING = "framing"
    MECHANICAL = "mechanical"
    PLUMBING = "plumbing"
    GENERAL = "general"
    UNKNOWN = "unknown"


class Priority(StrEnum):
    ROUTINE = "routine"
    ATTENTION = "attention"
    URGENT = "urgent"
    CRITICAL = "critical"


class JudgmentKind(StrEnum):
    CODE_INTERPRETATION = "code_interpretation"
    DEADLINE_TRADEOFF = "deadline_tradeoff"
    FINAL_PACKET_APPROVAL = "final_packet_approval"


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    citation_id: str = Field(min_length=1, max_length=64)
    code_reference: str = Field(min_length=1, max_length=120)
    notice_text: str = Field(min_length=1, max_length=2_000)
    trade: Trade = Trade.UNKNOWN
    evidence_requirements: list[str] = Field(default_factory=list, max_length=10)
    ambiguity_reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_human_judgment_for_incomplete_work(self) -> Citation:
        reasons: list[str] = []
        if self.trade is Trade.UNKNOWN:
            reasons.append("the notice does not identify a recognized trade")
        if not self.evidence_requirements:
            reasons.append(
                "the notice does not state observable evidence requirements"
            )
        if not reasons:
            return self

        existing = self.ambiguity_reason or ""
        missing = [reason for reason in reasons if reason not in existing]
        if missing:
            combined = "; ".join(filter(None, [existing, *missing]))
            self.ambiguity_reason = combined
        return self


class InspectionNotice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notice_id: str = Field(min_length=1, max_length=120)
    issued_on: date
    reinspection_due_on: date
    property_label: str = Field(min_length=1, max_length=240)
    citations: list[Citation] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def validate_notice_invariants(self) -> InspectionNotice:
        if self.reinspection_due_on < self.issued_on:
            raise ValueError("reinspection deadline cannot precede issue date")
        citation_ids = [citation.citation_id for citation in self.citations]
        if len(citation_ids) != len(set(citation_ids)):
            raise ValueError("citation identifiers must be unique within a notice")
        for citation in self.citations:
            if any(len(item) > 500 for item in citation.evidence_requirements):
                raise ValueError("evidence requirements may not exceed 500 characters")
        return self


class FollowUpAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    citation_id: str
    trade: Trade
    priority: Priority
    message: str
    due_on: date


class JudgmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: JudgmentKind
    citation_id: str | None = None
    question: str
    reason: str


class CampaignPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notice_id: str
    as_of: date
    days_remaining: int
    priority: Priority
    actions: list[FollowUpAction]
    judgments: list[JudgmentRequest]
