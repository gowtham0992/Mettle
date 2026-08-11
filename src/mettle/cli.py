from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from mettle.campaign import build_campaign_plan
from mettle.notice_parser import NoticeParseError, parse_notice


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mettle",
        description="Build a deadline-aware recovery plan from a failed-inspection notice.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    ingest = subparsers.add_parser("ingest", help="ingest a synthetic notice")
    ingest.add_argument("notice", type=Path)
    ingest.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=date.today(),
        help="campaign date in YYYY-MM-DD format",
    )
    serve = subparsers.add_parser("serve", help="run the local demo dashboard")
    serve.add_argument("--port", type=int, default=4310)
    args = parser.parse_args(argv)

    if args.command == "serve":
        if not 1024 <= args.port <= 65535:
            parser.error("port must be between 1024 and 65535")
        import uvicorn

        uvicorn.run("mettle.web.app:app", host="127.0.0.1", port=args.port)
        return 0

    try:
        notice = parse_notice(args.notice.read_text(encoding="utf-8"))
        plan = build_campaign_plan(notice, as_of=args.as_of)
    except (OSError, NoticeParseError, ValueError) as exc:
        parser.error(str(exc))

    print(plan.model_dump_json(indent=2))
    return 0
