import io
import json

import pytest

from mettle.agentcore_client import AgentCoreInvocationError, invoke_json


class RecordingClient:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.requests: list[dict] = []

    def invoke_agent_runtime(self, **kwargs):
        self.requests.append(kwargs)
        return self.response


def test_invoke_json_preserves_session_and_sends_bounded_json() -> None:
    client = RecordingClient(
        {"statusCode": 200, "response": io.BytesIO(b'{"ok":true}')}
    )
    session_id = "mettle-cloud-session-12345678901234567890"

    result = invoke_json(
        client,
        runtime_arn="arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/example",
        session_id=session_id,
        payload={"operation": "start", "notice_text": "synthetic"},
    )

    assert result == {"ok": True}
    request = client.requests[0]
    assert request["runtimeSessionId"] == session_id
    assert request["qualifier"] == "DEFAULT"
    assert json.loads(request["payload"]) == {
        "operation": "start",
        "notice_text": "synthetic",
    }


def test_invoke_json_rejects_short_sessions_before_network_call() -> None:
    client = RecordingClient({})

    with pytest.raises(ValueError, match="between 33 and 256"):
        invoke_json(
            client,
            runtime_arn="arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/example",
            session_id="too-short",
            payload={},
        )

    assert client.requests == []


def test_invoke_json_rejects_non_json_runtime_response() -> None:
    client = RecordingClient({"statusCode": 200, "response": io.BytesIO(b"oops")})

    with pytest.raises(AgentCoreInvocationError, match="invalid JSON"):
        invoke_json(
            client,
            runtime_arn="arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/example",
            session_id="mettle-cloud-session-12345678901234567890",
            payload={},
        )
