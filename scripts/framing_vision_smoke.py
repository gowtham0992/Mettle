"""Paid, bounded synthetic evaluation; never submit real contractor information."""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
from uuid import uuid4

import boto3

from mettle.agentcore_client import invoke_json
from mettle.photo_upload import normalize_photo


NOTICE = """Contractor-supplied setup details
Permit: SYNTHETIC-FRAMING-EVAL
Property: Redacted test job
Inspection date: 2026-09-05
Reinspection deadline: 2026-09-12

Original report
SYNTHETIC REVIEW ONLY — NOT A REAL JOB
Inspection correction comments:
1. Install protective plates where the framing was bored near the stud edge. Provide a photograph showing each corrected location.
"""
CASES = (
    ("evidence/framing-plates-visible-v2.png", "accepted"),
    ("evidence/framing-closeup-insufficient.png", "not_accepted"),
    ("mettle-mark.png", "rejected"),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-id", required=True)
    parser.add_argument("--profile", default="mettle-agentcore")
    parser.add_argument("--repeat", type=int, choices=range(1, 6), default=3)
    parser.add_argument("--allow-model-spend", action="store_true")
    args = parser.parse_args()
    if not args.allow_model_spend:
        parser.error("Live intake and photo calls cost AWS credit; pass --allow-model-spend explicitly.")
    session = boto3.Session(profile_name=args.profile, region_name="us-east-1")
    runtime = session.client("bedrock-agentcore-control").get_agent_runtime(agentRuntimeId=args.runtime_id)
    if runtime["status"] != "READY":
        raise RuntimeError("Runtime must be READY.")
    # Refuse evaluation before any calls if live messaging is enabled.
    if runtime.get("environmentVariables", {}).get("METTLE_SMS_ENABLED") == "1":
        raise RuntimeError("Evaluation requires recorded-only delivery.")
    client = session.client("bedrock-agentcore")

    def call(payload, sid):
        result = invoke_json(client, runtime_arn=runtime["agentRuntimeArn"], session_id=sid, payload=payload)
        if result.get("ok") is not True:
            raise RuntimeError("Evaluation operation failed; no private payload logged.")
        return result

    sid = "mettle-eval-" + uuid4().hex
    started = call({"operation": "start", "idempotency_key": uuid4().hex, "payload": {
        "notice_text": NOTICE, "intake_provider": "bedrock", "as_of": "2026-09-06",
        "roster": [{"trade": trade, "name": "Synthetic Contractor", "phone": "+12025550146"}
                   for trade in ("framing", "general")],
    }}, sid)
    workflow = started["workflow"]
    citations = workflow["snapshot"]["notice"]["citations"]
    if len(citations) != 1 or not citations[0]["evidence_requirements"]:
        raise RuntimeError("Source correction was not preserved; do not invent fallback requirements.")
    reviewed = call({"operation": "review", "workflow_id": workflow["workflow_id"],
                     "idempotency_key": uuid4().hex, "payload": {
        "interrupt_id": workflow["snapshot"]["interrupts"][0]["interrupt_id"],
        "citations": [{"citation_id": citations[0]["citation_id"], "trade": "framing",
                       "closure_route": "photo_evidence", "evidence_requirements": citations[0]["evidence_requirements"]}],
    }}, sid)
    if any(d["status"] != "recorded" for d in reviewed["workflow"]["snapshot"]["deliveries"]):
        raise RuntimeError("Unexpected delivery provider; stop evaluation.")
    static = Path(__file__).resolve().parents[1] / "src/mettle/web/static"
    passed = 0
    for repetition in range(1, args.repeat + 1):
        for filename, expected in CASES:
            sid = "mettle-eval-" + uuid4().hex
            call({"operation": "restore", "workflow_id": workflow["workflow_id"],
                  "checkpoint": reviewed["checkpoint"]}, sid)
            result = call({"operation": "submit_photo_evidence", "workflow_id": workflow["workflow_id"],
                           "idempotency_key": uuid4().hex, "payload": {
                "citation_id": citations[0]["citation_id"],
                "image_base64": base64.b64encode(normalize_photo((static / filename).read_bytes())).decode("ascii"),
            }}, sid)
            assessment = result["workflow"]["evidence"][-1]
            ok = (assessment["status"] in {"manual_review", "rejected"}
                  if expected == "not_accepted" else assessment["status"] == expected)
            passed += int(ok)
            print(json.dumps({"case": filename, "repeat": repetition, "expected": expected,
                              "actual": assessment["status"], "passed": ok}), flush=True)
    total = args.repeat * len(CASES)
    print(json.dumps({"passed": passed, "total": total}), flush=True)
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
