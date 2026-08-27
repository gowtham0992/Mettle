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
from mettle.photo_upload import normalize_photo


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
    parser.add_argument(
        "--vision",
        action="store_true",
        help="assess citation 1 through live Nova Lite instead of the fixture adapter",
    )
    parser.add_argument(
        "--chase",
        action="store_true",
        help="exercise T-3 follow-up, replay safety, and the T-2 deadline interrupt",
    )
    args = parser.parse_args()
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    account_id = session.client("sts").get_caller_identity()["Account"]
    expected_arn_prefix = (
        f"arn:aws:bedrock-agentcore:{args.region}:{account_id}:runtime/"
    )
    if not args.runtime_arn.startswith(expected_arn_prefix):
        parser.error(
            "runtime ARN must belong to the selected AWS profile and approved region"
        )

    notice = Path("examples/notices/failed-rough-in.txt").read_text(encoding="utf-8")
    session_id = f"mettle-smoke-{uuid.uuid4()}"
    client = session.client("bedrock-agentcore")

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
                    {
                        "trade": "plumbing",
                        "name": "Gowtham (GC fallback)",
                        "phone": "+13035550104",
                    },
                    {
                        "trade": "general",
                        "name": "Gowtham (GC fallback)",
                        "phone": "+13035550105",
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

    reviewed = invoke_json(
        client,
        runtime_arn=args.runtime_arn,
        session_id=session_id,
        payload={
            "operation": "review",
            "idempotency_key": f"review_{uuid.uuid4().hex}",
            "workflow_id": workflow["workflow_id"],
            "payload": {
                "interrupt_id": interrupts[0]["interrupt_id"],
                "citations": [
                    {
                        "citation_id": citation["citation_id"],
                        "trade": (
                            citation["trade"]
                            if citation["trade"] != "unknown"
                            else "general"
                        ),
                        "closure_route": citation.get(
                            "closure_route", "photo_evidence"
                        ),
                        "evidence_requirements": (
                            citation["evidence_requirements"]
                            or [
                                "Wide photo showing the completed correction "
                                "and its location"
                            ]
                        ),
                    }
                    for citation in workflow["snapshot"]["notice"]["citations"]
                ],
            },
        },
    )
    if not reviewed.get("ok") or reviewed["workflow"]["snapshot"]["status"] != "completed":
        raise AgentCoreInvocationError(
            "contractor review did not complete: "
            + json.dumps(reviewed, sort_keys=True)
        )
    print(json.dumps({"review": _summary(reviewed)}, indent=2))

    workflow_id = workflow["workflow_id"]
    current = reviewed
    citation_one_closed = False
    if args.vision:
        photo = normalize_photo(
            Path("src/mettle/web/static/evidence/panel-wide-measured.png").read_bytes()
        )
        current = invoke_json(
            client,
            runtime_arn=args.runtime_arn,
            session_id=session_id,
            payload={
                "operation": "submit_photo_evidence",
                "idempotency_key": f"photo_{uuid.uuid4().hex}",
                "workflow_id": workflow_id,
                "payload": {
                    "citation_id": "1",
                    "image_base64": base64.b64encode(photo).decode("ascii"),
                },
            },
        )
        assessment = current.get("workflow", {}).get("evidence", [{}])[-1]
        if not current.get("ok") or assessment.get("status") != "accepted":
            safe_error = current.get("error", {})
            raise AgentCoreInvocationError(
                "vision evidence was not accepted "
                f"({assessment.get('status', 'missing')}; "
                f"{safe_error.get('code', 'no_error_code')}: "
                f"{safe_error.get('message', 'no safe error message')})"
            )
        print(
            json.dumps(
                {
                    "vision": {
                        "citation_id": assessment["citation_id"],
                        "status": assessment["status"],
                        "requirements_matched": len(assessment["matched_requirements"]),
                    }
                },
                indent=2,
            )
        )
        citation_one_closed = True

    if args.chase and not citation_one_closed:
        current = invoke_json(
            client,
            runtime_arn=args.runtime_arn,
            session_id=session_id,
            payload={
                "operation": "submit_evidence",
                "idempotency_key": f"evidence_{uuid.uuid4().hex}",
                "workflow_id": workflow_id,
                "payload": {
                    "citation_id": "1",
                    "sample_id": "panel_wide_measured",
                },
            },
        )
        if not current.get("ok") or current["workflow"]["evidence"][-1]["status"] != "accepted":
            raise AgentCoreInvocationError("pre-chase evidence did not accept citation 1")
        citation_one_closed = True

    if args.chase:
        check_key = f"check_{uuid.uuid4().hex}"
        check_payload = {
            "operation": "run_next_check",
            "idempotency_key": check_key,
            "workflow_id": workflow_id,
            "payload": {},
        }
        first_check = invoke_json(
            client,
            runtime_arn=args.runtime_arn,
            session_id=session_id,
            payload=check_payload,
        )
        replayed_check = invoke_json(
            client,
            runtime_arn=args.runtime_arn,
            session_id=session_id,
            payload=check_payload,
        )
        first_snapshot = first_check.get("workflow", {}).get("snapshot", {})
        if (
            not first_check.get("ok")
            or first_snapshot.get("status") != "completed"
            or first_snapshot.get("plan", {}).get("as_of") != "2026-08-14"
            or [
                action.get("citation_id")
                for action in first_snapshot.get("plan", {}).get("actions", [])
            ]
            != ["2", "3"]
            or len(first_snapshot.get("deliveries", [])) != 5
            or replayed_check.get("workflow") != first_check.get("workflow")
        ):
            raise AgentCoreInvocationError("T-3 chase or replay verification failed")

        critical = invoke_json(
            client,
            runtime_arn=args.runtime_arn,
            session_id=session_id,
            payload={
                "operation": "run_next_check",
                "idempotency_key": f"check_{uuid.uuid4().hex}",
                "workflow_id": workflow_id,
                "payload": {},
            },
        )
        critical_snapshot = critical.get("workflow", {}).get("snapshot", {})
        deadline_interrupts = critical_snapshot.get("interrupts", [])
        if (
            not critical.get("ok")
            or critical_snapshot.get("status") != "interrupted"
            or critical_snapshot.get("plan", {}).get("as_of") != "2026-08-15"
            or len(deadline_interrupts) != 1
            or deadline_interrupts[0].get("name") != "deadline-tradeoff"
            or len(critical_snapshot.get("deliveries", [])) != 7
        ):
            raise AgentCoreInvocationError("T-2 deadline interrupt verification failed")

        deadline_resumed = invoke_json(
            client,
            runtime_arn=args.runtime_arn,
            session_id=session_id,
            payload={
                "operation": "resume",
                "idempotency_key": f"resume_{uuid.uuid4().hex}",
                "workflow_id": workflow_id,
                "payload": {
                    "interrupt_id": deadline_interrupts[0]["interrupt_id"],
                    "decision": (
                        "Keep the current reinspection date and continue critical "
                        "follow-ups."
                    ),
                },
            },
        )
        deadline_snapshot = deadline_resumed.get("workflow", {}).get("snapshot", {})
        if (
            not deadline_resumed.get("ok")
            or deadline_snapshot.get("status") != "completed"
            or not deadline_snapshot.get("deadline_decision")
            or len(deadline_snapshot.get("deliveries", [])) != 7
        ):
            raise AgentCoreInvocationError("deadline decision did not resume safely")
        current = deadline_resumed
        print(
            json.dumps(
                {
                    "chase": {
                        "t_minus_3_open_citations": ["2", "3"],
                        "t_minus_3_deliveries": 5,
                        "replay_safe": True,
                        "t_minus_2_interrupt": "deadline-tradeoff",
                        "t_minus_2_deliveries": 7,
                    }
                },
                indent=2,
            )
        )

    fixture_evidence = (
        (("2", "framing_plates_complete"), ("3", "mechanical_access_wide"))
        if citation_one_closed
        else (
            ("1", "panel_wide_measured"),
            ("2", "framing_plates_complete"),
            ("3", "mechanical_access_wide"),
        )
    )
    for citation_id, sample_id in fixture_evidence:
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
    reader = PdfReader(BytesIO(pdf))
    # The communication record is intentionally a first-class final page,
    # even when the smoke run does not add deadline-chase deliveries.
    expected_pages = 5
    packet_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if (
        not rendered.get("ok")
        or rendered.get("content_type") != "application/pdf"
        or sha256(pdf).hexdigest() != rendered.get("sha256")
        or len(reader.pages) != expected_pages
        or "Recovery communication record" not in packet_text
    ):
        raise AgentCoreInvocationError("packet response failed integrity checks")
    print(
        json.dumps(
            {
                "complete": {
                    "workflow_id": workflow_id,
                    "evidence_accepted": len(approved["workflow"]["evidence"]),
                    "packet_status": approved["workflow"]["packet"]["status"],
                    "packet_pages": len(reader.pages),
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
