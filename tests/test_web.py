from fastapi.testclient import TestClient

from mettle.demo import DemoStore
from mettle.web.app import create_app


def client() -> TestClient:
    return TestClient(create_app(store=DemoStore()))


def test_dashboard_and_campaign_api_load() -> None:
    with client() as browser:
        page = browser.get("/")
        campaign = browser.get("/api/campaign")

    assert page.status_code == 200
    assert "Recovery command center" in page.text
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
