from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path

from mettle.agents.bedrock import (
    BedrockIntakeError,
    BedrockIntakeSettings,
    extract_notice_with_bedrock,
)
from mettle.campaign import build_campaign_plan
from mettle.notice_parser import NoticeParseError, parse_notice


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mettle",
        description="Build a deadline-aware recovery plan from a failed-inspection notice.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    ingest = subparsers.add_parser("ingest", help="ingest a failed-inspection notice")
    ingest.add_argument("notice", type=Path)
    ingest.add_argument(
        "--provider",
        choices=("local", "bedrock"),
        default="local",
        help="intake provider; Bedrock is opt-in and consumes AWS credits",
    )
    ingest.add_argument("--aws-region", default="us-east-1")
    ingest.add_argument(
        "--aws-profile",
        help="named AWS profile; recommended when multiple accounts are configured",
    )
    ingest.add_argument("--model-id", default="amazon.nova-micro-v1:0")
    ingest.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=date.today(),
        help="campaign date in YYYY-MM-DD format",
    )
    serve = subparsers.add_parser("serve", help="run the local demo dashboard")
    serve.add_argument("--port", type=int, default=4310)
    serve.add_argument(
        "--enable-bedrock",
        action="store_true",
        help="show the opt-in live Bedrock intake action; consumes AWS credits",
    )
    serve.add_argument("--aws-region", default="us-east-1")
    serve.add_argument(
        "--aws-profile",
        help="server-side named AWS profile used for enabled AWS execution",
    )
    serve.add_argument(
        "--enable-agentcore",
        action="store_true",
        help="enable deployed AgentCore execution; consumes AWS credits",
    )
    serve.add_argument(
        "--agentcore-runtime-arn",
        help="deployed Bedrock AgentCore runtime ARN (kept server-side)",
    )
    args = parser.parse_args(argv)

    if args.command == "serve":
        if not 1024 <= args.port <= 65535:
            parser.error("port must be between 1024 and 65535")
        if args.enable_bedrock:
            try:
                BedrockIntakeSettings(
                    region=args.aws_region,
                    profile=args.aws_profile,
                    model_id="amazon.nova-micro-v1:0",
                )
            except ValueError as exc:
                parser.error(str(exc))
            os.environ["METTLE_BEDROCK_ENABLED"] = "1"
            os.environ["METTLE_AWS_REGION"] = args.aws_region
            if args.aws_profile:
                os.environ["METTLE_AWS_PROFILE"] = args.aws_profile
        if args.enable_agentcore:
            if not args.agentcore_runtime_arn:
                parser.error(
                    "--agentcore-runtime-arn is required with --enable-agentcore"
                )
            if not args.agentcore_runtime_arn.startswith(
                "arn:aws:bedrock-agentcore:"
            ):
                parser.error("--agentcore-runtime-arn must be an AgentCore ARN")
            os.environ["METTLE_AGENTCORE_ENABLED"] = "1"
            os.environ["METTLE_AGENTCORE_RUNTIME_ARN"] = args.agentcore_runtime_arn
            os.environ["METTLE_AWS_REGION"] = args.aws_region
            if args.aws_profile:
                os.environ["METTLE_AWS_PROFILE"] = args.aws_profile
        import uvicorn

        uvicorn.run("mettle.web.app:app", host="127.0.0.1", port=args.port)
        return 0

    try:
        notice_text = args.notice.read_text(encoding="utf-8")
        if args.provider == "bedrock":
            notice = extract_notice_with_bedrock(
                notice_text,
                settings=BedrockIntakeSettings(
                    region=args.aws_region,
                    model_id=args.model_id,
                    profile=args.aws_profile,
                ),
            )
        else:
            notice = parse_notice(notice_text)
        plan = build_campaign_plan(notice, as_of=args.as_of)
    except (OSError, NoticeParseError, BedrockIntakeError, ValueError) as exc:
        parser.error(str(exc))

    print(plan.model_dump_json(indent=2))
    return 0
