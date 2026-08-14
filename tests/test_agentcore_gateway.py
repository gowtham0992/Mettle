from __future__ import annotations

import io
import json
from base64 import b64encode
from collections import deque
from hashlib import sha256
from pathlib import Path

import pytest

from mettle.agentcore_gateway import AgentCoreGatewayError, AgentCoreWorkflowGateway
from mettle.workflow_registry import (
    ApprovePacketRequest,
    CreateWorkflowRequest,
    PreparePacketRequest,
    ReviewWorkflowRequest,
    RunNextCheckRequest,
    SubmitEvidenceRequest,
    SubmitPhotoEvidenceRequest,
    WorkflowConflict,
    WorkflowRegistry,
)


NOTICE = Path("examples/notices/failed-rough-in.txt").read_text(encoding="utf-8")
RUNTIME_ARN = (
    "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/MettleRecovery-example"
)


def create_payload() -> CreateWorkflowRequest:
    return CreateWorkflowRequest.model_validate(
        {
            "notice_text": NOTICE,
            "intake_provider": "local",
            "as_of": "2026-08-10",
            "roster": [
                {
                    "trade": "electrical",
                    "name": "Mike Alvarez",
                    "phone": "+13035550101",
                },
                {
                    "trade": "framing",
                    "name": "Jen Ortiz",
                    "phone": "+13035550102",
                },
                {
                    "trade": "mechanical",
                    "name": "Luis Vega",
                    "phone": "+13035550103",
                },
            ],
        }
    )


def interrupted_envelope():
    return WorkflowRegistry().create(
        create_payload(), idempotency_key="source_create_123"
    )[0]


def review_request(envelope) -> ReviewWorkflowRequest:
    return ReviewWorkflowRequest.model_validate(
        {
            "interrupt_id": envelope.snapshot.interrupts[0].interrupt_id,
            "citations": [
                {
                    "citation_id": citation.citation_id,
                    "trade": citation.trade.value if citation.trade.value != "unknown" else "general",
                    "closure_route": citation.closure_route.value,
                    "evidence_requirements": citation.evidence_requirements
                    or ["Wide photo showing the completed correction and its location"],
                }
                for citation in envelope.snapshot.notice.citations
            ],
        }
    )


class QueueClient:
    def __init__(self, results: list[dict | Exception]) -> None:
        self.results = deque(results)
        self.requests: list[dict] = []

    def invoke_agent_runtime(self, **kwargs):
        self.requests.append(kwargs)
        result = self.results.popleft()
        if isinstance(result, Exception):
            raise result
        return {
            "statusCode": 200,
            "response": io.BytesIO(json.dumps(result).encode("utf-8")),
        }


def success(envelope, *, replayed: bool = False) -> dict:
    return {
        "ok": True,
        "replayed": replayed,
        "workflow": envelope.model_dump(mode="json"),
    }


def test_create_keeps_agentcore_session_private_and_replays_without_second_spend() -> None:
    envelope = interrupted_envelope()
    client = QueueClient([success(envelope)])
    gateway = AgentCoreWorkflowGateway(client=client, runtime_arn=RUNTIME_ARN)

    first, replayed = gateway.create(create_payload(), idempotency_key="cloud_create_123")
    replay, was_replayed = gateway.create(
        create_payload(), idempotency_key="cloud_create_123"
    )

    assert replayed is False
    assert was_replayed is True
    assert replay == first
    assert len(client.requests) == 1
    request = client.requests[0]
    assert request["runtimeSessionId"].startswith("mettle-")
    assert len(request["runtimeSessionId"]) >= 33
    invocation = json.loads(request["payload"])
    assert invocation["operation"] == "start"
    assert invocation["idempotency_key"] == "cloud_create_123"
    assert "runtimeSessionId" not in json.dumps(first.model_dump(mode="json"))


