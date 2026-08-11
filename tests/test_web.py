from pathlib import Path

from fastapi.testclient import TestClient

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
