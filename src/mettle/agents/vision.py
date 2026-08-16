from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

import boto3
from botocore.config import Config as BotocoreConfig
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from strands import Agent
from strands.models import BedrockModel

from mettle.domain import Citation
from mettle.evidence import EvidenceAgentStep, EvidenceAssessment, EvidenceStatus


class BedrockVisionError(RuntimeError):
    """A safe, caller-facing failure from the Bedrock vision boundary."""


class BedrockVisionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    region: str = Field(default="us-east-1", pattern=r"^[a-z]{2}(?:-gov)?-[a-z]+-\d$")
    model_id: str = "amazon.nova-lite-v1:0"
    profile: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._-]+$")
    max_output_tokens: int = Field(default=768, ge=256, le=2048)

    @field_validator("model_id")
    @classmethod
    def restrict_model(cls, value: str) -> str:
        if value not in {"amazon.nova-lite-v1:0", "us.amazon.nova-lite-v1:0"}:
            raise ValueError("model_id must select an approved Nova Lite model")
        return value


class _Finding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requirement: str
    verdict: Literal["shown", "not_shown", "uncertain"]
    observation: str = Field(min_length=1, max_length=300)


class _VisionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    findings: list[_Finding]


def create_vision_model(settings: BedrockVisionSettings) -> BedrockModel:
    config = BotocoreConfig(
        connect_timeout=5,
        read_timeout=45,
        retries={"total_max_attempts": 2, "mode": "standard"},
    )
    connection: dict[str, Any]
    if settings.profile is not None:
        connection = {
            "boto_session": boto3.Session(
                profile_name=settings.profile,
                region_name=settings.region,
            )
        }
    else:
        connection = {"region_name": settings.region}
    return BedrockModel(
        **connection,
        model_id=settings.model_id,
        boto_client_config=config,
        max_tokens=settings.max_output_tokens,
        temperature=0.0,
        streaming=False,
    )


VISION_SYSTEM_PROMPT = """
You are Mettle's visible-evidence specialist. Compare only observable pixels
with requirements grounded in the failed-inspection notice. Never interpret a
building code, infer hidden work, certify compliance, or estimate an unreadable
measurement. Route ambiguity to the licensed contractor.
""".strip()


def assess_visible_evidence_with_agent(
    *,
    model: Any,
    image: bytes,
    prompt: str,
) -> _VisionResult:
    """Run a dedicated multimodal Strands agent with validated output."""
    agent = Agent(
        model=model,
        name="mettle-evidence",
        description="Notice-anchored visible-evidence assessment",
        system_prompt=VISION_SYSTEM_PROMPT,
        callback_handler=None,
    )
    return agent.structured_output(
        _VisionResult,
        [
            {"image": {"format": "jpeg", "source": {"bytes": image}}},
            {"text": prompt},
        ],
    )


ModelFactory = Callable[[BedrockVisionSettings], Any]
AgentAssessor = Callable[..., _VisionResult]


def assess_photo_with_bedrock(
    *,
    citation: Citation,
    image: bytes,
    assessment_id: str,
    settings: BedrockVisionSettings | None = None,
    model_factory: ModelFactory = create_vision_model,
    agent_assessor: AgentAssessor = assess_visible_evidence_with_agent,
) -> EvidenceAssessment:
    """Use a dedicated Strands agent, then enforce deterministic safety policy."""
    selected = settings or BedrockVisionSettings()
    requirements = list(citation.evidence_requirements)
    if not requirements:
        return EvidenceAssessment(
            assessment_id=assessment_id,
            citation_id=citation.citation_id,
            sample_id=f"upload_{assessment_id}",
            image_url="",
            status=EvidenceStatus.MANUAL_REVIEW,
            missing_requirements=["The notice does not define observable evidence."],
            explanation="Contractor review is required because the notice does not define visible evidence requirements.",
        )

    prompt = (
        "Inspect only the pixels in this job-site photo against each evidence requirement below. "
        "Do not decide code compliance, infer hidden work, estimate an unreadable measurement, or rely on outside code knowledge. "
        "Use shown only when the requested item is clearly visible, not_shown when it is absent, and uncertain when blur, framing, or ambiguity prevents a reliable observation. "
        "Return each requirement verbatim exactly once.\n\nRequirements:\n- "
        + "\n- ".join(requirements)
    )
    try:
        result = agent_assessor(
            model=model_factory(selected),
            image=image,
            prompt=prompt,
        )
    except (ClientError, BotoCoreError) as exc:
        raise BedrockVisionError(
            "The Strands evidence agent could not reach Bedrock with the current AWS configuration"
        ) from exc
    except (KeyError, TypeError, ValidationError, BedrockVisionError) as exc:
        if isinstance(exc, BedrockVisionError):
            raise
        raise BedrockVisionError(
            "The Strands evidence agent returned an invalid assessment"
        ) from exc
    except Exception as exc:
        raise BedrockVisionError(
            "The Strands evidence agent could not complete the assessment"
        ) from exc

    by_requirement = {finding.requirement: finding for finding in result.findings}
    if len(result.findings) != len(requirements) or set(by_requirement) != set(requirements):
        raise BedrockVisionError("Bedrock did not assess every notice requirement exactly once")

    matched = [item for item in requirements if by_requirement[item].verdict == "shown"]
    uncertain = [item for item in requirements if by_requirement[item].verdict == "uncertain"]
    missing = [item for item in requirements if by_requirement[item].verdict != "shown"]
    if uncertain:
        status = EvidenceStatus.MANUAL_REVIEW
        explanation = "The photo is ambiguous for: " + "; ".join(uncertain) + ". Contractor review is required."
    elif missing:
        status = EvidenceStatus.REJECTED
        detail = "; ".join(by_requirement[item].observation for item in missing)
        explanation = f"The photo does not visibly show every notice requirement. Re-request: {detail}"
    else:
        status = EvidenceStatus.ACCEPTED
        explanation = "The photo visibly shows every item requested by the notice. Acceptance records evidence sufficiency, not code compliance."

    return EvidenceAssessment(
        assessment_id=assessment_id,
        citation_id=citation.citation_id,
        sample_id=f"upload_{assessment_id}",
        image_url="",
        status=status,
        observed_capabilities=[by_requirement[item].observation for item in requirements],
        matched_requirements=matched,
        missing_requirements=missing,
        explanation=explanation,
        agent_run=[
            EvidenceAgentStep(
                step="Ground requirements",
                status="completed",
                detail=f"Bound the run to {len(requirements)} requirement(s) quoted from citation {citation.citation_id}.",
            ),
            EvidenceAgentStep(
                step="Inspect visible evidence",
                status="completed",
                detail=f"Strands Evidence Agent used {selected.model_id} to inspect the submitted image.",
            ),
            EvidenceAgentStep(
                step="Apply safety policy",
                status="interrupted" if status is EvidenceStatus.MANUAL_REVIEW else "completed",
                detail=(
                    "Ambiguity was routed to contractor judgment; no compliance decision was made."
                    if status is EvidenceStatus.MANUAL_REVIEW
                    else "Deterministic policy converted the grounded findings into an evidence-sufficiency result."
                ),
            ),
        ],
    )
