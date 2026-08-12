from __future__ import annotations

import json
from typing import Any, Protocol


class AgentCoreResponseBody(Protocol):
    def read(self) -> bytes: ...


class AgentCoreDataClient(Protocol):
    def invoke_agent_runtime(self, **kwargs: Any) -> dict[str, Any]: ...


class AgentCoreInvocationError(RuntimeError):
    """Raised when a deployed runtime returns an invalid response."""


def invoke_json(
    client: AgentCoreDataClient,
    *,
    runtime_arn: str,
    session_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Invoke one AgentCore session without logging its sensitive payload."""
    if not runtime_arn.startswith("arn:aws:bedrock-agentcore:"):
        raise ValueError("runtime_arn must be an Amazon Bedrock AgentCore ARN")
    if not 33 <= len(session_id) <= 256:
        raise ValueError("session_id must be between 33 and 256 characters")

    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        runtimeSessionId=session_id,
        qualifier="DEFAULT",
        contentType="application/json",
        accept="application/json",
        payload=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
    )
    status = response.get("statusCode")
    if status is not None and not 200 <= int(status) < 300:
        raise AgentCoreInvocationError(f"AgentCore invocation failed with HTTP {status}")

    body = response.get("response") or response.get("payload")
    if body is None or not hasattr(body, "read"):
        raise AgentCoreInvocationError("AgentCore returned no readable response body")
    try:
        decoded = json.loads(body.read().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError) as exc:
        raise AgentCoreInvocationError("AgentCore returned invalid JSON") from exc
    if not isinstance(decoded, dict):
        raise AgentCoreInvocationError("AgentCore returned a non-object JSON response")
    return decoded
