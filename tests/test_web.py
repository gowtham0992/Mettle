import base64
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader

from mettle.agents.bedrock import BedrockIntakeError
from mettle.demo import DemoStore
from mettle.domain import Citation
from mettle.evidence import EvidenceAssessment, EvidenceStatus
from mettle.notice_parser import parse_notice
from mettle.web.app import create_app
from mettle.workflow_registry import WorkflowRegistry


NOTICE = Path("examples/notices/failed-rough-in.txt").read_text(encoding="utf-8")
DENVER_NOTICE = Path("examples/notices/denver-remodel.txt").read_text(encoding="utf-8")
WEB_TEMPLATE = Path("infra/web/template.yaml").read_text(encoding="utf-8")


def test_notice_ocr_requires_verified_identity(monkeypatch):
    monkeypatch.setenv("METTLE_NOTICE_OCR_ENABLED", "1")
    with TestClient(create_app()) as browser:
        response = browser.post("/api/agentcore/notices/ocr", json={"filename":"notice.png", "file_base64":"YWJjZA=="})
    assert response.status_code == 401


def test_notice_ocr_disabled_even_for_verified_identity(monkeypatch):
    monkeypatch.delenv("METTLE_NOTICE_OCR_ENABLED", raising=False)
    monkeypatch.setattr("mettle.web.app._verified_subject", lambda request: "test-subject")
    with TestClient(create_app()) as browser:
        response = browser.post("/api/agentcore/notices/ocr", json={"filename":"notice.png", "file_base64":"YWJjZA=="})
    assert response.status_code == 422
    assert "not enabled" in response.json()["error"]["message"]


def test_notice_ocr_returns_reviewable_text(monkeypatch):
    from unittest.mock import Mock
    monkeypatch.setenv("METTLE_NOTICE_OCR_ENABLED", "1")
    monkeypatch.setattr("mettle.web.app._verified_subject", lambda request: "test-subject")
    aws = Mock()
    aws.detect_document_text.return_value = {"Blocks":[{"BlockType":"LINE", "Text":"Permit REVIEW-1. Correct panel clearance."}]}
    monkeypatch.setattr("mettle.web.app.boto3.client", lambda *args, **kwargs: aws)
    image = BytesIO()
    Image.new("RGB", (100,100), "white").save(image, format="PNG")
    with TestClient(create_app()) as browser:
        response = browser.post("/api/agentcore/notices/ocr", json={"filename":"notice.png", "file_base64":base64.b64encode(image.getvalue()).decode()})
    assert response.status_code == 200
    assert response.json()["text"] == "Permit REVIEW-1. Correct panel clearance."
    aws.detect_document_text.assert_called_once()


class FakeAgentCoreGateway:
    def __init__(self) -> None:
        self.registry = WorkflowRegistry(
            bedrock_intake=parse_notice,
            photo_assessor=accept_photo,
        )

    def create(self, payload, *, idempotency_key):
        return self.registry.create(payload, idempotency_key=idempotency_key)

    def get(self, workflow_id):
        return self.registry.get(workflow_id)

    def resume(self, workflow_id, payload, *, idempotency_key):
        return self.registry.resume(
            workflow_id, payload, idempotency_key=idempotency_key
        )

    def review(self, workflow_id, payload, *, idempotency_key):
        return self.registry.review(
            workflow_id, payload, idempotency_key=idempotency_key
        )

    def submit_evidence(self, workflow_id, payload, *, idempotency_key):
        return self.registry.submit_evidence(
            workflow_id, payload, idempotency_key=idempotency_key
        )

    def submit_photo_evidence(self, workflow_id, payload, *, image, idempotency_key):
        return self.registry.submit_photo_evidence(
            workflow_id,
            payload,
            image=image,
            idempotency_key=idempotency_key,
        )

    def review_evidence(self, workflow_id, payload, *, idempotency_key):
        return self.registry.review_evidence(
            workflow_id,
            payload,
            idempotency_key=idempotency_key,
        )

    def run_next_check(self, workflow_id, payload, *, idempotency_key):
        return self.registry.run_next_check(
            workflow_id,
            idempotency_key=idempotency_key,
        )

    def prepare_packet(self, workflow_id, payload, *, idempotency_key):
        return self.registry.prepare_packet(
            workflow_id, idempotency_key=idempotency_key
        )

    def approve_packet(self, workflow_id, payload, *, idempotency_key):
        return self.registry.approve_packet(
            workflow_id, payload, idempotency_key=idempotency_key
        )

    def render_packet(self, workflow_id):
        return self.registry.render_packet(
            workflow_id,
            evidence_dir=Path("src/mettle/web/static/evidence"),
        )


def workflow_payload(*, notice_text: str = NOTICE, intake_provider: str = "local") -> dict:
    return {
        "notice_text": notice_text,
        "intake_provider": intake_provider,
        "as_of": "2026-08-10",
        "roster": [
            {"trade": "electrical", "name": "Mike Alvarez", "phone": "+13035550101"},
            {"trade": "framing", "name": "Jen Ortiz", "phone": "+13035550102"},
            {"trade": "mechanical", "name": "Luis Vega", "phone": "+13035550103"},
        ],
    }


def accept_photo(*, citation: Citation, image: bytes, assessment_id: str):
    assert image.startswith(b"\xff\xd8\xff")
    return EvidenceAssessment(
        assessment_id=assessment_id,
        citation_id=citation.citation_id,
        sample_id=f"upload_{assessment_id}",
        image_url="",
        status=EvidenceStatus.ACCEPTED,
        matched_requirements=citation.evidence_requirements,
        explanation="Every requested item is visibly shown; this is not a code-compliance decision.",
    )


def hold_photo_for_review(*, citation: Citation, image: bytes, assessment_id: str):
    assert image.startswith(b"\xff\xd8\xff")
    return EvidenceAssessment(
        assessment_id=assessment_id,
        citation_id=citation.citation_id,
        sample_id=f"upload_{assessment_id}",
        image_url="",
        status=EvidenceStatus.MANUAL_REVIEW,
        missing_requirements=citation.evidence_requirements,
        explanation="The image is ambiguous. Contractor review is required.",
    )


def review_payload(created: dict) -> dict:
    interrupt = created["snapshot"]["interrupts"][0]
    return {
        "interrupt_id": interrupt["interrupt_id"],
        "citations": [
            {
                "citation_id": citation["citation_id"],
                "trade": citation["trade"] if citation["trade"] != "unknown" else "general",
                "closure_route": citation.get("closure_route", "photo_evidence"),
                "evidence_requirements": citation["evidence_requirements"]
                or ["Wide photo showing the completed correction and its location"],
            }
            for citation in created["snapshot"]["notice"]["citations"]
        ],
    }


def approve_review(
    browser: TestClient,
    created: dict,
    *,
    key: str = "approve_review_123",
    root: str = "/api/workflows",
):
    return browser.post(
        f"{root}/{created['workflow_id']}/review",
        json=review_payload(created),
        headers={"Idempotency-Key": key},
    )


