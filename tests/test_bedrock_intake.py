from datetime import date

import pytest
from botocore.exceptions import ClientError

from mettle.agents.bedrock import (
    BedrockIntakeError,
    BedrockIntakeSettings,
    create_bedrock_model,
    extract_notice_with_bedrock,
)
from mettle.domain import Citation, InspectionNotice, Trade


NOTICE = InspectionNotice(
    notice_id="TEST-1",
    issued_on=date(2026, 8, 1),
    reinspection_due_on=date(2026, 8, 10),
    property_label="Synthetic property",
    citations=[
        Citation(
            citation_id="1",
            code_reference="NEC 110.26",
            notice_text="Maintain the required working clearance.",
            trade=Trade.ELECTRICAL,
            evidence_requirements=["Wide photo showing the panel area"],
        )
    ],
)


def test_bedrock_model_has_explicit_cost_and_network_bounds() -> None:
    model = create_bedrock_model(BedrockIntakeSettings())
    config = model.get_config()

    assert config["model_id"] == "amazon.nova-micro-v1:0"
    assert config["max_tokens"] == 2_048
    assert config["temperature"] == 0.0
    assert model.client.meta.region_name == "us-east-1"
    assert model.client.meta.config.connect_timeout == 5
    assert model.client.meta.config.read_timeout == 45
    assert model.client.meta.config.retries["total_max_attempts"] == 2


def test_bedrock_settings_reject_more_expensive_models() -> None:
    with pytest.raises(ValueError, match="approved Nova Micro"):
        BedrockIntakeSettings(model_id="amazon.nova-pro-v1:0")


def test_bedrock_intake_injects_bounded_model_and_returns_validated_notice() -> None:
    settings = BedrockIntakeSettings(region="us-west-2")
    observed: dict[str, object] = {}

    def model_factory(received: BedrockIntakeSettings) -> object:
        observed["settings"] = received
        return object()

    def extractor(text: str, *, model: object) -> InspectionNotice:
        observed["text"] = text
        observed["model"] = model
        return NOTICE

    result = extract_notice_with_bedrock(
        "synthetic notice",
        settings=settings,
        model_factory=model_factory,
        agent_extractor=extractor,
    )

    assert result == NOTICE
    assert observed["settings"] == settings
    assert observed["text"] == "synthetic notice"


def test_bedrock_intake_rejects_oversized_notice_before_creating_model() -> None:
    created = False

    def model_factory(_settings: BedrockIntakeSettings) -> object:
        nonlocal created
        created = True
        return object()

    with pytest.raises(BedrockIntakeError, match="exceeds the 1,000-character"):
        extract_notice_with_bedrock(
            "x" * 1_001,
            settings=BedrockIntakeSettings(max_input_characters=1_000),
            model_factory=model_factory,
        )

    assert created is False


def test_bedrock_client_error_is_sanitized_but_keeps_support_identifiers() -> None:
    def extractor(_text: str, *, model: object) -> InspectionNotice:
        raise ClientError(
            {
                "Error": {
                    "Code": "AccessDeniedException",
                    "Message": "sensitive upstream details",
                },
                "ResponseMetadata": {"RequestId": "request-123"},
            },
            "Converse",
        )

    with pytest.raises(BedrockIntakeError) as captured:
        extract_notice_with_bedrock(
            "synthetic notice",
            model_factory=lambda _settings: object(),
            agent_extractor=extractor,
        )

    assert str(captured.value) == (
        "Bedrock request failed (AccessDeniedException; request request-123)"
    )
    assert "sensitive" not in str(captured.value)


def test_notice_contract_rejects_duplicate_citation_ids_and_reversed_dates() -> None:
    duplicate = NOTICE.citations[0].model_copy()
    with pytest.raises(ValueError, match="identifiers must be unique"):
        NOTICE.model_copy(update={"citations": [NOTICE.citations[0], duplicate]}).model_validate(
            NOTICE.model_copy(update={"citations": [NOTICE.citations[0], duplicate]}).model_dump()
        )

    with pytest.raises(ValueError, match="cannot precede"):
        InspectionNotice.model_validate(
            {
                **NOTICE.model_dump(),
                "reinspection_due_on": date(2026, 7, 31),
            }
        )
