from __future__ import annotations

import argparse
import base64
import json
import uuid
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import boto3
from pypdf import PdfReader

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
        description="Run Mettle's paid end-to-end AgentCore cloud smoke test."
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

    workflow_id = workflow["workflow_id"]
    current = resumed
    for citation_id, sample_id in (
        ("1", "panel_wide_measured"),
        ("2", "framing_plates_complete"),
        ("3", "mechanical_access_wide"),
    ):
        current = invoke_json(
            client,
            runtime_arn=args.runtime_arn,
            session_id=session_id,
            payload={
                "operation": "submit_evidence",
                "idempotency_key": f"evidence_{uuid.uuid4().hex}",
                "workflow_id": workflow_id,
                "payload": {"citation_id": citation_id, "sample_id": sample_id},
            },
        )
        if not current.get("ok") or current["workflow"]["evidence"][-1]["status"] != "accepted":
            raise AgentCoreInvocationError(
                f"evidence operation did not accept citation {citation_id}"
            )

    prepared = invoke_json(
        client,
        runtime_arn=args.runtime_arn,
        session_id=session_id,
        payload={
            "operation": "prepare_packet",
            "idempotency_key": f"prepare_{uuid.uuid4().hex}",
            "workflow_id": workflow_id,
            "payload": {},
        },
    )
    packet = prepared.get("workflow", {}).get("packet")
    if not prepared.get("ok") or not packet or packet["status"] != "awaiting_approval":
        raise AgentCoreInvocationError("packet preparation did not request approval")

    approved = invoke_json(
        client,
        runtime_arn=args.runtime_arn,
        session_id=session_id,
        payload={
            "operation": "approve_packet",
            "idempotency_key": f"approve_{uuid.uuid4().hex}",
            "workflow_id": workflow_id,
            "payload": {
                "approval_id": packet["approval_id"],
                "decision": "Approve packet for reinspection scheduling",
            },
        },
    )
    if not approved.get("ok") or approved["workflow"]["packet"]["status"] != "approved":
        raise AgentCoreInvocationError("packet approval did not complete")

    rendered = invoke_json(
        client,
        runtime_arn=args.runtime_arn,
        session_id=session_id,
        payload={"operation": "render_packet", "workflow_id": workflow_id},
    )
    try:
        pdf = base64.b64decode(rendered["body_base64"], validate=True)
    except (KeyError, ValueError) as exc:
        raise AgentCoreInvocationError("packet response was not valid base64") from exc
    if (
        not rendered.get("ok")
        or rendered.get("content_type") != "application/pdf"
        or sha256(pdf).hexdigest() != rendered.get("sha256")
        or len(PdfReader(BytesIO(pdf)).pages) != 4
    ):
        raise AgentCoreInvocationError("packet response failed integrity checks")
    print(
        json.dumps(
            {
                "complete": {
                    "workflow_id": workflow_id,
                    "evidence_accepted": len(approved["workflow"]["evidence"]),
                    "packet_status": approved["workflow"]["packet"]["status"],
                    "packet_pages": 4,
                    "packet_bytes": len(pdf),
                    "packet_sha256": rendered["sha256"],
                }
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