def ready_workflow(browser: TestClient) -> tuple[str, dict]:
    created = browser.post(
        "/api/workflows",
        json=workflow_payload(),
        headers={"Idempotency-Key": "packet_workflow_123"},
    ).json()
    workflow_id = created["workflow_id"]
    reviewed = approve_review(browser, created, key="packet_review_123")
    assert reviewed.status_code == 200
    for index, (citation_id, sample_id) in enumerate(
        [
            ("1", "panel_wide_measured"),
            ("2", "framing_plates_complete"),
            ("3", "mechanical_access_wide"),
        ]
    ):
        response = browser.post(
            f"/api/workflows/{workflow_id}/evidence",
            json={"citation_id": citation_id, "sample_id": sample_id},
            headers={"Idempotency-Key": f"packet_evidence_{index}_123"},
        )
        assert response.status_code == 200
        assert response.json()["evidence"][-1]["status"] == "accepted"
    return workflow_id, created


def client(*, workflows: WorkflowRegistry | None = None, agentcore=None) -> TestClient:
    return TestClient(
        create_app(store=DemoStore(), workflows=workflows, agentcore=agentcore)
    )


def jpeg_photo() -> bytes:
    output = BytesIO()
    Image.new("RGB", (80, 60), (195, 185, 160)).save(output, format="JPEG")
    return output.getvalue()


def test_real_photo_upload_is_normalized_assessed_and_idempotent() -> None:
    workflows = WorkflowRegistry(photo_assessor=accept_photo)
    with client(workflows=workflows) as browser:
        created = browser.post(
            "/api/workflows",
            json=workflow_payload(),
            headers={"Idempotency-Key": "photo_workflow_123"},
        ).json()
        workflow_id = created["workflow_id"]
        approve_review(browser, created, key="photo_review_123")
        headers = {
            "Content-Type": "image/jpeg",
            "Idempotency-Key": "photo_evidence_123",
        }
        first = browser.post(
            f"/api/workflows/{workflow_id}/evidence/photo?citation_id=1",
            content=jpeg_photo(),
            headers=headers,
        )
        replay = browser.post(
            f"/api/workflows/{workflow_id}/evidence/photo?citation_id=1",
            content=jpeg_photo(),
            headers=headers,
        )
        assessment_id = first.json()["evidence"][-1]["assessment_id"]
        photo = browser.get(f"/api/workflows/{workflow_id}/evidence/{assessment_id}/photo")
        assert photo.status_code == 200
        assert photo.headers["cache-control"] == "no-store"
        assert base64.b64decode(photo.json()["image_base64"]).startswith(b"\xff\xd8\xff")
        assert browser.get(f"/api/workflows/{workflow_id}/evidence/missing/photo").status_code == 404
        assert browser.get(f"/api/agentcore/workflows/{workflow_id}/evidence/{assessment_id}/photo").status_code == 401

    assert first.status_code == 200
    assert first.json()["evidence"][-1]["status"] == "accepted"
    assert replay.json() == first.json()
    assert len(replay.json()["evidence"]) == 1


def test_ambiguous_photo_requires_and_records_contractor_review() -> None:
    workflows = WorkflowRegistry(photo_assessor=hold_photo_for_review)
    with client(workflows=workflows) as browser:
        created = browser.post(
            "/api/workflows",
            json=workflow_payload(),
            headers={"Idempotency-Key": "manual_review_workflow_123"},
        ).json()
        workflow_id = created["workflow_id"]
        approve_review(browser, created, key="manual_review_launch_123")
        assessed = browser.post(
            f"/api/workflows/{workflow_id}/evidence/photo?citation_id=1",
            content=jpeg_photo(),
            headers={
                "Content-Type": "image/jpeg",
                "Idempotency-Key": "manual_review_photo_123",
            },
        )
        assessment_id = assessed.json()["evidence"][-1]["assessment_id"]
        blocked_check = browser.post(
            f"/api/workflows/{workflow_id}/checks/next",
            json={},
            headers={"Idempotency-Key": "manual_review_check_123"},
        )
        payload = {
            "assessment_id": assessment_id,
            "disposition": "accept",
            "decision": "I reviewed the image and accept it as sufficient visible proof.",
        }
        resolved = browser.post(
            f"/api/workflows/{workflow_id}/evidence/review",
            json=payload,
            headers={"Idempotency-Key": "manual_review_accept_123"},
        )
        replay = browser.post(
            f"/api/workflows/{workflow_id}/evidence/review",
            json=payload,
            headers={"Idempotency-Key": "manual_review_accept_123"},
        )

    assert assessed.status_code == 200
    assert assessed.json()["evidence"][-1]["status"] == "manual_review"
    assert blocked_check.status_code == 409
    assert "resolve the pending contractor evidence review" in blocked_check.json()["error"]["message"]
    assert resolved.status_code == 200
    evidence = resolved.json()["evidence"][-1]
    assert evidence["status"] == "accepted"
    assert evidence["automated_status"] == "manual_review"
    assert evidence["contractor_decision"] == payload["decision"]
    assert evidence["agent_run"][-1]["step"] == "Contractor resolution"
    assert replay.json() == resolved.json()


def test_contractor_can_return_ambiguous_photo_and_submit_replacement() -> None:
    workflows = WorkflowRegistry(photo_assessor=hold_photo_for_review)
    with client(workflows=workflows) as browser:
        created = browser.post(
            "/api/workflows",
            json=workflow_payload(),
            headers={"Idempotency-Key": "return_photo_workflow_123"},
        ).json()
        workflow_id = created["workflow_id"]
        approve_review(browser, created, key="return_photo_launch_123")
        assessed = browser.post(
            f"/api/workflows/{workflow_id}/evidence/photo?citation_id=1",
            content=jpeg_photo(),
            headers={
                "Content-Type": "image/jpeg",
                "Idempotency-Key": "return_photo_assess_123",
            },
        ).json()
        returned = browser.post(
            f"/api/workflows/{workflow_id}/evidence/review",
            json={
                "assessment_id": assessed["evidence"][-1]["assessment_id"],
                "disposition": "reject",
                "decision": "Send a wider image that shows the full measured clearance.",
            },
            headers={"Idempotency-Key": "return_photo_decision_123"},
        )
        replacement = browser.post(
            f"/api/workflows/{workflow_id}/evidence",
            json={"citation_id": "1", "sample_id": "panel_wide_measured"},
            headers={"Idempotency-Key": "return_photo_replacement_123"},
        )

    assert returned.status_code == 200
    returned_evidence = returned.json()["evidence"][-1]
    assert returned_evidence["status"] == "rejected"
    assert returned_evidence["automated_status"] == "manual_review"
    assert replacement.status_code == 200
    assert replacement.json()["evidence"][-1]["status"] == "accepted"
    assert len(replacement.json()["evidence"]) == 2


