from __future__ import annotations

import logging
import os
from hashlib import sha256
from typing import Any

import boto3
from pydantic import ValidationError

from mettle.automation import EventBridgeCampaignScheduler, ScheduledCheckEvent
from mettle.durable_agentcore_gateway import DurableAgentCoreWorkflowGateway


LOGGER = logging.getLogger(__name__)


def configured_gateway() -> DurableAgentCoreWorkflowGateway:
    region = os.getenv("METTLE_AWS_REGION", "us-east-1")
    runtime_arn = os.environ["METTLE_AGENTCORE_RUNTIME_ARN"]
    table_name = os.environ["METTLE_DYNAMODB_TABLE"]
    packet_bucket_name = os.environ["METTLE_PACKET_BUCKET"]
    target_arn = os.environ["METTLE_SCHEDULER_TARGET_ARN"]
    execution_role_arn = os.environ["METTLE_SCHEDULER_ROLE_ARN"]
    schedule_group = os.environ["METTLE_SCHEDULER_GROUP"]
    dlq_arn = os.environ["METTLE_SCHEDULER_DLQ_ARN"]
    delay = os.getenv("METTLE_SCHEDULER_DEMO_DELAY_SECONDS")
    session = boto3.Session(region_name=region)
    return DurableAgentCoreWorkflowGateway(
        client=session.client("bedrock-agentcore"),
        runtime_arn=runtime_arn,
        table=session.resource("dynamodb").Table(table_name),
        packet_bucket=session.resource("s3").Bucket(packet_bucket_name),
        campaign_scheduler=EventBridgeCampaignScheduler(
            client=session.client("scheduler"),
            target_arn=target_arn,
            execution_role_arn=execution_role_arn,
            schedule_group=schedule_group,
            dlq_arn=dlq_arn,
            timezone_name=os.getenv(
                "METTLE_SCHEDULER_TIMEZONE", "America/Denver"
            ),
            demo_delay_seconds=int(delay) if delay else None,
        ),
    )


def handle_scheduled_check(event: object, _context: Any) -> dict[str, Any]:
    try:
        scheduled = ScheduledCheckEvent.model_validate(event)
    except ValidationError as exc:
        raise ValueError("scheduled checkpoint payload is invalid") from exc
    envelope, executed = configured_gateway().run_scheduled_check(scheduled)
    workflow_reference = sha256(envelope.workflow_id.encode("utf-8")).hexdigest()[:12]
    LOGGER.info(
        "scheduled_check_completed workflow=%s version=%s executed=%s status=%s",
        workflow_reference,
        scheduled.schedule_version,
        executed,
        envelope.snapshot.status,
    )
    return {
        "ok": True,
        "executed": executed,
        "workflow_reference": workflow_reference,
        "automation_status": (
            envelope.automation.status if envelope.automation is not None else None
        ),
    }
