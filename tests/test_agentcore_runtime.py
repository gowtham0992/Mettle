import base64
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from PIL import Image

from mettle.agentcore_runtime import MettleAgentCoreRuntime
from mettle.notice_parser import parse_notice
from mettle.evidence import EvidenceAssessment, EvidenceStatus
from mettle.workflow_registry import WorkflowRegistry


NOTICE = Path("examples/notices/failed-rough-in.txt").read_text(encoding="utf-8")


def workflow_payload(*, provider: str = "bedrock") -> dict:
    return {
        "notice_text": NOTICE,
        "intake_provider": provider,
        "as_of": "2026-08-10",
        "roster": [
            {"trade": "electrical", "name": "Mike Alvarez", "phone": "+13035550101"},
            {"trade": "framing", "name": "Jen Ortiz", "phone": "+13035550102"},
            {"trade": "mechanical", "name": "Luis Vega", "phone": "+13035550103"},
        ],
    }


def runtime() -> MettleAgentCoreRuntime:
    def accept_photo(*, citation, image, assessment_id):
        return EvidenceAssessment(
            assessment_id=assessment_id,
            citation_id=citation.citation_id,
            sample_id=f"upload_{assessment_id}",
            image_url="",
            status=EvidenceStatus.ACCEPTED,
            matched_requirements=citation.evidence_requirements,
            explanation="Visible evidence accepted, not code compliance.",
        )
    return MettleAgentCoreRuntime(
        workflows=WorkflowRegistry(
            bedrock_intake=parse_notice,
            photo_assessor=accept_photo,
        )
    )


def jpeg_photo() -> bytes:
    output = BytesIO()
    Image.new("RGB", (80, 60), "gray").save(output, format="JPEG")
    return output.getvalue()


def review_payload(workflow: dict) -> dict:
    return {
        "interrupt_id": workflow["snapshot"]["interrupts"][0]["interrupt_id"],
        "citations": [
            {
                "citation_id": citation["citation_id"],
                "trade": citation["trade"] if citation["trade"] != "unknown" else "general",
                "closure_route": citation.get("closure_route", "photo_evidence"),
                "evidence_requirements": citation["evidence_requirements"]
                or ["Wide photo showing the completed correction and its location"],
            }
            for citation in workflow["snapshot"]["notice"]["citations"]
        ],
    }


def approve_review(subject, workflow, session_id, key):
    return subject.handle(
        {
            "operation": "review",
            "idempotency_key": key,
            "workflow_id": workflow["workflow_id"],
            "payload": review_payload(workflow),
        },
        session_id=session_id,
    )


def test_agentcore_session_starts_then_resumes_the_same_strands_graph() -> None:
    subject = runtime()
    started = subject.handle(
        {
            "operation": "start",
            "idempotency_key": "agentcore_start_123",
            "payload": workflow_payload(),
        },
        session_id="session-123456789012345678901234567890123",
    )

    assert started["ok"] is True
    workflow = started["workflow"]
    assert workflow["intake_provider"] == "bedrock"
    assert workflow["snapshot"]["status"] == "interrupted"
    assert len(workflow["snapshot"]["deliveries"]) == 0

    resumed = approve_review(
        subject,
        workflow,
        "session-123456789012345678901234567890123",
        "agentcore_review_123",
    )

    assert resumed["ok"] is True
    assert resumed["workflow"]["snapshot"]["status"] == "completed"
    assert len(resumed["workflow"]["snapshot"]["deliveries"]) == 3


def test_agentcore_start_replay_does_not_repeat_paid_intake() -> None:
    calls: list[str] = []

    def intake(text: str):
        calls.append(text)
        return parse_notice(text)

    subject = MettleAgentCoreRuntime(
        workflows=WorkflowRegistry(bedrock_intake=intake)
    )
    request = {
        "operation": "start",
        "idempotency_key": "agentcore_replay_123",
        "payload": workflow_payload(),
    }

    first = subject.handle(request, session_id="session-123456789012345678901234567890123")
    replay = subject.handle(request, session_id="session-123456789012345678901234567890123")

    assert first["replayed"] is False
    assert replay["replayed"] is True
    assert replay["workflow"] == first["workflow"]
    assert calls == [NOTICE]


def test_agentcore_accepts_bounded_base64_photo_for_vision_assessment() -> None:
    subject = runtime()
    session_id = "session-photo-123456789012345678901234567890"
    started = subject.handle(
        {
            "operation": "start",
            "idempotency_key": "agentcore_photo_start_123",
            "payload": workflow_payload(),
        },
        session_id=session_id,
    )
    approve_review(subject, started["workflow"], session_id, "agentcore_photo_review_123")
    response = subject.handle(
        {
            "operation": "submit_photo_evidence",
            "idempotency_key": "agentcore_photo_submit_123",
            "workflow_id": started["workflow"]["workflow_id"],
            "payload": {
                "citation_id": "1",
                "image_base64": base64.b64encode(jpeg_photo()).decode("ascii"),
            },
        },
        session_id=session_id,
    )

    assert response["ok"] is True
    assert response["workflow"]["evidence"][-1]["status"] == "accepted"