def test_accepted_evidence_cannot_be_silently_replaced() -> None:
    with client() as browser:
        created = browser.post(
            "/api/workflows",
            json=workflow_payload(),
            headers={"Idempotency-Key": "locked_evidence_workflow_123"},
        ).json()
        workflow_id = created["workflow_id"]
        approve_review(browser, created, key="locked_evidence_review_123")
        accepted = browser.post(
            f"/api/workflows/{workflow_id}/evidence",
            json={"citation_id": "1", "sample_id": "panel_wide_measured"},
            headers={"Idempotency-Key": "locked_evidence_accept_123"},
        )
        replacement = browser.post(
            f"/api/workflows/{workflow_id}/evidence",
            json={"citation_id": "1", "sample_id": "panel_closeup_insufficient"},
            headers={"Idempotency-Key": "locked_evidence_replace_123"},
        )

    assert accepted.status_code == 200
    assert replacement.status_code == 422
    assert replacement.json()["error"] == {
        "code": "invalid_evidence_submission",
        "message": "accepted evidence is locked; keep the approved proof or start an explicit replacement workflow",
    }


def test_json_photo_upload_crosses_text_only_edge_and_remains_idempotent() -> None:
    workflows = WorkflowRegistry(photo_assessor=accept_photo)
    encoded = base64.b64encode(jpeg_photo()).decode("ascii")
    with client(workflows=workflows) as browser:
        created = browser.post(
            "/api/workflows",
            json=workflow_payload(),
            headers={"Idempotency-Key": "json_photo_workflow_123"},
        ).json()
        workflow_id = created["workflow_id"]
        approve_review(browser, created, key="json_photo_review_123")
        headers = {"Idempotency-Key": "json_photo_evidence_123"}
        first = browser.post(
            f"/api/workflows/{workflow_id}/evidence/photo?citation_id=1",
            json={"image_base64": encoded},
            headers=headers,
        )
        replay = browser.post(
            f"/api/workflows/{workflow_id}/evidence/photo?citation_id=1",
            json={"image_base64": encoded},
            headers=headers,
        )

    assert first.status_code == 200
    assert first.json()["evidence"][-1]["status"] == "accepted"
    assert replay.json() == first.json()


def test_json_photo_upload_rejects_invalid_base64_before_image_decode() -> None:
    workflows = WorkflowRegistry(photo_assessor=accept_photo)
    with client(workflows=workflows) as browser:
        workflow_id = browser.post(
            "/api/workflows",
            json=workflow_payload(),
            headers={"Idempotency-Key": "invalid_json_photo_workflow_123"},
        ).json()["workflow_id"]
        response = browser.post(
            f"/api/workflows/{workflow_id}/evidence/photo?citation_id=1",
            json={"image_base64": "not-valid-%%%"},
            headers={"Idempotency-Key": "invalid_json_photo_123"},
        )

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "invalid_photo",
        "message": "photo encoding is invalid",
    }


def test_json_photo_upload_enforces_configured_decoded_size_limit(monkeypatch) -> None:
    monkeypatch.setenv("METTLE_MAX_UPLOAD_BYTES", "100")
    workflows = WorkflowRegistry(photo_assessor=accept_photo)
    with client(workflows=workflows) as browser:
        workflow_id = browser.post(
            "/api/workflows",
            json=workflow_payload(),
            headers={"Idempotency-Key": "large_json_photo_workflow_123"},
        ).json()["workflow_id"]
        response = browser.post(
            f"/api/workflows/{workflow_id}/evidence/photo?citation_id=1",
            json={"image_base64": base64.b64encode(b"x" * 101).decode("ascii")},
            headers={"Idempotency-Key": "large_json_photo_123"},
        )

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "invalid_photo",
        "message": "photo exceeds the configured upload limit",
    }


def test_real_photo_upload_rejects_spoofed_content_and_oversize() -> None:
    workflows = WorkflowRegistry(photo_assessor=accept_photo)
    with client(workflows=workflows) as browser:
        workflow_id = browser.post(
            "/api/workflows",
            json=workflow_payload(),
            headers={"Idempotency-Key": "bad_photo_workflow_123"},
        ).json()["workflow_id"]
        spoofed = browser.post(
            f"/api/workflows/{workflow_id}/evidence/photo?citation_id=1",
            content=b"<svg><script>alert(1)</script></svg>",
            headers={
                "Content-Type": "image/png",
                "Idempotency-Key": "spoofed_photo_123",
            },
        )

    assert spoofed.status_code == 422
    assert spoofed.json()["error"]["code"] == "invalid_photo"


def test_recovery_check_is_idempotent_stops_closed_citation_and_interrupts_at_t_minus_two() -> None:
    with client() as browser:
        created = browser.post(
            "/api/workflows",
            json=workflow_payload(),
            headers={"Idempotency-Key": "check_workflow_123"},
        ).json()
        workflow_id = created["workflow_id"]
        approve_review(browser, created, key="check_review_123")
        browser.post(
            f"/api/workflows/{workflow_id}/evidence",
            json={"citation_id": "1", "sample_id": "panel_wide_measured"},
            headers={"Idempotency-Key": "check_evidence_123"},
        )
        headers = {"Idempotency-Key": "check_tick_123"}
        first = browser.post(
            f"/api/workflows/{workflow_id}/checks/next",
            json={},
            headers=headers,
        )
        replay = browser.post(
            f"/api/workflows/{workflow_id}/checks/next",
            json={},
            headers=headers,
        )
        critical = browser.post(
            f"/api/workflows/{workflow_id}/checks/next",
            json={},
            headers={"Idempotency-Key": "check_tick_critical_123"},
        )

    assert first.status_code == 200
    assert replay.json() == first.json()
    assert first.json()["snapshot"]["plan"]["as_of"] == "2026-08-14"
    assert [
        item["citation_id"] for item in first.json()["snapshot"]["deliveries"][-2:]
    ] == ["2", "3"]
    assert critical.json()["snapshot"]["status"] == "interrupted"
    assert critical.json()["snapshot"]["interrupts"][0]["name"] == "deadline-tradeoff"


def test_recovery_check_refuses_to_advance_past_pending_judgment() -> None:
    with client() as browser:
        created = browser.post(
            "/api/workflows",
            json=workflow_payload(),
            headers={"Idempotency-Key": "blocked_check_workflow_123"},
        ).json()
        blocked = browser.post(
            f"/api/workflows/{created['workflow_id']}/checks/next",
            json={},
            headers={"Idempotency-Key": "blocked_check_tick_123"},
        )

    assert blocked.status_code == 409
    assert "waiting for a contractor decision" in blocked.json()["error"]["message"]


