from __future__ import annotations

import json
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from hashlib import sha256
from typing import Any, Callable, Protocol
from zoneinfo import ZoneInfo

from botocore.exceptions import ClientError
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AutomationStatus(StrEnum):
    AWAITING_DECISION = "awaiting_decision"
    SCHEDULED = "scheduled"
    COMPLETE = "complete"


class CampaignAutomation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: AutomationStatus
    schedule_version: int = Field(ge=0)
    schedule_name: str | None = Field(
        default=None,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    next_check_at: datetime | None = None
    logical_check_on: date | None = None
    accelerated_demo_clock: bool = False

    @model_validator(mode="after")
    def validate_scheduled_state(self) -> CampaignAutomation:
        if self.status is AutomationStatus.SCHEDULED and (
            self.schedule_version < 1
            or self.schedule_name is None
            or self.next_check_at is None
            or self.logical_check_on is None
        ):
            raise ValueError("scheduled automation requires a complete checkpoint")
        return self


class ScheduledCheckEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    owner_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    workflow_id: str = Field(min_length=1, max_length=64)
    schedule_name: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    schedule_version: int = Field(ge=1)
    logical_check_on: date

    @property
    def idempotency_key(self) -> str:
        workflow_digest = sha256(self.workflow_id.encode("utf-8")).hexdigest()[:12]
        return (
            f"scheduled_{self.schedule_version}_{self.logical_check_on:%Y%m%d}_"
            f"{workflow_digest}"
        )


class CampaignScheduler(Protocol):
    def schedule(
        self,
        *,
        owner_hash: str,
        workflow_id: str,
        logical_check_on: date,
        schedule_version: int,
        previous: CampaignAutomation | None,
    ) -> CampaignAutomation: ...

    def cancel(self, automation: CampaignAutomation | None) -> None: ...


class EventBridgeSchedulerClient(Protocol):
    def create_schedule(self, **kwargs: Any) -> dict[str, Any]: ...

    def update_schedule(self, **kwargs: Any) -> dict[str, Any]: ...

    def delete_schedule(self, **kwargs: Any) -> dict[str, Any]: ...


def _resource_not_found(exc: ClientError) -> bool:
    return exc.response.get("Error", {}).get("Code") == "ResourceNotFoundException"


class EventBridgeCampaignScheduler:
    """Creates exact, one-time recovery checkpoints with no PII in their names."""

    def __init__(
        self,
        *,
        client: EventBridgeSchedulerClient,
        target_arn: str,
        execution_role_arn: str,
        schedule_group: str,
        dlq_arn: str,
        timezone_name: str = "America/Denver",
        demo_delay_seconds: int | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not target_arn.startswith("arn:aws:lambda:"):
            raise ValueError("scheduler target must be a Lambda ARN")
        if not execution_role_arn.startswith("arn:aws:iam::"):
            raise ValueError("scheduler execution role must be an IAM ARN")
        if not dlq_arn.startswith("arn:aws:sqs:"):
            raise ValueError("scheduler DLQ must be an SQS ARN")
        if demo_delay_seconds is not None and not 60 <= demo_delay_seconds <= 3600:
            raise ValueError("demo scheduler delay must be between 60 and 3600 seconds")
        self._client = client
        self._target_arn = target_arn
        self._execution_role_arn = execution_role_arn
        self._schedule_group = schedule_group
        self._dlq_arn = dlq_arn
        self._timezone = ZoneInfo(timezone_name)
        self._demo_delay_seconds = demo_delay_seconds
        self._clock = clock or (lambda: datetime.now(UTC))

    def schedule(
        self,
        *,
        owner_hash: str,
        workflow_id: str,
        logical_check_on: date,
        schedule_version: int,
        previous: CampaignAutomation | None,
    ) -> CampaignAutomation:
        if previous is not None and previous.schedule_name:
            self.cancel(previous)

        workflow_digest = sha256(
            f"{owner_hash}\0{workflow_id}".encode("utf-8")
        ).hexdigest()[:24]
        schedule_name = f"mettle-{workflow_digest}-v{schedule_version}"
        event = ScheduledCheckEvent(
            owner_hash=owner_hash,
            workflow_id=workflow_id,
            schedule_name=schedule_name,
            schedule_version=schedule_version,
            logical_check_on=logical_check_on,
        )
        execution_at = self._execution_at(logical_check_on)
        request = {
            "Name": schedule_name,
            "GroupName": self._schedule_group,
            "Description": "Mettle autonomous failed-inspection recovery checkpoint",
            "ScheduleExpression": f"at({execution_at:%Y-%m-%dT%H:%M:%S})",
            "ScheduleExpressionTimezone": "UTC",
            "FlexibleTimeWindow": {"Mode": "OFF"},
            "ActionAfterCompletion": "DELETE",
            "State": "ENABLED",
            "Target": {
                "Arn": self._target_arn,
                "RoleArn": self._execution_role_arn,
                "Input": json.dumps(event.model_dump(mode="json"), separators=(",", ":")),
                "DeadLetterConfig": {"Arn": self._dlq_arn},
                "RetryPolicy": {
                    "MaximumEventAgeInSeconds": 3600,
                    "MaximumRetryAttempts": 2,
                },
            },
        }
        try:
            self._client.update_schedule(**request)
        except ClientError as exc:
            if not _resource_not_found(exc):
                raise
            self._client.create_schedule(**request)
        return CampaignAutomation(
            status=AutomationStatus.SCHEDULED,
            schedule_version=schedule_version,
            schedule_name=schedule_name,
            next_check_at=execution_at,
            logical_check_on=logical_check_on,
            accelerated_demo_clock=self._demo_delay_seconds is not None,
        )

    def cancel(self, automation: CampaignAutomation | None) -> None:
        if automation is None or not automation.schedule_name:
            return
        try:
            self._client.delete_schedule(
                Name=automation.schedule_name,
                GroupName=self._schedule_group,
            )
        except ClientError as exc:
            if not _resource_not_found(exc):
                raise

    def _execution_at(self, logical_check_on: date) -> datetime:
        if self._demo_delay_seconds is not None:
            return (
                self._clock().astimezone(UTC)
                + timedelta(seconds=self._demo_delay_seconds)
            ).replace(microsecond=0)
        local = datetime.combine(logical_check_on, time(hour=8), self._timezone)
        return local.astimezone(UTC).replace(microsecond=0)
