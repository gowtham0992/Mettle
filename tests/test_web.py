from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfReader

from mettle.demo import DemoStore
from mettle.web.app import create_app


NOTICE = Path("examples/notices/failed-rough-in.txt").read_text(encoding="utf-8")


def workflow_payload(*, notice_text: str = NOTICE) -> dict:
    return {
        "notice_text": notice_text,
        "as_of": "2026-08-10",
        "roster": [
            {"trade": "electrical", "name": "Mike Alvarez", "phone": "+13035550101"},
            {"trade": "framing", "name": "Jen Ortiz", "phone": "+13035550102"},
            {"trade": "mechanical", "name": "Luis Vega", "phone": "+13035550103"},
        ],
    }


def ready_workflow(browser: TestClient) -> tuple[str, dict]:
    created = browser.post(
        "/api/workflows",
        json=workflow_payload(),
        headers={"Idempotency-Key": "packet_workflow_123"},
    ).json()
    workflow_id = created["workflow_id"]
    interrupt_id = created["snapshot"]["interrupts"][0]["interrupt_id"]
    resumed = browser.post(
        f"/api/workflows/{workflow_id}/resume",
        json={
            "interrupt_id": interrupt_id,
            "decision": "Wide photo showing equipment clearance with the access panel open",
        },
        headers={"Idempotency-Key": "packet_resume_123"},
    )
    assert resumed.status_code == 200
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


def client() -> TestClient:
    return TestClient(create_app(store=DemoStore()))


def test_dashboard_and_campaign_api_load() -> None:
    with client() as browser:
        page = browser.get("/")
        campaign = browser.get("/api/campaign")

    assert page.status_code == 200
    assert "Recovery command center" in page.text
    assert "Load a failed-inspection notice" in page.text
    assert page.headers["content-security-policy"].startswith("default-src 'self'")
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
    assert len(created.json()["snapshot"]["deliveries"]) == 2
    assert created.json()["snapshot"]["interrupts"][0]["name"] == "contractor-judgment"


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


def test_workflow_resume_is_idempotent_and_does_not_duplicate_outreach() -> None:
    with client() as browser:
        created = browser.post(
            "/api/workflows",
            json=workflow_payload(),
            headers={"Idempotency-Key": "create_workflow_789"},
        ).json()
        workflow_id = created["workflow_id"]
        interrupt_id = created["snapshot"]["interrupts"][0]["interrupt_id"]
        payload = {
            "interrupt_id": interrupt_id,
            "decision": "Use a wide equipment-clearance photo with the panel open.",
        }
        headers = {"Idempotency-Key": "resume_workflow_789"}
        first = browser.post(f"/api/workflows/{workflow_id}/resume", json=payload, headers=headers)
        replay = browser.post(f"/api/workflows/{workflow_id}/resume", json=payload, headers=headers)

    assert first.status_code == 200
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert first.json()["snapshot"]["status"] == "completed"
    assert len(first.json()["snapshot"]["deliveries"]) == 3
    assert first.json()["snapshot"]["deliveries"][-1]["recipient"]["name"] == "Luis Vega"


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
        response = browser.post(
            "/api/workflows",
            json=payload,
            headers={"Idempotency-Key": "missing_roster_123"},
        )

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "workflow_configuration_error",
        "message": "missing recipient for trade(s): framing",
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