def test_recovery_check_rejects_client_supplied_clock_state() -> None:
    with client() as browser:
        created = browser.post(
            "/api/workflows",
            json=workflow_payload(),
            headers={"Idempotency-Key": "strict_check_workflow_123"},
        ).json()
        response = browser.post(
            f"/api/workflows/{created['workflow_id']}/checks/next",
            json={"as_of": "2026-08-16"},
            headers={"Idempotency-Key": "strict_check_tick_123"},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_reinspection_packet_with_chase_history_has_stable_structure() -> None:
    with client() as browser:
        created = browser.post(
            "/api/workflows",
            json=workflow_payload(),
            headers={"Idempotency-Key": "chase_packet_workflow_123"},
        ).json()
        workflow_id = created["workflow_id"]
        approve_review(browser, created, key="chase_packet_review_123")
        browser.post(
            f"/api/workflows/{workflow_id}/evidence",
            json={"citation_id": "1", "sample_id": "panel_wide_measured"},
            headers={"Idempotency-Key": "chase_packet_evidence_1"},
        )
        browser.post(
            f"/api/workflows/{workflow_id}/checks/next",
            json={},
            headers={"Idempotency-Key": "chase_packet_check_t3"},
        )
        deadline = browser.post(
            f"/api/workflows/{workflow_id}/checks/next",
            json={},
            headers={"Idempotency-Key": "chase_packet_check_t2"},
        ).json()
        browser.post(
            f"/api/workflows/{workflow_id}/resume",
            json={
                "interrupt_id": deadline["snapshot"]["interrupts"][0]["interrupt_id"],
                "decision": "Keep the current reinspection date and continue critical follow-ups",
            },
            headers={"Idempotency-Key": "chase_packet_deadline_resume"},
        )
        for citation_id, sample_id in (
            ("2", "framing_plates_complete"),
            ("3", "mechanical_access_wide"),
        ):
            browser.post(
                f"/api/workflows/{workflow_id}/evidence",
                json={"citation_id": citation_id, "sample_id": sample_id},
                headers={"Idempotency-Key": f"chase_packet_evidence_{citation_id}"},
            )
        prepared = browser.post(
            f"/api/workflows/{workflow_id}/packet/prepare",
            json={},
            headers={"Idempotency-Key": "chase_packet_prepare_123"},
        ).json()
        browser.post(
            f"/api/workflows/{workflow_id}/packet/approve",
            json={
                "approval_id": prepared["packet"]["approval_id"],
                "decision": "Approve packet for reinspection scheduling",
            },
            headers={"Idempotency-Key": "chase_packet_approve_123"},
        )
        downloaded = browser.get(f"/api/workflows/{workflow_id}/packet.pdf")

    assert downloaded.status_code == 200
    reader = PdfReader(BytesIO(downloaded.content))
    assert len(reader.pages) == 5
    packet_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Recovery communication record" in packet_text


def test_dashboard_and_campaign_api_load() -> None:
    with client() as browser:
        page = browser.get("/")
        evidence_flow = browser.get("/static/evidence-flow.js")
        script = browser.get("/static/app.js")
        styles = browser.get("/static/styles.css")
        workbench = browser.get("/static/workbench.js")
        workbench_styles = browser.get("/static/workbench.css")
        campaign = browser.get("/api/campaign")

    assert page.status_code == 200
    assert evidence_flow.status_code == 200
    assert workbench.status_code == 200
    assert workbench_styles.status_code == 200
    assert "Recovery command center" in page.text
    assert "Start with the failed-inspection report" in page.text
    assert "Start a recovery" in page.text
    assert "Judge walkthrough" in page.text
    assert "Start my recovery" in page.text
    assert "What Mettle handled" in page.text
    assert "models interpret language and visible evidence; they never decide deadlines, gates, or what Mettle may claim" in page.text
    assert "The browser never owns the agent runtime." in page.text
    assert "Explore mode" not in page.text
    assert "JUDGE WALKTHROUGH · RECORDED SAMPLE" in page.text
    assert 'id="revise-source-button"' in page.text
    assert "YOUR RECOVERY PATH" in page.text
    assert 'id="workflow-journey"' in page.text
    assert 'id="judge-lens-impact"' in page.text
    assert 'id="judge-tour"' in page.text
    assert 'id="tour-skip"' in page.text
    assert 'id="tour-secondary"' in page.text
    assert "Same product, staged for evaluation" in page.text
    assert "Failed-inspection recovery stages" in page.text
    assert 'id="start-agentcore-button"' in page.text
    assert 'id="workflow-date-error"' in page.text
    assert 'id="start-workflow-button"' in page.text
    assert "Approve & start follow-up" in page.text
    assert "4 · Review" in page.text
    assert 'data-workspace-panel="correction"' in page.text
    assert 'id="correction-source-text"' in page.text
    assert '/static/workbench.js' in page.text
    assert '/static/workbench.css' in page.text
    assert "Inspectable Strands control flow" in page.text
    assert "STRANDS GRAPHBUILDER" in page.text
    assert "RUN RECEIPT · SANITIZED · READ ONLY" in page.text
    assert "What runs, what wakes it, where it stops." in page.text
    assert 'id="agent-flow"' in page.text
    assert 'id="photo-mode-note"' in page.text
    assert "Recovery navigation" in page.text
    assert "What needs attention" in page.text
    assert "Proof, review, and release" in page.text
    assert "Inspectable Strands control flow" in page.text
    assert 'data-workspace-view="recovery"' in page.text
    assert 'data-workspace-panel="activity"' in page.text
    assert "Demonstration controls" in page.text
    assert "Background activity" in page.text
    assert 'id="away-briefing"' in page.text
    assert 'id="theme-toggle"' in page.text
    assert 'id="error-title"' in page.text
    assert "Compress to next checkpoint" in page.text
    assert "Simulate scheduled check" not in page.text
    assert page.headers["content-security-policy"].startswith("default-src 'self'")
    assert script.status_code == 200
    assert "function exitRecoverySetup()" in script.text
    assert 'openRecoverySetup({ returnToWelcome: true });' in script.text
    assert 'elements.noticeDialog.addEventListener("cancel"' in script.text
    assert 'elements.noticeDialog.open && event.key === "Escape"' in script.text
    assert "function renderAgentRun(data)" in script.text
    assert "function renderCorrectionSummary(data)" in script.text
    assert "function renderProvenance(data)" in script.text
    assert "function renderAgentFlow(data)" in script.text
    assert "function agentFlowStage(" in script.text
    assert 'title: "Recover in the background"' in script.text
    assert 'title: "Stop for authority"' in script.text
    assert "const judgeLensByPhase" in script.text
    assert "function openWelcomeChooser()" in script.text
    assert "EventBridge wakes the deadline-chase graph" in script.text
    assert "function setWorkspaceView(view" in script.text
    assert "function openWorkspacePanel(view" in script.text
    assert "function buildBackgroundBrief(data)" in script.text
    assert "function renderBackgroundBrief(data)" in script.text
    assert "function setJudgeTourActive(active" in script.text
    assert "function resolveTheme()" in script.text
    assert "function applyTheme(theme" in script.text
    assert 'localStorage.setItem(themePreferenceKey, nextTheme)' in script.text
    assert "function tourPhase(data)" in script.text
    assert "function renderJudgeTour(data)" in script.text
    assert "function renderJourney(data)" in script.text
    assert "function hasApprovedEvidenceBoundary(data, citationId)" in script.text
    assert '<script src="/static/evidence-flow.js" defer></script>' in page.text
    assert "selectEvidenceCitation(data.citations, elements.photoCitation.value)" in script.text
    assert 'elements.photoFile.value = "";' in script.text
    assert "elements.photoForm.reset()" not in script.text
    assert "requestError.code = payload.error?.code" in script.text
    assert 'sessionStorage.setItem("mettle_post_auth_path"' in script.text
    assert 'sessionStorage.removeItem("mettle_post_auth_path")' in script.text
    assert 'sessionStorage.setItem("mettle_recovery_draft"' in script.text
    assert 'sessionStorage.removeItem("mettle_recovery_draft")' in script.text
    assert "function restoreRecoveryDraft()" in script.text
    assert "function recoveryWorkingDate()" in script.text
    assert "elements.startBedrock.hidden = true" in script.text
    assert 'Start the server with Bedrock enabled' not in page.text
    assert 'Start the server with Bedrock enabled' not in script.text
    assert 'response.headers.get("content-type")' in script.text
    assert 'code = "edge_request_failed"' in script.text
    assert '"Content-Type": "application/json"' in script.text
    assert "base64Standard(await file.arrayBuffer())" in script.text
    assert 'error.code === "workflow_not_found"' in script.text
    assert '"Recovery unavailable"' in script.text
    assert 'elements.retry.textContent = "Start a new recovery"' in script.text
    assert "!hasApprovedEvidenceBoundary(data, citationId)" in script.text
    assert 'citation.stage === "ready"' in script.text
    assert 'judgment.kind === "evidence_review"' in script.text
    assert 'disposition: submittedButton.dataset.disposition' in script.text
    assert "recoveryDateError(" in script.text
    assert 'openCount === 1 ? "correction still needs" : "corrections still need"' in script.text
    assert "async function runSampleUntilPause()" in script.text
    assert "function stageTourClock(days, cadence)" in script.text
    assert "function createPacketFinale(data)" in script.text
    assert "function createEvidenceComparison()" in script.text
    assert "function createTourAgentProof(data)" in script.text
    assert 'node("span", "tour-agent-proof__mode", "SAMPLE · STRANDS")' in script.text
    assert 'image: "/static/evidence/framing-closeup-insufficient.png"' in script.text
    assert '["Trades contacted", "0"]' in script.text
    assert 'title: "Outreach held before approval"' in script.text
    assert "Send a wider shot that identifies the corrected wall location." in script.text
    assert 'if (!phase.complete) artifacts.push(createTourAgentProof(data));' in script.text
    assert 'viewer.src = "/api/demo/packet/preview.pdf#page=2&toolbar=1&navpanes=0"' in script.text
    assert "Recorded synthetic assessment replayed. No model or AWS service was called." in script.text
    assert '"3 BEFORENODECALL GATES"' in script.text
    assert 'sessionStorage.setItem("mettle_entry_selected", "tour")' in script.text
    assert styles.status_code == 200
    assert ".workspace-panel--view-hidden" in styles.text
    assert ".citation__summary" in styles.text
    assert ".citation--needs-action" in styles.text
    assert ".packet-row" in styles.text
    assert ".agent-flow__track" in styles.text
    assert ".agent-flow__stage" in styles.text
    assert ".agent-flow__node--human" in styles.text
    assert ".judge-lens__item" in styles.text
    assert ".auth-control" in styles.text
    assert ".theme-toggle" in styles.text
    assert ':root[data-theme="light"]' in styles.text
    assert ".entry-choice--primary" in styles.text
    assert "--orange: #ff5a2f" in styles.text
    assert ".recovery-line" in styles.text
    assert ".command-stack { position: sticky" in styles.text
    assert ".packet-layout" in styles.text
    assert ".aws-boundary__flow" in styles.text
    assert ".welcome-dialog__grid" in styles.text
    assert ".product-workspace" in styles.text
    assert ".demo-driver { display: none" in styles.text
    assert "function createCoordinationTimeline(data)" in script.text
    assert "function createTourWorkspaceFrame(data, phase, artifacts)" in script.text
    assert campaign.status_code == 200
    assert campaign.json()["notice_id"] == "CR-2026-0417"


def test_contractor_can_import_a_text_notice_without_persisting_the_file() -> None:
    encoded = base64.b64encode(NOTICE.encode("utf-8")).decode("ascii")
    with client() as browser:
        response = browser.post(
            "/api/notices/text",
            json={"filename": "redacted-notice.txt", "file_base64": encoded},
        )

    assert response.status_code == 200
    assert response.json() == {"text": NOTICE.strip()}


def test_cloudfront_forwards_only_the_guided_demo_session_cookie() -> None:
    static_policy = WEB_TEMPLATE.split("  StaticCachePolicy:", 1)[1].split(
        "  ApiCachePolicy:", 1
    )[0]
    api_cache_policy = WEB_TEMPLATE.split("  ApiCachePolicy:", 1)[1].split(
        "  ApiOriginRequestPolicy:", 1
    )[0]
    api_origin_policy = WEB_TEMPLATE.split("  ApiOriginRequestPolicy:", 1)[1].split(
        "  WebAcl:", 1
    )[0]

    assert "CookieBehavior: none" in static_policy
    assert "mettle_demo_session" not in static_policy
    assert "CookieBehavior: none" in api_cache_policy
    assert "mettle_demo_session" not in api_cache_policy
    assert "CookieBehavior: whitelist" in api_origin_policy
    assert "- mettle_demo_session" in api_origin_policy
    assert "CookieBehavior: all" not in WEB_TEMPLATE


def test_advance_replay_is_idempotent_at_http_boundary() -> None:
    payload = {"idempotency_key": "replay_key_123"}
    with client() as browser:
        browser.post(
            "/api/judgments/route-review/resolve",
            json={"decision": "Approve routes with a wide mechanical photo"},
        )
        first = browser.post("/api/demo/advance", json=payload)
        replay = browser.post("/api/demo/advance", json=payload)

    assert first.status_code == 200
    assert replay.status_code == 200
    assert replay.json()["scenario_step"] == first.json()["scenario_step"] == 1
    assert replay.json()["metrics"] == first.json()["metrics"]


def test_guided_demo_state_is_isolated_per_browser_session() -> None:
    app = create_app(store=DemoStore())
    with TestClient(app) as first_browser, TestClient(app) as second_browser:
        assert first_browser.get("/api/campaign").json()["scenario_step"] == 0
        assert second_browser.get("/api/campaign").json()["scenario_step"] == 0

        first_browser.post(
            "/api/judgments/route-review/resolve",
            json={"decision": "Approve routes with a wide mechanical photo"},
        )
        advanced = first_browser.post(
            "/api/demo/advance",
            json={"idempotency_key": "isolated_browser_advance_123"},
        )

        assert advanced.status_code == 200
        assert advanced.json()["scenario_step"] == 1
        assert second_browser.get("/api/campaign").json()["scenario_step"] == 0


def test_guided_demo_session_cookie_is_opaque_and_hardened() -> None:
    app = create_app(store=DemoStore())
    with TestClient(app, base_url="https://testserver") as browser:
        response = browser.get("/api/campaign")

    cookie = response.headers["set-cookie"]
    assert "mettle_demo_session=" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=lax" in cookie
    assert "Max-Age=7200" in cookie

def test_guided_demo_packet_requires_approval_then_downloads_pdf() -> None:
    with client() as browser:
        blocked = browser.get("/api/demo/packet.pdf")
        browser.post(
            "/api/judgments/route-review/resolve",
            json={"decision": "Wide photo showing equipment and measured service clearance"},
        )
        for step in range(3):
            browser.post(
                "/api/demo/advance",
                json={"idempotency_key": f"demo_packet_before_{step}"},
            )
        browser.post(
            "/api/judgments/deadline-choice/resolve",
            json={"decision": "Keep the date and continue critical recovery"},
        )
        for step in range(3, 6):
            campaign = browser.post(
                "/api/demo/advance",
                json={"idempotency_key": f"demo_packet_after_{step}"},
            ).json()
        browser.post(
            "/api/judgments/final-approval/resolve",
            json={"decision": "Approve packet for reinspection scheduling"},
        )
        downloaded = browser.get("/api/demo/packet.pdf")
        previewed = browser.get("/api/demo/packet/preview.pdf")

    assert blocked.status_code == 409
    assert campaign["packet_status"] == "awaiting_approval"
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "application/pdf"
    assert len(PdfReader(BytesIO(downloaded.content)).pages) == 5
    assert len(downloaded.content) < 4_000_000
    assert previewed.status_code == 200
    assert previewed.headers["content-disposition"].startswith("inline;")
    assert previewed.headers["x-frame-options"] == "SAMEORIGIN"
    assert "frame-ancestors 'self'" in previewed.headers["content-security-policy"]
    assert len(PdfReader(BytesIO(previewed.content)).pages) == 5


def test_api_rejects_oversized_decision_and_unknown_fields() -> None:
    with client() as browser:
        oversized = browser.post(
            "/api/judgments/route-review/resolve",
            json={"decision": "x" * 501},
        )
        unknown = browser.post(
            "/api/demo/advance",
            json={"idempotency_key": "valid_key_123", "admin": True},
        )

    assert oversized.status_code == 422
    assert oversized.json()["error"]["code"] == "invalid_request"
    assert unknown.status_code == 422


def test_api_returns_actionable_conflict_for_changed_replay() -> None:
    with client() as browser:
        first = browser.post(
            "/api/judgments/route-review/resolve",
            json={"decision": "Use a wide equipment-clearance photo"},
        )
        conflict = browser.post(
            "/api/judgments/route-review/resolve",
            json={"decision": "Use a different decision"},
        )

    assert first.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json() == {
        "error": {
            "code": "conflict",
            "message": "this judgment was already resolved differently",
        }
    }


def test_workflow_api_runs_real_strands_graph_and_restores_snapshot() -> None:
    headers = {"Idempotency-Key": "create_workflow_123"}
    with client() as browser:
        created = browser.post("/api/workflows", json=workflow_payload(), headers=headers)
        restored = browser.get(f"/api/workflows/{created.json()['workflow_id']}")

    assert created.status_code == 201
    assert restored.status_code == 200
    assert created.json() == restored.json()
    assert created.json()["snapshot"]["status"] == "interrupted"
    assert len(created.json()["snapshot"]["deliveries"]) == 0
    assert created.json()["snapshot"]["interrupts"][0]["name"] == "correction-review"


def test_workflow_rejects_working_date_on_or_after_reinspection_deadline() -> None:
    for index, as_of in enumerate(("2026-08-17", "2026-08-18")):
        payload = workflow_payload()
        payload["as_of"] = as_of
        with client() as browser:
            response = browser.post(
                "/api/workflows",
                json=payload,
                headers={"Idempotency-Key": f"expired_workflow_{index}_123"},
            )

        assert response.status_code == 422
        assert response.json()["error"] == {
            "code": "workflow_configuration_error",
            "message": "The working date must be before the notice's reinspection deadline. Update the working date or use a current notice.",
        }


def test_workflow_rejects_working_date_before_notice_issue_date() -> None:
    payload = workflow_payload()
    payload["as_of"] = "2026-08-06"
    with client() as browser:
        response = browser.post(
            "/api/workflows",
            json=payload,
            headers={"Idempotency-Key": "future_notice_workflow_123"},
        )

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "workflow_configuration_error",
        "message": "The working date cannot be before the notice's inspection date. Update the working date or use a current notice.",
    }


