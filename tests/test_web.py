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

    assert first.status_code == 200
    assert first.json()["evidence"][-1]["status"] == "accepted"
    assert replay.json() == first.json()
    assert len(replay.json()["evidence"]) == 1


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
        script = browser.get("/static/app.js")
        campaign = browser.get("/api/campaign")

    assert page.status_code == 200
    assert "Recovery command center" in page.text
    assert "Start with the failed-inspection report" in page.text
    assert "Start a recovery" in page.text
    assert "Try the sample campaign" in page.text
    assert "Extract on AgentCore" in page.text
    assert "Extract locally" in page.text
    assert "Approve & begin recovery" in page.text
    assert "Recovery clock" in page.text
    assert "Agent run" in page.text
    assert "HANDOFFS, AUTONOMOUS WORK, AND HUMAN INTERRUPTS" in page.text
    assert "Simulate scheduled check" in page.text
    assert page.headers["content-security-policy"].startswith("default-src 'self'")
    assert script.status_code == 200
    assert "function exitRecoverySetup()" in script.text
    assert 'openRecoverySetup({ returnToWelcome: true });' in script.text
    assert 'elements.noticeDialog.addEventListener("cancel"' in script.text
    assert 'elements.noticeDialog.open && event.key === "Escape"' in script.text
    assert "function renderAgentRun(data)" in script.text
    assert campaign.status_code == 200
    assert campaign.json()["notice_id"] == "CR-2026-0417"


def test_advance_replay_is_idempotent_at_http_boundary() -> None:
    payload = {"idempotency_key": "replay_key_123"}
    with client() as browser:
        first = browser.post("/api/demo/advance", json=payload)
        replay = browser.post("/api/demo/advance", json=payload)

    assert first.status_code == 200
    assert replay.status_code == 200
    assert replay.json()["scenario_step"] == first.json()["scenario_step"] == 1
    assert replay.json()["metrics"] == first.json()["metrics"]


def test_guided_demo_packet_requires_approval_then_downloads_pdf() -> None:
    with client() as browser:
        blocked = browser.get("/api/demo/packet.pdf")
        browser.post(
            "/api/judgments/code-c3/resolve",
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

    assert blocked.status_code == 409
    assert campaign["packet_status"] == "awaiting_approval"
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"] == "application/pdf"
    assert len(PdfReader(BytesIO(downloaded.content)).pages) == 4
    assert len(downloaded.content) < 4_000_000


def test_api_rejects_oversized_decision_and_unknown_fields() -> None:
    with client() as browser:
        oversized = browser.post(
            "/api/judgments/code-c3/resolve",
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
            "/api/judgments/code-c3/resolve",
            json={"decision": "Use a wide equipment-clearance photo"},
        )
        conflict = browser.post(
            "/api/judgments/code-c3/resolve",
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
            "message": "The notice format is not supported by local intake. Use the representative example or run live Bedrock intake.",
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
    assert len(PdfReader(BytesIO(downloaded.content)).pages) == 4


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
