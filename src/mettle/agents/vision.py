from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, Protocol

import boto3
from botocore.config import Config as BotocoreConfig
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from mettle.domain import Citation
from mettle.evidence import EvidenceAssessment, EvidenceStatus


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


class ConverseClient(Protocol):
    def converse(self, **kwargs: Any) -> dict[str, Any]: ...


def _client(settings: BedrockVisionSettings) -> ConverseClient:
    config = BotocoreConfig(
        connect_timeout=5,
        read_timeout=45,
        retries={"total_max_attempts": 2, "mode": "standard"},
    )
    session = boto3.Session(
        profile_name=settings.profile,
        region_name=settings.region,
    )
    return session.client("bedrock-runtime", config=config)


def assess_photo_with_bedrock(
    *,
    citation: Citation,
    image: bytes,
    assessment_id: str,
    settings: BedrockVisionSettings | None = None,
    client_factory: Callable[[BedrockVisionSettings], ConverseClient] = _client,
) -> EvidenceAssessment:
    """Check only visible notice evidence, never construction-code compliance."""
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

    tool_name = "record_visible_evidence"
    schema = _VisionResult.model_json_schema()
    prompt = (
        "Inspect only the pixels in this job-site photo against each evidence requirement below. "
        "Do not decide code compliance, infer hidden work, estimate an unreadable measurement, or rely on outside code knowledge. "
        "Use shown only when the requested item is clearly visible, not_shown when it is absent, and uncertain when blur, framing, or ambiguity prevents a reliable observation. "
        "Return each requirement verbatim exactly once.\n\nRequirements:\n- "
        + "\n- ".join(requirements)
    )
    try:
        response = client_factory(selected).converse(
            modelId=selected.model_id,
            messages=[{
                "role": "user",
                "content": [
                    {"image": {"format": "jpeg", "source": {"bytes": image}}},
                    {"text": prompt},
                ],
            }],
            inferenceConfig={"maxTokens": selected.max_output_tokens, "temperature": 0},
            toolConfig={
                "tools": [{"toolSpec": {
                    "name": tool_name,
                    "description": "Record pixel-grounded findings for every requested evidence item.",
                    "inputSchema": {"json": schema},
                }}],
                "toolChoice": {"tool": {"name": tool_name}},
            },
        )
        blocks = response["output"]["message"]["content"]
        tool_inputs = [
            block["toolUse"]["input"]
            for block in blocks
            if block.get("toolUse", {}).get("name") == tool_name
        ]
        if len(tool_inputs) != 1:
            raise BedrockVisionError("Bedrock did not return one evidence assessment")
        result = _VisionResult.model_validate(tool_inputs[0])
    except (ClientError, BotoCoreError) as exc:
        raise BedrockVisionError("Bedrock could not assess the photo with the current AWS configuration") from exc
    except (KeyError, TypeError, ValidationError, BedrockVisionError) as exc:
        if isinstance(exc, BedrockVisionError):
            raise
        raise BedrockVisionError("Bedrock returned an invalid evidence assessment") from exc

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
    )