def test_workflow_accepts_a_second_municipal_notice_shape_and_pauses_before_outreach() -> None:
    payload = workflow_payload(notice_text=DENVER_NOTICE)
    payload["as_of"] = "2026-08-21"
    with client() as browser:
        created = browser.post(
            "/api/workflows",
            json=payload,
            headers={"Idempotency-Key": "denver_notice_shape_123"},
        )

    assert created.status_code == 201
    snapshot = created.json()["snapshot"]
    assert snapshot["notice"]["notice_id"] == "2026-RES-00981"
    assert len(snapshot["notice"]["citations"]) == 2
    assert snapshot["deliveries"] == []
    assert snapshot["interrupts"][0]["name"] == "correction-review"


def test_workflow_api_returns_actionable_error_for_unsupported_notice() -> None:
    with client() as browser:
        response = browser.post(
            "/api/workflows",
            json=workflow_payload(notice_text="A correction happened somewhere."),
            headers={"Idempotency-Key": "unsupported_notice_123"},
        )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "unsupported_notice_format",
            "message": "Mettle could not identify the notice schedule or correction lines. Keep the permit or record ID, inspection date, reinspection deadline, property address, and numbered correction text in the paste.",
        }
    }


def test_workflow_create_replay_is_idempotent_and_changed_replay_conflicts() -> None:
    headers = {"Idempotency-Key": "create_workflow_456"}
    with client() as browser:
        first = browser.post("/api/workflows", json=workflow_payload(), headers=headers)
        replay = browser.post("/api/workflows", json=workflow_payload(), headers=headers)
        changed = browser.post(
            "/api/workflows",
            json=workflow_payload(notice_text=NOTICE.replace("100 Demo Way", "200 Demo Way")),
            headers=headers,
        )

    assert first.status_code == 201
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert changed.status_code == 409
    assert changed.json()["error"]["code"] == "idempotency_conflict"


