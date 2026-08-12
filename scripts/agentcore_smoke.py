from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

import boto3

from mettle.agentcore_client import AgentCoreInvocationError, invoke_json


EXPECTED_ARN_PREFIX = (
    "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/"
)


def _summary(response: dict) -> dict:
    workflow = response.get("workflow", {})
    snapshot = workflow.get("snapshot", {})
    return {
        "ok": response.get("ok"),
        "replayed": response.get("replayed"),
        "workflow_id": workflow.get("workflow_id"),
        "status": snapshot.get("status"),
        "deliveries": len(snapshot.get("deliveries", [])),
        "interrupts": len(snapshot.get("interrupts", [])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Mettle's paid start/resume AgentCore cloud smoke test."
    )
    parser.add_argument("--runtime-arn", required=True)
    parser.add_argument("--profile", default="mettle-agentcore")
    parser.add_argument("--region", default="us-east-1", choices=("us-east-1",))
    args = parser.parse_args()
    if not args.runtime_arn.startswith(EXPECTED_ARN_PREFIX):
        parser.error("runtime ARN must be a Mettle runtime in the approved account and region")

    notice = Path("examples/notices/failed-rough-in.txt").read_text(encoding="utf-8")
    session_id = f"mettle-smoke-{uuid.uuid4()}"
    client = boto3.Session(profile_name=args.profile, region_name=args.region).client(
        "bedrock-agentcore"
    )

    started = invoke_json(
        client,
        runtime_arn=args.runtime_arn,
        session_id=session_id,
        payload={
            "operation": "start",
            "idempotency_key": f"start_{uuid.uuid4().hex}",
            "payload": {
                "notice_text": notice,
                "intake_provider": "bedrock",
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
            },
        },
    )
    if not started.get("ok"):
        raise AgentCoreInvocationError("start operation failed")
    workflow = started["workflow"]
    interrupts = workflow["snapshot"]["interrupts"]
    if len(interrupts) != 1:
        raise AgentCoreInvocationError("start did not produce exactly one judgment")
    print(json.dumps({"start": _summary(started)}, indent=2))

    resumed = invoke_json(
        client,
        runtime_arn=args.runtime_arn,
        session_id=session_id,
        payload={
            "operation": "resume",
            "idempotency_key": f"resume_{uuid.uuid4().hex}",
            "workflow_id": workflow["workflow_id"],
            "payload": {
                "interrupt_id": interrupts[0]["interrupt_id"],
                "decision": (
                    "Request a wide equipment-clearance photo with the access "
                    "panel open."
                ),
            },
        },
    )
    if not resumed.get("ok") or resumed["workflow"]["snapshot"]["status"] != "completed":
        raise AgentCoreInvocationError("resume operation did not complete")
    print(json.dumps({"resume": _summary(resumed)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
