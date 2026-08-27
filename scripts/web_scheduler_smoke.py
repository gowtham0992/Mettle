from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path
from typing import Any

import boto3


EXPECTED_FUNCTION = "mettle-web"
NOTICE = Path("examples/notices/failed-rough-in.txt")


def api_event(
    *,
    method: str,
    path: str,
    subject: str,
    account_id: str,
    body: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    headers = {
        "content-type": "application/json",
        "host": "d1ytth8asjpes8.cloudfront.net",
        "x-forwarded-proto": "https",
    }
    if idempotency_key is not None:
        headers["idempotency-key"] = idempotency_key
    return {
        "version": "2.0",
        "routeKey": "ANY /api/agentcore/{proxy+}",
        "rawPath": path,
        "rawQueryString": "",
        "headers": headers,
        "requestContext": {
            "accountId": account_id,
            "apiId": "scheduler-smoke",
            "authorizer": {
                "jwt": {
                    "claims": {"sub": subject},
                    "scopes": [],
                }
            },
            "domainName": "d1ytth8asjpes8.cloudfront.net",
            "domainPrefix": "d1ytth8asjpes8",
            "http": {
                "method": method,
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "mettle-scheduler-smoke",
            },
            "requestId": uuid.uuid4().hex,
            "routeKey": "ANY /api/agentcore/{proxy+}",
            "stage": "$default",
            "time": "20/Aug/2026:00:00:00 +0000",
            "timeEpoch": int(time.time() * 1000),
        },
        "body": json.dumps(body, separators=(",", ":")) if body is not None else None,
        "isBase64Encoded": False,
    }


def invoke_api(client: Any, *, function_name: str, event: dict[str, Any]) -> dict[str, Any]:
    response = client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(event, separators=(",", ":")).encode("utf-8"),
    )
    payload = json.loads(response["Payload"].read())
    if response.get("FunctionError"):
        raise RuntimeError("web Lambda returned a function error")
    status = payload.get("statusCode")
    body = json.loads(payload.get("body") or "{}")
    if not isinstance(status, int) or not 200 <= status < 300:
        raise RuntimeError(f"web API returned HTTP {status}: {body}")
    return body


def review_payload(workflow: dict[str, Any]) -> dict[str, Any]:
    interrupt = workflow["snapshot"]["interrupts"][0]
    return {
        "interrupt_id": interrupt["interrupt_id"],
        "citations": [
            {
                "citation_id": citation["citation_id"],
                "trade": (
                    citation["trade"]
                    if citation["trade"] != "unknown"
                    else "general"
                ),
                "closure_route": citation.get("closure_route", "photo_evidence"),
                "evidence_requirements": citation["evidence_requirements"]
                or ["Wide photo showing the completed correction and its location"],
            }
            for citation in workflow["snapshot"]["notice"]["citations"]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prove the deployed web gateway schedules and executes one checkpoint."
    )
    parser.add_argument("--profile", default="mettle")
    parser.add_argument("--region", default="us-east-1", choices=("us-east-1",))
    parser.add_argument("--function-name", default=EXPECTED_FUNCTION)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()
    if args.function_name != EXPECTED_FUNCTION:
        parser.error(f"function name must be {EXPECTED_FUNCTION}")

    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    account = session.client("sts").get_caller_identity()["Account"]

    lambda_client = session.client("lambda")
    scheduler = session.client("scheduler")
    subject = f"scheduler-smoke-{uuid.uuid4().hex}"
    create_key = f"smoke_create_{uuid.uuid4().hex}"
    review_key = f"smoke_review_{uuid.uuid4().hex}"
    workflow_id: str | None = None
    active_schedule: str | None = None

    try:
        created = invoke_api(
            lambda_client,
            function_name=args.function_name,
            event=api_event(
                method="POST",
                path="/api/agentcore/workflows",
                subject=subject,
                account_id=account,
                idempotency_key=create_key,
                body={
                    "notice_text": NOTICE.read_text(encoding="utf-8"),
                    "intake_provider": "bedrock",
                    "as_of": "2026-08-10",
                    "roster": [
                        {"trade": "electrical", "name": "Demo Electrician", "phone": "+13035550101"},
                        {"trade": "framing", "name": "Demo Framer", "phone": "+13035550102"},
                        {"trade": "mechanical", "name": "Demo Mechanical", "phone": "+13035550103"},
                        {"trade": "general", "name": "Demo GC", "phone": "+13035550104"},
                    ],
                },
            ),
        )
        workflow_id = created["workflow_id"]
        reviewed = invoke_api(
            lambda_client,
            function_name=args.function_name,
            event=api_event(
                method="POST",
                path=f"/api/agentcore/workflows/{workflow_id}/review",
                subject=subject,
                account_id=account,
                idempotency_key=review_key,
                body=review_payload(created),
            ),
        )
        first = reviewed.get("automation") or {}
        if first.get("status") != "scheduled" or first.get("schedule_version") != 1:
            raise RuntimeError(f"review did not arm schedule version 1: {first}")
        active_schedule = first["schedule_name"]
        scheduler.get_schedule(Name=active_schedule, GroupName="mettle-recovery")
        print(
            json.dumps(
                {
                    "workflow_reference": workflow_id[:12],
                    "armed": first,
                },
                indent=2,
            )
        )

        deadline = time.monotonic() + args.timeout_seconds
        while time.monotonic() < deadline:
            time.sleep(15)
            current = invoke_api(
                lambda_client,
                function_name=args.function_name,
                event=api_event(
                    method="GET",
                    path=f"/api/agentcore/workflows/{workflow_id}",
                    subject=subject,
                    account_id=account,
                ),
            )
            automation = current.get("automation") or {}
            if automation.get("schedule_version", 0) >= 2:
                active_schedule = automation.get("schedule_name")
                print(
                    json.dumps(
                        {
                            "executed": True,
                            "automation": automation,
                            "deliveries": len(current["snapshot"].get("deliveries", [])),
                            "workflow_status": current["snapshot"]["status"],
                        },
                        indent=2,
                    )
                )
                return 0
        raise TimeoutError("scheduled checkpoint did not advance before the timeout")
    finally:
        if active_schedule:
            try:
                scheduler.delete_schedule(
                    Name=active_schedule,
                    GroupName="mettle-recovery",
                )
                print(json.dumps({"cleanup": "cancelled follow-on smoke schedule"}))
            except scheduler.exceptions.ResourceNotFoundException:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