def test_live_bedrock_workflow_runs_inside_graph_and_replays_without_second_call() -> None:
    calls: list[str] = []

    def bedrock_intake(text: str):
        calls.append(text)
        return parse_notice(text)

    workflows = WorkflowRegistry(bedrock_intake=bedrock_intake)
    headers = {"Idempotency-Key": "bedrock_workflow_123"}
    payload = workflow_payload(intake_provider="bedrock")
    with client(workflows=workflows) as browser:
        capabilities = browser.get("/api/capabilities")
        first = browser.post("/api/workflows", json=payload, headers=headers)
        replay = browser.post("/api/workflows", json=payload, headers=headers)

    assert capabilities.json() == {
        "bedrock_intake": True,
        "agentcore_runtime": False,
        "photo_evidence": False,
        "max_photo_bytes": 5_000_000,
    }
    assert first.status_code == 201
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert first.json()["intake_provider"] == "bedrock"
    assert first.json()["snapshot"]["status"] == "interrupted"
    assert calls == [NOTICE]


def test_live_bedrock_workflow_fails_closed_when_server_has_not_enabled_it() -> None:
    with client() as browser:
        capabilities = browser.get("/api/capabilities")
        response = browser.post(
            "/api/workflows",
            json=workflow_payload(intake_provider="bedrock"),
            headers={"Idempotency-Key": "bedrock_disabled_123"},
        )

    assert capabilities.json() == {
        "bedrock_intake": False,
        "agentcore_runtime": False,
        "photo_evidence": False,
        "max_photo_bytes": 5_000_000,
    }
    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "workflow_configuration_error",
        "message": "live Bedrock intake is not enabled on this server",
    }