def test_create_retry_after_transport_failure_reuses_the_same_agentcore_session() -> None:
    envelope = interrupted_envelope()
    client = QueueClient([RuntimeError("network down"), success(envelope, replayed=True)])
    gateway = AgentCoreWorkflowGateway(client=client, runtime_arn=RUNTIME_ARN)

    with pytest.raises(AgentCoreGatewayError, match="could not be reached"):
        gateway.create(create_payload(), idempotency_key="cloud_retry_123")
    result, replayed = gateway.create(
        create_payload(), idempotency_key="cloud_retry_123"
    )

    assert result.workflow_id == envelope.workflow_id
    assert replayed is True
    assert len(client.requests) == 2
    assert client.requests[0]["runtimeSessionId"] == client.requests[1]["runtimeSessionId"]


def test_changed_create_replay_is_rejected_before_agentcore_invocation() -> None:
    envelope = interrupted_envelope()
    client = QueueClient([success(envelope)])
    gateway = AgentCoreWorkflowGateway(client=client, runtime_arn=RUNTIME_ARN)
    gateway.create(create_payload(), idempotency_key="cloud_conflict_123")
    changed = create_payload().model_copy(
        update={"notice_text": NOTICE.replace("100 Demo Way", "200 Demo Way")}
    )

    with pytest.raises(WorkflowConflict, match="different workflow request"):
        gateway.create(changed, idempotency_key="cloud_conflict_123")

    assert len(client.requests) == 1


def test_review_reuses_session_and_is_locally_idempotent() -> None:
    source = WorkflowRegistry()
    created, _ = source.create(create_payload(), idempotency_key="resume_source_123")
    payload = review_request(created)
    completed = source.review(
        created.workflow_id,
        payload,
        idempotency_key="review_source_decision_123",
    )
    client = QueueClient([success(created), success(completed)])
    gateway = AgentCoreWorkflowGateway(client=client, runtime_arn=RUNTIME_ARN)
    gateway.create(create_payload(), idempotency_key="cloud_resume_create_123")

    first = gateway.review(
        created.workflow_id,
        payload,
        idempotency_key="cloud_review_123",
    )
    replay = gateway.review(
        created.workflow_id,
        payload,
        idempotency_key="cloud_review_123",
    )

    assert first == replay
    assert first.snapshot.status == "completed"
    assert len(client.requests) == 2
    assert client.requests[0]["runtimeSessionId"] == client.requests[1]["runtimeSessionId"]


def test_photo_evidence_is_base64_encoded_inside_the_private_agentcore_request() -> None:
    created = interrupted_envelope()
    accepted = created.model_copy(deep=True)
    client = QueueClient([success(created), success(accepted)])
    gateway = AgentCoreWorkflowGateway(client=client, runtime_arn=RUNTIME_ARN)
    gateway.create(create_payload(), idempotency_key="cloud_photo_create_123")

    gateway.submit_photo_evidence(
        created.workflow_id,
        SubmitPhotoEvidenceRequest(citation_id="1"),
        image=b"normalized-jpeg",
        idempotency_key="cloud_photo_submit_123",
    )

    request_body = json.loads(client.requests[1]["payload"])
    assert request_body["operation"] == "submit_photo_evidence"
    assert request_body["payload"]["image_base64"] == b64encode(b"normalized-jpeg").decode("ascii")


def test_recovery_check_uses_the_existing_private_agentcore_session() -> None:
    created = interrupted_envelope()
    checked = created.model_copy(deep=True)
    client = QueueClient([success(created), success(checked)])
    gateway = AgentCoreWorkflowGateway(client=client, runtime_arn=RUNTIME_ARN)
    gateway.create(create_payload(), idempotency_key="cloud_check_create_123")

    gateway.run_next_check(
        created.workflow_id,
        RunNextCheckRequest(),
        idempotency_key="cloud_check_tick_123",
    )

    request_body = json.loads(client.requests[1]["payload"])
    assert request_body["operation"] == "run_next_check"
    assert client.requests[1]["runtimeSessionId"] == client.requests[0]["runtimeSessionId"]


def test_runtime_error_is_mapped_without_exposing_untrusted_details() -> None:
    client = QueueClient(
        [{"ok": False, "error": {"code": "internal_error", "message": "secret"}}]
    )
    gateway = AgentCoreWorkflowGateway(client=client, runtime_arn=RUNTIME_ARN)

    with pytest.raises(AgentCoreGatewayError) as raised:
        gateway.create(create_payload(), idempotency_key="cloud_error_123")

    assert "secret" not in str(raised.value)


