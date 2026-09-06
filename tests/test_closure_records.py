from io import BytesIO
from pathlib import Path

import pytest

from mettle.domain import ClosureRoute
from mettle.workflow_registry import (
    WorkflowRegistry, SubmitEvidenceRequest, SubmitPhotoEvidenceRequest,
    EvidenceSubmissionError, ReviewWorkflowRequest, ApprovePacketRequest,
)
from mettle.workflow import ReviewedCitation
from test_durable_agentcore_gateway import payload


def reviewed_registry():
    registry = WorkflowRegistry(photo_assessor=lambda **kwargs: pytest.fail("Vision must not assess non-photo routes"))
    first, _ = registry.create(payload(), idempotency_key="create_records")
    registry.review(first.workflow_id, ReviewWorkflowRequest(
        interrupt_id=first.snapshot.interrupts[0].interrupt_id,
        citations=tuple(ReviewedCitation(
            citation_id=c.citation_id, trade=c.trade,
            closure_route=ClosureRoute.DOCUMENT_EVIDENCE if c.citation_id != "3" else ClosureRoute.PHYSICAL_REINSPECTION,
            evidence_requirements=("Required source record",),
        ) for c in first.snapshot.notice.citations),
    ), idempotency_key="review_records")
    return registry, first.workflow_id


def record_request(citation="1", route="document_evidence"):
    return SubmitEvidenceRequest.model_validate({
        "citation_id": citation,
        "contractor_record": {
            "route": route, "reference": "TEST record 123 revision A",
            "reviewer": "Test Contractor", "reviewed_on": "2026-08-10",
            "details": "Reviewed the retained source record against every required item.",
            "confirmed": True,
        },
    })


def test_record_closure_is_explicit_persisted_and_retry_safe():
    registry, workflow_id = reviewed_registry()
    request = record_request()
    result = registry.submit_evidence(workflow_id, request, idempotency_key="record_once")
    assert result.evidence[-1].status == "accepted"
    assert result.evidence[-1].contractor_record.reference == "TEST record 123 revision A"
    assert "Contractor" in result.evidence[-1].explanation
    assert registry.submit_evidence(workflow_id, request, idempotency_key="record_once") == result
    cold = WorkflowRegistry()
    cold.restore_checkpoint(workflow_id, registry.checkpoint(workflow_id))
    assert cold.get(workflow_id).evidence == result.evidence
    with pytest.raises(EvidenceSubmissionError, match="locked"):
        cold.submit_evidence(workflow_id, request, idempotency_key="different_key")


def test_non_photo_routes_reject_photo_and_wrong_record_route():
    registry, workflow_id = reviewed_registry()
    with pytest.raises(EvidenceSubmissionError, match="photo"):
        registry.submit_photo_evidence(workflow_id, SubmitPhotoEvidenceRequest(citation_id="1"), image=b"not needed", idempotency_key="no_photo")
    with pytest.raises(EvidenceSubmissionError, match="route"):
        registry.submit_evidence(workflow_id, record_request("3"), idempotency_key="wrong_route")


def test_mixed_records_can_reach_packet_without_fake_photos():
    registry, workflow_id = reviewed_registry()
    for citation, route in [("1", "document_evidence"), ("2", "document_evidence"), ("3", "physical_reinspection")]:
        registry.submit_evidence(workflow_id, record_request(citation, route), idempotency_key=f"record_{citation}")
    result = registry.prepare_packet(workflow_id, idempotency_key="prepare_records")
    assert result.packet.citations_ready == 3
    registry.approve_packet(workflow_id, ApprovePacketRequest(approval_id=result.packet.approval_id, decision="Reviewed the source records and approve this test packet"), idempotency_key="approve_records")
    from pypdf import PdfReader
    pdf = registry.render_packet(workflow_id, evidence_dir=Path("src/mettle/web/static/evidence"))
    text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(pdf)).pages)
    assert "CONTRACTOR-REVIEWED SOURCE RECORD" in text
    assert "TEST record 123 revision A" in text
    assert "not attached or independently authenticated" in text


@pytest.mark.parametrize("update", [
    {"confirmed": False}, {"confirmed": "true"}, {"details": " " * 30},
    {"reference": " " * 10}, {"details": "x" * 4001},
])
def test_invalid_source_record_rejected_at_boundary(update):
    from pydantic import ValidationError
    data = record_request().model_dump()
    data["contractor_record"].update(update)
    with pytest.raises(ValidationError):
        SubmitEvidenceRequest.model_validate(data)


def test_future_review_date_cannot_close_a_correction():
    registry, workflow_id = reviewed_registry()
    data = record_request().model_dump(mode="json")
    data["contractor_record"]["reviewed_on"] = "9999-01-01"
    with pytest.raises(EvidenceSubmissionError, match="future"):
        registry.submit_evidence(workflow_id, SubmitEvidenceRequest.model_validate(data), idempotency_key="future_record")
    assert not registry.get(workflow_id).evidence


def test_record_roundtrips_through_authenticated_gateway_and_cold_runtime():
    from test_cold_gateway import PrivateBucket, RuntimeClient
    from test_durable_agentcore_gateway import MemoryTable, RUNTIME_ARN, review_request
    from mettle.durable_agentcore_gateway import DurableAgentCoreWorkflowGateway
    from mettle.request_identity import set_principal, reset_principal
    from mettle.workflow_registry import WorkflowNotFound
    client = RuntimeClient()
    gateway = DurableAgentCoreWorkflowGateway(client=client, runtime_arn=RUNTIME_ARN, table=MemoryTable(), packet_bucket=PrivateBucket(), clock=lambda: 1_000_000)
    token = set_principal("record-owner")
    try:
        first, _ = gateway.create(payload(), idempotency_key="record_create_gateway")
        review = review_request(first)
        review = review.model_copy(update={"citations": tuple(c.model_copy(update={"closure_route": ClosureRoute.DOCUMENT_EVIDENCE}) for c in review.citations)})
        gateway.review(first.workflow_id, review, idempotency_key="record_review_gateway")
        client.sessions.clear()
        result = gateway.submit_evidence(first.workflow_id, record_request(), idempotency_key="record_submit_gateway")
        assert result.evidence[-1].contractor_record.reference == "TEST record 123 revision A"
        client.sessions.clear()
        assert gateway.submit_evidence(first.workflow_id, record_request(), idempotency_key="record_submit_gateway") == result
        other = set_principal("not-record-owner")
        try:
            with pytest.raises(WorkflowNotFound):
                gateway.submit_evidence(first.workflow_id, record_request("2"), idempotency_key="record_other_gateway")
        finally:
            reset_principal(other)
    finally:
        reset_principal(token)