def test_live_bedrock_failure_is_safe_and_retryable() -> None:
    def failing_intake(_text: str):
        raise BedrockIntakeError("Bedrock could not be reached with the current AWS configuration")

    workflows = WorkflowRegistry(bedrock_intake=failing_intake)
    with client(workflows=workflows) as browser:
        response = browser.post(
            "/api/workflows",
            json=workflow_payload(intake_provider="bedrock"),
            headers={"Idempotency-Key": "bedrock_failure_123"},
        )

    assert response.status_code == 502
    assert response.headers["retry-after"] == "5"
    assert response.json()["error"] == {
        "code": "bedrock_intake_failed",
        "message": "Bedrock could not be reached with the current AWS configuration",
    }


def test_agentcore_http_boundary_starts_restores_and_resumes_cloud_workflow() -> None:
    cloud = FakeAgentCoreGateway()
    payload = workflow_payload(intake_provider="bedrock")
    with client(agentcore=cloud) as browser:
        capabilities = browser.get("/api/capabilities")
        created = browser.post(
            "/api/agentcore/workflows",
            json=payload,
            headers={"Idempotency-Key": "agentcore_create_123"},
        )
        workflow_id = created.json()["workflow_id"]
        restored = browser.get(f"/api/agentcore/workflows/{workflow_id}")
        resumed = approve_review(
            browser,
            created.json(),
            key="agentcore_review_123",
            root="/api/agentcore/workflows",
        )
        evidence_responses = []
        for index, (citation_id, sample_id) in enumerate(
            [
                ("1", "panel_wide_measured"),
                ("2", "framing_plates_complete"),
                ("3", "mechanical_access_wide"),
            ]
        ):
            evidence_responses.append(
                browser.post(
                    f"/api/agentcore/workflows/{workflow_id}/evidence",
                    json={"citation_id": citation_id, "sample_id": sample_id},
                    headers={"Idempotency-Key": f"agentcore_evidence_{index}"},
                )
            )
        prepared = browser.post(
            f"/api/agentcore/workflows/{workflow_id}/packet/prepare",
            json={},
            headers={"Idempotency-Key": "agentcore_prepare_123"},
        )
        approved = browser.post(
            f"/api/agentcore/workflows/{workflow_id}/packet/approve",
            json={
                "approval_id": prepared.json()["packet"]["approval_id"],
                "decision": "Approve packet for reinspection scheduling",
            },
            headers={"Idempotency-Key": "agentcore_approve_123"},
        )
        downloaded = browser.get(
            f"/api/agentcore/workflows/{workflow_id}/packet.pdf"
        )

    assert capabilities.json() == {
        "bedrock_intake": False,
        "agentcore_runtime": True,
        "photo_evidence": True,
        "max_photo_bytes": 5_000_000,
    }
    assert created.status_code == 201
    assert restored.json() == created.json()
    assert resumed.status_code == 200
    assert resumed.json()["snapshot"]["status"] == "completed"
    assert len(resumed.json()["snapshot"]["deliveries"]) == 3
    assert all(item.json()["evidence"][-1]["status"] == "accepted" for item in evidence_responses)
    assert approved.json()["packet"]["status"] == "approved"
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "application/pdf"
    assert len(PdfReader(BytesIO(downloaded.content)).pages) == 5


def test_agentcore_http_boundary_fails_closed_without_explicit_server_enablement() -> None:
    with client() as browser:
        disabled = browser.post(
            "/api/agentcore/workflows",
            json=workflow_payload(intake_provider="bedrock"),
            headers={"Idempotency-Key": "agentcore_disabled_123"},
        )
        wrong_provider = browser.post(
            "/api/agentcore/workflows",
            json=workflow_payload(intake_provider="local"),
            headers={"Idempotency-Key": "agentcore_provider_123"},
        )

    assert disabled.status_code == 422
    assert disabled.json()["error"] == {
        "code": "workflow_configuration_error",
        "message": "AgentCore execution is not enabled on this server",
    }
    assert wrong_provider.status_code == 422
    assert wrong_provider.json()["error"]["message"] == (
        "AgentCore execution requires live Bedrock notice intake"
    )


def test_workflow_review_is_idempotent_and_does_not_duplicate_outreach() -> None:
    with client() as browser:
        created = browser.post(
            "/api/workflows",
            json=workflow_payload(),
            headers={"Idempotency-Key": "create_workflow_789"},
        ).json()
        workflow_id = created["workflow_id"]
        payload = review_payload(created)
        headers = {"Idempotency-Key": "review_workflow_789"}
        first = browser.post(f"/api/workflows/{workflow_id}/review", json=payload, headers=headers)
        replay = browser.post(f"/api/workflows/{workflow_id}/review", json=payload, headers=headers)

    assert first.status_code == 200
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert first.json()["snapshot"]["status"] == "completed"
    assert len(first.json()["snapshot"]["deliveries"]) == 3
    assert first.json()["snapshot"]["deliveries"][-1]["recipient"]["name"] == "Luis Vega"


def test_workflow_blocks_actions_until_complete_valid_correction_review() -> None:
    with client() as browser:
        created = browser.post(
            "/api/workflows",
            json=workflow_payload(),
            headers={"Idempotency-Key": "review_boundary_create_123"},
        ).json()
        evidence_before_review = browser.post(
            f"/api/workflows/{created['workflow_id']}/evidence",
            json={"citation_id": "1", "sample_id": "panel_wide_measured"},
            headers={"Idempotency-Key": "review_boundary_evidence_123"},
        )
        invalid = review_payload(created)
        invalid["citations"][0]["evidence_requirements"] = []
        invalid_review = browser.post(
            f"/api/workflows/{created['workflow_id']}/review",
            json=invalid,
            headers={"Idempotency-Key": "review_boundary_invalid_123"},
        )

    assert created["snapshot"]["deliveries"] == []
    assert evidence_before_review.status_code == 422
    assert evidence_before_review.json()["error"]["code"] == "invalid_evidence_submission"
    assert invalid_review.status_code == 422
    assert invalid_review.json()["error"]["code"] == "invalid_request"