def test_full_cloud_mutation_path_reuses_session_and_caches_verified_pdf() -> None:
    source = WorkflowRegistry()
    created, _ = source.create(create_payload(), idempotency_key="full_source_create")
    review_payload = review_request(created)
    resumed = source.review(
        created.workflow_id,
        review_payload,
        idempotency_key="full_source_review",
    )
    envelopes = [created, resumed]
    evidence_payloads = [
        SubmitEvidenceRequest(citation_id="1", sample_id="panel_wide_measured"),
        SubmitEvidenceRequest(citation_id="2", sample_id="framing_plates_complete"),
        SubmitEvidenceRequest(citation_id="3", sample_id="mechanical_access_wide"),
    ]
    for index, payload in enumerate(evidence_payloads):
        envelopes.append(
            source.submit_evidence(
                created.workflow_id,
                payload,
                idempotency_key=f"full_source_evidence_{index}",
            )
        )
    prepared = source.prepare_packet(
        created.workflow_id,
        idempotency_key="full_source_prepare",
    )
    envelopes.append(prepared)
    approval_payload = ApprovePacketRequest(
        approval_id=prepared.packet.approval_id,
        decision="Approve packet for reinspection scheduling",
    )
    approved = source.approve_packet(
        created.workflow_id,
        approval_payload,
        idempotency_key="full_source_approve",
    )
    envelopes.append(approved)
    pdf = b"%PDF-1.7\nsynthetic verified packet\n%%EOF"
    render_result = {
        "ok": True,
        "content_type": "application/pdf",
        "filename": "mettle-reinspection-packet.pdf",
        "sha256": sha256(pdf).hexdigest(),
        "body_base64": b64encode(pdf).decode("ascii"),
    }
    client = QueueClient([*(success(item) for item in envelopes), render_result])
    gateway = AgentCoreWorkflowGateway(client=client, runtime_arn=RUNTIME_ARN)

    cloud, _ = gateway.create(
        create_payload(), idempotency_key="full_cloud_create_123"
    )
    gateway.review(
        cloud.workflow_id,
        review_payload,
        idempotency_key="full_cloud_review_123",
    )
    for index, payload in enumerate(evidence_payloads):
        gateway.submit_evidence(
            cloud.workflow_id,
            payload,
            idempotency_key=f"full_cloud_evidence_{index}",
        )
    gateway.prepare_packet(
        cloud.workflow_id,
        PreparePacketRequest(),
        idempotency_key="full_cloud_prepare_123",
    )
    gateway.approve_packet(
        cloud.workflow_id,
        approval_payload,
        idempotency_key="full_cloud_approve_123",
    )
    first_pdf = gateway.render_packet(cloud.workflow_id)
    cached_pdf = gateway.render_packet(cloud.workflow_id)

    assert first_pdf == cached_pdf == pdf
    assert len(client.requests) == 8
    assert len({item["runtimeSessionId"] for item in client.requests}) == 1
    operations = [json.loads(item["payload"])["operation"] for item in client.requests]
    assert operations == [
        "start",
        "review",
        "submit_evidence",
        "submit_evidence",
        "submit_evidence",
        "prepare_packet",
        "approve_packet",
        "render_packet",
    ]


def test_packet_integrity_mismatch_is_rejected_and_not_cached() -> None:
    created = interrupted_envelope()
    pdf = b"%PDF-1.7\nnot trusted\n%%EOF"
    client = QueueClient(
        [
            success(created),
            {
                "ok": True,
                "content_type": "application/pdf",
                "filename": "mettle-reinspection-packet.pdf",
                "sha256": "0" * 64,
                "body_base64": b64encode(pdf).decode("ascii"),
            },
        ]
    )
    gateway = AgentCoreWorkflowGateway(client=client, runtime_arn=RUNTIME_ARN)
    cloud, _ = gateway.create(
        create_payload(), idempotency_key="packet_integrity_create_123"
    )

    with pytest.raises(AgentCoreGatewayError, match="integrity check failed"):
        gateway.render_packet(cloud.workflow_id)
