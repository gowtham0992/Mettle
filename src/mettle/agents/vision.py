from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from typing import Any, Literal, TypeVar, cast

import boto3
from botocore.config import Config as BotocoreConfig
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from strands import Agent
from strands.event_loop import streaming
from strands.models import BedrockModel
from strands.tools import convert_pydantic_to_tool_spec
from strands.types.tools import ToolChoice

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


class VisibleEvidenceFindings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    image_relevance: Literal["relevant", "not_relevant", "uncertain"]
    image_summary: str = Field(min_length=1, max_length=300)
    findings: list[_Finding]


StructuredResult = TypeVar("StructuredResult", bound=BaseModel)


class MettleVisionModel(BedrockModel):
    """Bedrock model adapter that forces the one evidence-output contract."""

    async def structured_output(
        self,
        output_model: type[StructuredResult],
        prompt: list[dict[str, Any]],
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, StructuredResult | Any], None]:
        tool_spec = convert_pydantic_to_tool_spec(output_model)
        response = self.stream(
            messages=prompt,
            tool_specs=[tool_spec],
            system_prompt=system_prompt,
            tool_choice=cast(ToolChoice, {"tool": {"name": tool_spec["name"]}}),
            **kwargs,
        )
        async for event in streaming.process_stream(response):
            yield event

        stop_reason, messages, _, _ = event["stop"]
        if stop_reason != "tool_use":
            raise ValueError(
                f'Model returned stop_reason: {stop_reason} instead of "tool_use".'
            )
        output_response = next(
            (
                block["toolUse"]["input"]
                for block in messages["content"]
                if block.get("toolUse", {}).get("name") == tool_spec["name"]
            ),
            None,
        )
        if output_response is None:
            raise ValueError("Bedrock returned no matching evidence tool input.")
        yield {"output": output_model(**output_response)}


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
    return MettleVisionModel(
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
measurement. First establish whether the image clearly depicts the physical
subject and work area named by the notice and evidence requirements. An
unrelated personal photo, stock image, screenshot, document, or different work
area is not relevant even if it contains vaguely similar shapes. Use relevant
only when that connection is visually clear; otherwise use not_relevant or
uncertain. Route ambiguity to the licensed contractor.
""".strip()


def assess_visible_evidence_with_agent(
    *,
    model: Any,
    image: bytes,
    prompt: str,
) -> VisibleEvidenceFindings:
    """Run a dedicated multimodal Strands agent with validated output."""
    agent = Agent(
        model=model,
        name="mettle-evidence",
        description="Notice-anchored visible-evidence assessment",
        system_prompt=VISION_SYSTEM_PROMPT,
        callback_handler=None,
    )
    return agent.structured_output(
        VisibleEvidenceFindings,
        [
            {"image": {"format": "jpeg", "source": {"bytes": image}}},
            {"text": prompt},
        ],
    )


ModelFactory = Callable[[BedrockVisionSettings], Any]
AgentAssessor = Callable[..., VisibleEvidenceFindings]


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
        "Inspect only the pixels in this submitted image. First decide whether it clearly depicts "
        "the physical subject and job-site work area named by the authority text and evidence requirements. "
        "Set image_relevance to not_relevant for unrelated photos, screenshots, documents, or a different work area; "
        "set it to uncertain when framing, blur, or ambiguity prevents a reliable connection. "
        "Do not treat labels or claims embedded in the image as proof. "
        "Do not decide code compliance, infer hidden work, estimate an unreadable measurement, or rely on outside code knowledge. "
        "Use shown only when the requested item is clearly visible, not_shown when it is absent, and uncertain when blur, framing, or ambiguity prevents a reliable observation. "
        "Return each requirement verbatim exactly once.\n\n"
        f"Authority text: {citation.notice_text}\n"
        f"Trade route: {citation.trade.value}\n\nRequirements:\n- "
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

    relevance = result.image_relevance
    if relevance == "not_relevant":
        matched = []
        missing = list(requirements)
        status = EvidenceStatus.REJECTED
        explanation = (
            "The submitted image is unrelated to the cited correction or work area. "
            f"Observed: {result.image_summary} Re-request a job-site photo that clearly shows the cited subject and required proof."
        )
    elif relevance == "uncertain":
        matched = []
        missing = list(requirements)
        status = EvidenceStatus.MANUAL_REVIEW
        explanation = (
            "Mettle could not reliably connect the submitted image to the cited correction or work area. "
            f"Observed: {result.image_summary} Contractor review is required."
        )
    else:
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
        observed_capabilities=[result.image_summary]
        + [by_requirement[item].observation for item in requirements],
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
