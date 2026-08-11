from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


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

    citation_id: str = Field(min_length=1)
    code_reference: str = Field(min_length=1)
    notice_text: str = Field(min_length=1)
    trade: Trade = Trade.UNKNOWN
    evidence_requirements: list[str] = Field(default_factory=list)
    ambiguity_reason: str | None = None


class InspectionNotice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notice_id: str = Field(min_length=1)
    issued_on: date
    reinspection_due_on: date
    property_label: str = Field(min_length=1)
    citations: list[Citation] = Field(min_length=1)


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