def test_agentcore_runs_deadline_check_inside_the_same_session() -> None:
    subject = runtime()
    session_id = "session-check-123456789012345678901234567890"
    started = subject.handle(
        {
            "operation": "start",
            "idempotency_key": "agentcore_check_start_123",
            "payload": workflow_payload(),
        },
        session_id=session_id,
    )
    workflow = started["workflow"]
    approve_review(subject, workflow, session_id, "agentcore_check_review_123")

    checked = subject.handle(
        {
            "operation": "run_next_check",
            "idempotency_key": "agentcore_check_tick_123",
            "workflow_id": workflow["workflow_id"],
            "payload": {},
        },
        session_id=session_id,
    )

    assert checked["ok"] is True
    assert checked["workflow"]["snapshot"]["plan"]["as_of"] == "2026-08-14"
    assert len(checked["workflow"]["snapshot"]["deliveries"]) == 6


def test_agentcore_boundary_rejects_unknown_fields_without_echoing_input() -> None:
    response = runtime().handle(
        {
            "operation": "start",
            "idempotency_key": "agentcore_invalid_123",
            "payload": workflow_payload(),
            "aws_profile": "admin",
        },
        session_id="session-123456789012345678901234567890123",
    )

    assert response == {
        "ok": False,
        "error": {
            "code": "invalid_request",
            "message": "AgentCore request validation failed.",
        },
    }


def test_agentcore_boundary_returns_quiet_error_for_unknown_workflow() -> None:
    response = runtime().handle(
        {
            "operation": "resume",
            "idempotency_key": "agentcore_missing_123",
            "workflow_id": "not-a-workflow",
            "payload": {
                "interrupt_id": "not-an-interrupt",
                "decision": "Use a wide clearance photo",
            },
        },
        session_id="session-123456789012345678901234567890123",
    )

    assert response == {
        "ok": False,
        "error": {"code": "workflow_not_found", "message": "workflow does not exist"},
    }


def test_agentcore_session_completes_evidence_approval_and_pdf_packet() -> None:
    subject = runtime()
    session_id = "session-complete-123456789012345678901234567890"
    started = subject.handle(
        {
            "operation": "start",
            "idempotency_key": "agentcore_full_start_123",
            "payload": workflow_payload(),
        },
        session_id=session_id,
    )
    workflow = started["workflow"]
    workflow_id = workflow["workflow_id"]
    resumed = approve_review(subject, workflow, session_id, "agentcore_full_review_123")
    assert resumed["ok"] is True

    latest = None
    for index, (citation_id, sample_id) in enumerate(
        [
            ("1", "panel_wide_measured"),
            ("2", "framing_plates_complete"),
            ("3", "mechanical_access_wide"),
        ]
    ):
        latest = subject.handle(
            {
                "operation": "submit_evidence",
                "idempotency_key": f"agentcore_full_evidence_{index}",
                "workflow_id": workflow_id,
                "payload": {"citation_id": citation_id, "sample_id": sample_id},
            },
            session_id=session_id,
        )
        assert latest["ok"] is True
        assert latest["workflow"]["evidence"][-1]["status"] == "accepted"

    prepared = subject.handle(
        {
            "operation": "prepare_packet",
            "idempotency_key": "agentcore_full_prepare_123",
            "workflow_id": workflow_id,
            "payload": {},
        },
        session_id=session_id,
    )
    packet = prepared["workflow"]["packet"]
    assert packet["status"] == "awaiting_approval"
    approved = subject.handle(
        {
            "operation": "approve_packet",
            "idempotency_key": "agentcore_full_approve_123",
            "workflow_id": workflow_id,
            "payload": {
                "approval_id": packet["approval_id"],
                "decision": "Approve packet for reinspection scheduling",
            },
        },
        session_id=session_id,
    )
    assert approved["workflow"]["packet"]["status"] == "approved"

    rendered = subject.handle(
        {"operation": "render_packet", "workflow_id": workflow_id},
        session_id=session_id,
    )
    pdf = base64.b64decode(rendered["body_base64"], validate=True)
    assert rendered["ok"] is True
    assert rendered["content_type"] == "application/pdf"
    assert rendered["filename"] == "mettle-reinspection-packet.pdf"
    assert len(PdfReader(BytesIO(pdf)).pages) == 4


def test_agentcore_evidence_rejects_unknown_sample_without_echoing_it() -> None:
    subject = runtime()
    session_id = "session-evidence-1234567890123456789012345678"
    started = subject.handle(
        {
            "operation": "start",
            "idempotency_key": "agentcore_evidence_start_123",
            "payload": workflow_payload(),
        },
        session_id=session_id,
    )
    approve_review(
        subject,
        started["workflow"],
        session_id,
        "agentcore_evidence_review_123",
    )
    response = subject.handle(
        {
            "operation": "submit_evidence",
            "idempotency_key": "agentcore_bad_evidence_123",
            "workflow_id": started["workflow"]["workflow_id"],
            "payload": {"citation_id": "1", "sample_id": "secret_sample"},
        },
        session_id=session_id,
    )

    assert response == {
        "ok": False,
        "error": {
            "code": "invalid_evidence_submission",
            "message": "evidence sample is not available",
        },
    }
