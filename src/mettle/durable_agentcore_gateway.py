from __future__ import annotations

import base64
import binascii
import logging
import time
from hashlib import sha256
from typing import Any
from uuid import uuid4

from botocore.exceptions import ClientError
from pydantic import BaseModel, ValidationError

from mettle.agentcore_client import AgentCoreDataClient, invoke_json
from mettle.agentcore_gateway import AgentCoreGatewayError, _fingerprint
from mettle.agents.bedrock import BedrockIntakeError
from mettle.automation import (
    AutomationStatus,
    CampaignAutomation,
    CampaignScheduler,
    ScheduledCheckEvent,
)
from mettle.campaign import next_campaign_check
from mettle.request_identity import require_principal
from mettle.workflow import WorkflowConfigurationError, WorkflowStatus
from mettle.workflow_registry import (
    AgentCorePhotoEvidenceRequest,
    ApprovePacketRequest,
    EvidenceSubmissionError,
    PacketNotApproved,
    PacketNotReady,
    PreparePacketRequest,
    ReviewEvidenceRequest,
    ReviewWorkflowRequest,
    ResumeWorkflowRequest,
    RunNextCheckRequest,
    SubmitEvidenceRequest,
    SubmitPhotoEvidenceRequest,
    WorkflowConflict,
    WorkflowEnvelope,
    WorkflowNotFound,
    CreateWorkflowRequest,
)


SESSION_TTL_SECONDS = 8 * 60 * 60
LOCK_SECONDS = 45
MAX_PACKET_BYTES = 25_000_000
LOGGER = logging.getLogger(__name__)


def _is_conditional_failure(exc: ClientError) -> bool:
    return exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"


