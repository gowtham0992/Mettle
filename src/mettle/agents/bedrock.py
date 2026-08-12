from __future__ import annotations

from collections.abc import Callable
from typing import Any

import boto3
from botocore.config import Config as BotocoreConfig
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel, ConfigDict, Field, field_validator
from strands.models import BedrockModel

from mettle.agents.intake import extract_notice_with_agent
from mettle.domain import InspectionNotice


class BedrockIntakeError(RuntimeError):
    """A safe, caller-facing failure from the Bedrock intake boundary."""


class BedrockIntakeSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    region: str = Field(
        default="us-east-1",
        min_length=9,
        max_length=32,
        pattern=r"^[a-z]{2}(?:-gov)?-[a-z]+-\d$",
    )
    model_id: str = Field(
        default="amazon.nova-micro-v1:0",
        min_length=3,
        max_length=200,
        pattern=r"^[A-Za-z0-9._:/-]+$",
    )
    profile: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9._-]+$",
    )
    max_input_characters: int = Field(default=30_000, ge=1_000, le=100_000)
    max_output_tokens: int = Field(default=2_048, ge=256, le=4_096)

    @field_validator("model_id")
    @classmethod
    def restrict_model_to_low_cost_intake(cls, value: str) -> str:
        allowed = {
            "amazon.nova-micro-v1:0",
            "us.amazon.nova-micro-v1:0",
        }
        if value not in allowed:
            raise ValueError("model_id must select an approved Nova Micro model")
        return value


ModelFactory = Callable[[BedrockIntakeSettings], Any]
AgentExtractor = Callable[..., InspectionNotice]


def create_bedrock_model(settings: BedrockIntakeSettings) -> BedrockModel:
    """Create the low-cost intake model with bounded network behavior."""
    client_config = BotocoreConfig(
        connect_timeout=5,
        read_timeout=45,
        retries={"total_max_attempts": 2, "mode": "standard"},
    )
    session = (
        boto3.Session(profile_name=settings.profile)
        if settings.profile is not None
        else None
    )
    return BedrockModel(
        boto_session=session,
        model_id=settings.model_id,
        region_name=settings.region,
        boto_client_config=client_config,
        max_tokens=settings.max_output_tokens,
        temperature=0.0,
    )


def extract_notice_with_bedrock(
    text: str,
    *,
    settings: BedrockIntakeSettings | None = None,
    model_factory: ModelFactory = create_bedrock_model,
    agent_extractor: AgentExtractor = extract_notice_with_agent,
) -> InspectionNotice:
    """Extract one notice through Bedrock and validate it before returning state."""
    selected = settings or BedrockIntakeSettings()
    if not text.strip():
        raise BedrockIntakeError("notice must contain visible characters")
    if len(text) > selected.max_input_characters:
        raise BedrockIntakeError(
            f"notice exceeds the {selected.max_input_characters:,}-character Bedrock limit"
        )

    try:
        model = model_factory(selected)
        return agent_extractor(text, model=model)
    except ClientError as exc:
        error = exc.response.get("Error", {})
        code = str(error.get("Code", "ClientError"))
        request_id = str(exc.response.get("ResponseMetadata", {}).get("RequestId", "unknown"))
        raise BedrockIntakeError(
            f"Bedrock request failed ({code}; request {request_id})"
        ) from exc
    except BotoCoreError as exc:
        raise BedrockIntakeError(
            "Bedrock could not be reached with the current AWS configuration"
        ) from exc
    except BedrockIntakeError:
        raise
    except Exception as exc:
        raise BedrockIntakeError(
            "Bedrock returned output that did not satisfy Mettle's notice contract"
        ) from exc