def test_workflow_api_rejects_bad_boundaries_and_unknown_runs() -> None:
    with client() as browser:
        missing_key = browser.post("/api/workflows", json=workflow_payload())
        unknown_field = browser.post(
            "/api/workflows",
            json={**workflow_payload(), "send_live_sms": True},
            headers={"Idempotency-Key": "invalid_workflow_123"},
        )
        oversized = browser.post(
            "/api/workflows",
            json=workflow_payload(notice_text="x" * 100_001),
            headers={"Idempotency-Key": "invalid_workflow_456"},
        )
        missing = browser.get("/api/workflows/not-a-real-workflow")

    assert missing_key.status_code == 422
    assert unknown_field.status_code == 422
    assert oversized.status_code == 422
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "workflow_not_found"


def test_workflow_api_explains_missing_trade_configuration() -> None:
    payload = workflow_payload()
    payload["roster"] = payload["roster"][:1]
    with client() as browser:
        created = browser.post(
            "/api/workflows",
            json=payload,
            headers={"Idempotency-Key": "missing_roster_123"},
        ).json()
        response = approve_review(browser, created, key="missing_roster_review_123")

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "workflow_configuration_error",
        "message": "missing recipient for trade(s): framing, mechanical",
    }


def test_failed_correction_review_retry_remains_stable() -> None:
    payload = workflow_payload()
    payload["roster"] = payload["roster"][:1]
    with client() as browser:
        created = browser.post(
            "/api/workflows",
            json=payload,
            headers={"Idempotency-Key": "failed_review_workflow_123"},
        ).json()
        review = review_payload(created)
        url = f"/api/workflows/{created['workflow_id']}/review"
        first = browser.post(
            url,
            json=review,
            headers={"Idempotency-Key": "failed_review_retry_123"},
        )
        retry = browser.post(
            url,
            json=review,
            headers={"Idempotency-Key": "failed_review_retry_123"},
        )

    assert first.status_code == retry.status_code == 422
    assert first.json() == retry.json() == {
        "error": {
            "code": "workflow_configuration_error",
            "message": "missing recipient for trade(s): framing, mechanical",
        }
    }


def test_evidence_api_rejects_then_accepts_notice_anchored_samples() -> None:
    with client() as browser:
        create_headers = {"Idempotency-Key": "evidence_workflow_123"}
        created_response = browser.post(
            "/api/workflows",
            json=workflow_payload(),
            headers=create_headers,
        )
        created = created_response.json()
        workflow_id = created["workflow_id"]
        approve_review(browser, created, key="evidence_review_123")
        rejected = browser.post(
            f"/api/workflows/{workflow_id}/evidence",
            json={"citation_id": "1", "sample_id": "panel_closeup_insufficient"},
            headers={"Idempotency-Key": "evidence_closeup_123"},
        )
        accepted = browser.post(
            f"/api/workflows/{workflow_id}/evidence",
            json={"citation_id": "1", "sample_id": "panel_wide_measured"},
            headers={"Idempotency-Key": "evidence_wide_123"},
        )
        create_replay = browser.post(
            "/api/workflows",
            json=workflow_payload(),
            headers=create_headers,
        )

    assert rejected.status_code == 200
    assert rejected.json()["evidence"][-1]["status"] == "rejected"
    assert len(rejected.json()["evidence"][-1]["missing_requirements"]) == 2
    assert accepted.status_code == 200
    assert accepted.json()["evidence"][-1]["status"] == "accepted"
    assert accepted.json()["evidence"][-1]["missing_requirements"] == []
    assert create_replay.json() == created_response.json()
    assert create_replay.json()["evidence"] == []


def test_evidence_replay_is_idempotent_and_changed_replay_conflicts() -> None:
    with client() as browser:
        created = browser.post(
            "/api/workflows",
            json=workflow_payload(),
            headers={"Idempotency-Key": "evidence_workflow_456"},
        ).json()
        approve_review(browser, created, key="evidence_replay_review_456")
        path = f"/api/workflows/{created['workflow_id']}/evidence"
        headers = {"Idempotency-Key": "evidence_replay_456"}
        payload = {"citation_id": "1", "sample_id": "panel_closeup_insufficient"}
        first = browser.post(path, json=payload, headers=headers)
        replay = browser.post(path, json=payload, headers=headers)
        changed = browser.post(
            path,
            json={"citation_id": "1", "sample_id": "panel_wide_measured"},
            headers=headers,
        )

    assert replay.json() == first.json()
    assert len(replay.json()["evidence"]) == 1
    assert changed.status_code == 409


def test_packet_prepare_requires_every_citation_to_have_accepted_evidence() -> None:
    with client() as browser:
        created = browser.post(
            "/api/workflows",
            json=workflow_payload(),
            headers={"Idempotency-Key": "packet_incomplete_123"},
        ).json()
        response = browser.post(
            f"/api/workflows/{created['workflow_id']}/packet/prepare",
            json={},
            headers={"Idempotency-Key": "packet_prepare_incomplete_123"},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "packet_not_ready"
    assert "1, 2, 3" in response.json()["error"]["message"]


def test_packet_requires_final_approval_then_downloads_verified_pdf() -> None:
    with client() as browser:
        workflow_id, _created = ready_workflow(browser)
        prepared = browser.post(
            f"/api/workflows/{workflow_id}/packet/prepare",
            json={},
            headers={"Idempotency-Key": "packet_prepare_123"},
        )
        blocked_download = browser.get(f"/api/workflows/{workflow_id}/packet.pdf")
        approval_id = prepared.json()["packet"]["approval_id"]
        approved = browser.post(
            f"/api/workflows/{workflow_id}/packet/approve",
            json={
                "approval_id": approval_id,
                "decision": "Approve packet for reinspection scheduling",
            },
            headers={"Idempotency-Key": "packet_approve_123"},
        )
        approval_replay = browser.post(
            f"/api/workflows/{workflow_id}/packet/approve",
            json={
                "approval_id": approval_id,
                "decision": "Approve packet for reinspection scheduling",
            },
            headers={"Idempotency-Key": "packet_approve_123"},
        )
        pdf = browser.get(f"/api/workflows/{workflow_id}/packet.pdf")

    assert prepared.status_code == 200
    assert prepared.json()["packet"]["status"] == "awaiting_approval"
    assert blocked_download.status_code == 409
    assert approved.status_code == 200
    assert approved.json()["packet"]["status"] == "approved"
    assert approval_replay.json() == approved.json()
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF-")
    text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf.content)).pages)
    normalized_text = " ".join(text.split())
    assert "CR-2026-0417" in text
    assert "APPROVED BY CONTRACTOR" in text
    assert "does not certify code compliance" in normalized_text