class DurableAgentCoreWorkflowGateway:
    """User-scoped AgentCore session owner backed by DynamoDB and private S3.

    Runtime session identifiers never cross the HTTP boundary. DynamoDB records
    bind each public workflow identifier and idempotency attempt to the SHA-256
    digest of the verified Cognito subject.
    """

    def __init__(
        self,
        *,
        client: AgentCoreDataClient,
        runtime_arn: str,
        table: Any,
        packet_bucket: Any,
        campaign_scheduler: CampaignScheduler | None = None,
        clock: Any = time.time,
    ) -> None:
        if not runtime_arn.startswith("arn:aws:bedrock-agentcore:"):
            raise ValueError("runtime_arn must be an Amazon Bedrock AgentCore ARN")
        self._client = client
        self._runtime_arn = runtime_arn
        self._table = table
        self._packet_bucket = packet_bucket
        self._campaign_scheduler = campaign_scheduler
        self._clock = clock

    def _owner(self) -> str:
        return sha256(require_principal().encode("utf-8")).hexdigest()

    def _expires_at(self) -> int:
        return int(self._clock()) + SESSION_TTL_SECONDS

    def _workflow_key(self, owner: str, workflow_id: str) -> str:
        return f"u#{owner}#w#{workflow_id}"

    def _attempt_key(self, owner: str, kind: str, idempotency_key: str) -> str:
        return f"u#{owner}#{kind}#{idempotency_key}"

    def create(
        self,
        payload: CreateWorkflowRequest,
        *,
        idempotency_key: str,
    ) -> tuple[WorkflowEnvelope, bool]:
        owner = self._owner()
        fingerprint = _fingerprint(payload)
        attempt_key = self._attempt_key(owner, "create", idempotency_key)
        session_id = f"mettle-{uuid4().hex}"
        created = True
        try:
            self._table.put_item(
                Item={
                    "pk": attempt_key,
                    "kind": "create_attempt",
                    "fingerprint": fingerprint,
                    "session_id": session_id,
                    "status": "pending",
                    "expires_at": self._expires_at(),
                },
                ConditionExpression="attribute_not_exists(pk)",
            )
        except ClientError as exc:
            if not _is_conditional_failure(exc):
                raise
            created = False
            attempt = self._get(attempt_key)
            if attempt.get("fingerprint") != fingerprint:
                raise WorkflowConflict(
                    "idempotency key was already used with a different workflow request"
                ) from exc
            session_id = attempt["session_id"]
            if attempt.get("status") == "completed":
                return self._envelope(attempt.get("envelope")), True

        result = self._invoke(
            session_id=session_id,
            payload={
                "operation": "start",
                "idempotency_key": idempotency_key,
                "payload": payload.model_dump(mode="json"),
            },
        )
        envelope = self._parse_result(result)
        workflow_key = self._workflow_key(owner, envelope.workflow_id)
        try:
            self._table.put_item(
                Item={
                    "pk": workflow_key,
                    "kind": "workflow",
                    "session_id": session_id,
                    "workflow_id": envelope.workflow_id,
                    "envelope": envelope.model_dump(mode="json"),
                    "expires_at": self._expires_at(),
                },
                ConditionExpression=(
                    "attribute_not_exists(pk) OR session_id = :session_id"
                ),
                ExpressionAttributeValues={":session_id": session_id},
            )
        except ClientError as exc:
            if _is_conditional_failure(exc):
                raise AgentCoreGatewayError(
                    "AgentCore returned a workflow identifier owned by another session"
                ) from exc
            raise
        self._table.update_item(
            Key={"pk": attempt_key},
            UpdateExpression=(
                "SET #status = :completed, envelope = :envelope, "
                "workflow_id = :workflow_id, expires_at = :expires_at"
            ),
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":completed": "completed",
                ":envelope": envelope.model_dump(mode="json"),
                ":workflow_id": envelope.workflow_id,
                ":expires_at": self._expires_at(),
            },
        )
        return envelope.model_copy(deep=True), (not created) or bool(result.get("replayed"))

    def get(self, workflow_id: str) -> WorkflowEnvelope:
        owner = self._owner()
        return self._envelope(self._workflow(owner, workflow_id).get("envelope"))

    def run_scheduled_check(
        self,
        event: ScheduledCheckEvent,
    ) -> tuple[WorkflowEnvelope, bool]:
        """Run a trusted EventBridge checkpoint without a browser principal."""
        workflow = self._workflow(event.owner_hash, event.workflow_id)
        current = self._envelope(workflow.get("envelope"))
        automation = current.automation
        if (
            automation is None
            or automation.status is not AutomationStatus.SCHEDULED
            or automation.schedule_version != event.schedule_version
            or automation.schedule_name != event.schedule_name
            or automation.logical_check_on != event.logical_check_on
        ):
            return current, False
        envelope = self._mutate_owned(
            event.owner_hash,
            event.workflow_id,
            "run_next_check",
            RunNextCheckRequest(),
            event.idempotency_key,
        )
        return envelope, True

    def resume(self, workflow_id: str, payload: ResumeWorkflowRequest, *, idempotency_key: str) -> WorkflowEnvelope:
        return self._mutate(workflow_id, "resume", payload, idempotency_key)

    def review(self, workflow_id: str, payload: ReviewWorkflowRequest, *, idempotency_key: str) -> WorkflowEnvelope:
        return self._mutate(workflow_id, "review", payload, idempotency_key)

    def submit_evidence(self, workflow_id: str, payload: SubmitEvidenceRequest, *, idempotency_key: str) -> WorkflowEnvelope:
        return self._mutate(workflow_id, "submit_evidence", payload, idempotency_key)

    def submit_photo_evidence(
        self,
        workflow_id: str,
        payload: SubmitPhotoEvidenceRequest,
        *,
        image: bytes,
        idempotency_key: str,
    ) -> WorkflowEnvelope:
        cloud_payload = AgentCorePhotoEvidenceRequest(
            citation_id=payload.citation_id,
            image_base64=base64.b64encode(image).decode("ascii"),
        )
        return self._mutate(workflow_id, "submit_photo_evidence", cloud_payload, idempotency_key)

    def review_evidence(self, workflow_id: str, payload: ReviewEvidenceRequest, *, idempotency_key: str) -> WorkflowEnvelope:
        return self._mutate(workflow_id, "review_evidence", payload, idempotency_key)

    def prepare_packet(self, workflow_id: str, payload: PreparePacketRequest, *, idempotency_key: str) -> WorkflowEnvelope:
        return self._mutate(workflow_id, "prepare_packet", payload, idempotency_key)

    def run_next_check(self, workflow_id: str, payload: RunNextCheckRequest, *, idempotency_key: str) -> WorkflowEnvelope:
        return self._mutate(workflow_id, "run_next_check", payload, idempotency_key)

    def approve_packet(self, workflow_id: str, payload: ApprovePacketRequest, *, idempotency_key: str) -> WorkflowEnvelope:
        return self._mutate(workflow_id, "approve_packet", payload, idempotency_key)

    def _mutate(
        self,
        workflow_id: str,
        operation: str,
        payload: BaseModel,
        idempotency_key: str,
    ) -> WorkflowEnvelope:
        owner = self._owner()
        return self._mutate_owned(
            owner,
            workflow_id,
            operation,
            payload,
            idempotency_key,
        )

    def _mutate_owned(
        self,
        owner: str,
        workflow_id: str,
        operation: str,
        payload: BaseModel,
        idempotency_key: str,
    ) -> WorkflowEnvelope:
        workflow = self._workflow(owner, workflow_id)
        fingerprint = _fingerprint(payload)
        attempt_key = self._attempt_key(
            owner, f"w#{workflow_id}#m#{operation}", idempotency_key
        )
        try:
            self._table.put_item(
                Item={
                    "pk": attempt_key,
                    "kind": "mutation_attempt",
                    "fingerprint": fingerprint,
                    "status": "pending",
                    "expires_at": self._expires_at(),
                },
                ConditionExpression="attribute_not_exists(pk)",
            )
        except ClientError as exc:
            if not _is_conditional_failure(exc):
                raise
            attempt = self._get(attempt_key)
            if attempt.get("fingerprint") != fingerprint:
                raise WorkflowConflict(
                    f"idempotency key was already used with a different {operation} request"
                ) from exc
            if attempt.get("status") == "completed":
                return self._envelope(attempt.get("envelope"))

        workflow_key = self._workflow_key(owner, workflow_id)
        lock_token = uuid4().hex
        now = int(self._clock())
        try:
            self._table.update_item(
                Key={"pk": workflow_key},
                UpdateExpression="SET lock_token = :token, lock_until = :until",
                ConditionExpression=(
                    "attribute_exists(pk) AND "
                    "(attribute_not_exists(lock_token) OR lock_until < :now)"
                ),
                ExpressionAttributeValues={
                    ":token": lock_token,
                    ":until": now + LOCK_SECONDS,
                    ":now": now,
                },
            )
        except ClientError as exc:
            if _is_conditional_failure(exc):
                raise WorkflowConflict(
                    "another workflow operation is still in progress; retry shortly"
                ) from exc
            raise

        try:
            # The workflow may have advanced between the initial read and lock
            # acquisition. Re-read under our lock so schedule versions and the
            # AgentCore session always come from the latest committed envelope.
            workflow = self._get(workflow_key)
            result = self._invoke(
                session_id=workflow["session_id"],
                payload={
                    "operation": operation,
                    "idempotency_key": idempotency_key,
                    "workflow_id": workflow_id,
                    "payload": payload.model_dump(mode="json"),
                },
            )
            envelope = self._parse_result(result)
            if envelope.workflow_id != workflow_id:
                raise AgentCoreGatewayError(
                    "AgentCore returned a different workflow identifier"
                )
            previous_envelope = self._envelope(workflow.get("envelope"))
            envelope = self._reconcile_automation(
                owner=owner,
                operation=operation,
                envelope=envelope,
                previous=previous_envelope.automation,
            )
            self._table.update_item(
                Key={"pk": workflow_key},
                UpdateExpression=(
                    "SET envelope = :envelope, expires_at = :expires_at "
                    "REMOVE lock_token, lock_until, packet_key"
                ),
                ConditionExpression="lock_token = :token",
                ExpressionAttributeValues={
                    ":envelope": envelope.model_dump(mode="json"),
                    ":expires_at": self._expires_at(),
                    ":token": lock_token,
                },
            )
            self._table.update_item(
                Key={"pk": attempt_key},
                UpdateExpression=(
                    "SET #status = :completed, envelope = :envelope, "
                    "expires_at = :expires_at"
                ),
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":completed": "completed",
                    ":envelope": envelope.model_dump(mode="json"),
                    ":expires_at": self._expires_at(),
                },
            )
            return envelope.model_copy(deep=True)
        except Exception:
            self._release_lock(workflow_key, lock_token)
            raise

    def _reconcile_automation(
        self,
        *,
        owner: str,
        operation: str,
        envelope: WorkflowEnvelope,
        previous: CampaignAutomation | None,
    ) -> WorkflowEnvelope:
        scheduler = self._campaign_scheduler
        if scheduler is None:
            return envelope.model_copy(update={"automation": previous}, deep=True)

        if operation not in {
            "review",
            "resume",
            "submit_evidence",
            "submit_photo_evidence",
            "review_evidence",
            "run_next_check",
            "prepare_packet",
            "approve_packet",
        }:
            return envelope.model_copy(update={"automation": previous}, deep=True)

        snapshot = envelope.snapshot
        plan = snapshot.plan
        notice = snapshot.notice
        if envelope.packet is not None or operation in {"prepare_packet", "approve_packet"}:
            scheduler.cancel(previous)
            return envelope.model_copy(
                update={
                    "automation": CampaignAutomation(
                        status=AutomationStatus.COMPLETE,
                        schedule_version=previous.schedule_version if previous else 0,
                    )
                },
                deep=True,
            )
        latest_evidence = {
            assessment.citation_id: assessment for assessment in envelope.evidence
        }
        if any(
            assessment.status.value == "manual_review"
            for assessment in latest_evidence.values()
        ):
            scheduler.cancel(previous)
            return envelope.model_copy(
                update={
                    "automation": CampaignAutomation(
                        status=AutomationStatus.AWAITING_DECISION,
                        schedule_version=previous.schedule_version if previous else 0,
                    )
                },
                deep=True,
            )
        if operation in {"submit_evidence", "submit_photo_evidence"}:
            return envelope.model_copy(update={"automation": previous}, deep=True)
        if snapshot.status is WorkflowStatus.INTERRUPTED:
            scheduler.cancel(previous)
            return envelope.model_copy(
                update={
                    "automation": CampaignAutomation(
                        status=AutomationStatus.AWAITING_DECISION,
                        schedule_version=previous.schedule_version if previous else 0,
                    )
                },
                deep=True,
            )
        if plan is None or notice is None:
            return envelope.model_copy(update={"automation": previous}, deep=True)
        try:
            logical_check_on = next_campaign_check(
                plan.as_of,
                notice.reinspection_due_on,
            )
        except ValueError:
            scheduler.cancel(previous)
            return envelope.model_copy(
                update={
                    "automation": CampaignAutomation(
                        status=AutomationStatus.COMPLETE,
                        schedule_version=previous.schedule_version if previous else 0,
                    )
                },
                deep=True,
            )

        version = (previous.schedule_version if previous else 0) + 1
        automation = scheduler.schedule(
            owner_hash=owner,
            workflow_id=envelope.workflow_id,
            logical_check_on=logical_check_on,
            schedule_version=version,
            previous=previous,
        )
        return envelope.model_copy(update={"automation": automation}, deep=True)

    def packet_download_url(self, workflow_id: str) -> str:
        owner = self._owner()
        workflow = self._workflow(owner, workflow_id)
        key = workflow.get("packet_key")
        if not isinstance(key, str):
            result = self._invoke(
                session_id=workflow["session_id"],
                payload={"operation": "render_packet", "workflow_id": workflow_id},
            )
            if result.get("ok") is not True or result.get("content_type") != "application/pdf":
                self._raise_result_error(result)
            encoded = result.get("body_base64")
            expected_hash = result.get("sha256")
            if not isinstance(encoded, str) or not isinstance(expected_hash, str):
                raise AgentCoreGatewayError("AgentCore returned an invalid packet")
            try:
                pdf = base64.b64decode(encoded, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise AgentCoreGatewayError("AgentCore returned an invalid packet encoding") from exc
            if not pdf.startswith(b"%PDF-") or len(pdf) > MAX_PACKET_BYTES:
                raise AgentCoreGatewayError("AgentCore returned an invalid packet")
            if sha256(pdf).hexdigest() != expected_hash:
                raise AgentCoreGatewayError("AgentCore packet integrity check failed")
            key = f"{owner}/{workflow_id}/{expected_hash}.pdf"
            self._packet_bucket.put_object(
                Key=key,
                Body=pdf,
                ContentType="application/pdf",
                ContentDisposition='attachment; filename="mettle-reinspection-packet.pdf"',
                CacheControl="no-store",
                ServerSideEncryption="AES256",
                Metadata={"sha256": expected_hash},
            )
            self._table.update_item(
                Key={"pk": self._workflow_key(owner, workflow_id)},
                UpdateExpression="SET packet_key = :key, expires_at = :expires_at",
                ExpressionAttributeValues={":key": key, ":expires_at": self._expires_at()},
            )
        return self._packet_bucket.meta.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self._packet_bucket.name,
                "Key": key,
                "ResponseContentType": "application/pdf",
                "ResponseContentDisposition": 'attachment; filename="mettle-reinspection-packet.pdf"',
            },
            ExpiresIn=60,
        )

    def _workflow(self, owner: str, workflow_id: str) -> dict[str, Any]:
        item = self._get(self._workflow_key(owner, workflow_id), required=False)
        if not item:
            raise WorkflowNotFound("AgentCore workflow does not exist")
        return item

    def _get(self, key: str, *, required: bool = True) -> dict[str, Any]:
        item = self._table.get_item(Key={"pk": key}, ConsistentRead=True).get("Item")
        if not isinstance(item, dict):
            if required:
                raise AgentCoreGatewayError("AgentCore session state is unavailable")
            return {}
        return item

    def _release_lock(self, workflow_key: str, lock_token: str) -> None:
        try:
            self._table.update_item(
                Key={"pk": workflow_key},
                UpdateExpression="REMOVE lock_token, lock_until",
                ConditionExpression="lock_token = :token",
                ExpressionAttributeValues={":token": lock_token},
            )
        except ClientError as exc:
            if not _is_conditional_failure(exc):
                raise

    def _invoke(self, *, session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return invoke_json(
                self._client,
                runtime_arn=self._runtime_arn,
                session_id=session_id,
                payload=payload,
            )
        except Exception as exc:
            error_code = "unknown"
            request_id = "unknown"
            if isinstance(exc, ClientError):
                error = exc.response.get("Error", {})
                metadata = exc.response.get("ResponseMetadata", {})
                error_code = str(error.get("Code", "unknown"))
                request_id = str(metadata.get("RequestId", "unknown"))
            LOGGER.warning(
                "agentcore_invoke_failed error_type=%s code=%s request_id=%s",
                type(exc).__name__,
                error_code,
                request_id,
            )
            raise AgentCoreGatewayError(
                "AgentCore could not be reached with the current server configuration"
            ) from exc

    @staticmethod
    def _envelope(value: Any) -> WorkflowEnvelope:
        try:
            return WorkflowEnvelope.model_validate(value)
        except ValidationError as exc:
            raise AgentCoreGatewayError("Stored AgentCore workflow is invalid") from exc

    @classmethod
    def _parse_result(cls, result: dict[str, Any]) -> WorkflowEnvelope:
        if result.get("ok") is True:
            try:
                return WorkflowEnvelope.model_validate(result.get("workflow"))
            except ValidationError as exc:
                raise AgentCoreGatewayError("AgentCore returned an invalid Mettle workflow") from exc
        cls._raise_result_error(result)
        raise AgentCoreGatewayError("AgentCore could not complete the operation")

    @staticmethod
    def _raise_result_error(result: dict[str, Any]) -> None:
        error = result.get("error")
        code = error.get("code") if isinstance(error, dict) else None
        message = error.get("message") if isinstance(error, dict) else None
        safe_message = message if isinstance(message, str) else "AgentCore operation failed"
        if code == "workflow_not_found":
            raise WorkflowNotFound(safe_message)
        if code == "workflow_conflict":
            raise WorkflowConflict(safe_message)
        if code in {"invalid_request", "workflow_configuration_error"}:
            raise WorkflowConfigurationError(safe_message)
        if code == "bedrock_intake_failed":
            raise BedrockIntakeError(safe_message)
        if code == "invalid_evidence_submission":
            raise EvidenceSubmissionError(safe_message)
        if code == "packet_not_ready":
            raise PacketNotReady(safe_message)
        if code == "packet_not_approved":
            raise PacketNotApproved(safe_message)
        raise AgentCoreGatewayError("AgentCore could not complete the operation")
