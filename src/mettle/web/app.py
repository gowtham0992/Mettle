from __future__ import annotations

import base64
import binascii
import os
import re
import secrets
from hashlib import sha256
from pathlib import Path

import boto3
from botocore.config import Config as AWSClientConfig
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, Header, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from mettle.agents.bedrock import (
    BedrockIntakeError,
    BedrockIntakeSettings,
    extract_notice_with_bedrock,
)
from mettle.agents.vision import (
    BedrockVisionError,
    BedrockVisionSettings,
    assess_photo_with_bedrock,
)
from mettle.agentcore_gateway import (
    AgentCoreGatewayError,
    AgentCoreWorkflowGateway,
)
from mettle.automation import EventBridgeCampaignScheduler
from mettle.durable_agentcore_gateway import DurableAgentCoreWorkflowGateway
from mettle.demo import DemoCampaign, DemoConflict, DemoNotFound, DemoStore
from mettle.demo_sessions import DynamoDemoSessions, InMemoryDemoSessions
from mettle.workflow import WorkflowConfigurationError
from mettle.photo_upload import MAX_UPLOAD_BYTES, PhotoUploadError, normalize_photo
from mettle.request_identity import (
    AuthenticationRequired,
    require_principal,
    reset_principal,
    set_principal,
)
from mettle.notice_parser import NoticeParseError
from mettle.notice_upload import (
    MAX_NOTICE_BYTES,
    NoticeUploadError,
    extract_notice_text,
    extract_notice_ocr,
)
from mettle.workflow_registry import (
    ApprovePacketRequest,
    CreateWorkflowRequest,
    EvidenceSubmissionError,
    IntakeProvider,
    PacketNotApproved,
    PacketNotReady,
    PreparePacketRequest,
    ReviewEvidenceRequest,
    ReviewWorkflowRequest,
    RunNextCheckRequest,
    ResumeWorkflowRequest,
    SubmitEvidenceRequest,
    SubmitPhotoEvidenceRequest,
    WorkflowCapacityReached,
    WorkflowConflict,
    WorkflowEnvelope,
    WorkflowNotFound,
    WorkflowRegistry,
)


STATIC_DIR = Path(__file__).with_name("static")
DEMO_SESSION_COOKIE = "mettle_demo_session"
DEMO_SESSION_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32,64}$")


class AdvanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class ResolveJudgmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(min_length=3, max_length=500)

    @field_validator("decision")
    @classmethod
    def normalize_decision(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 3:
            raise ValueError("decision must contain at least 3 visible characters")
        return normalized


class CapabilitiesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    bedrock_intake: bool
    agentcore_runtime: bool
    photo_evidence: bool
    max_photo_bytes: int


class PublicConfigResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cognito_domain: str | None
    cognito_client_id: str | None
    notice_ocr: bool = False


class EncodedPhotoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    image_base64: str = Field(min_length=4, max_length=6_700_000)


class EncodedNoticeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    filename: str = Field(min_length=5, max_length=180)
    file_base64: str = Field(min_length=4, max_length=6_700_000)


class NoticeTextResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str


def configured_workflow_registry() -> WorkflowRegistry:
    """Build a registry whose paid intake boundary is explicitly server-enabled."""
    if os.getenv("METTLE_BEDROCK_ENABLED") != "1":
        return WorkflowRegistry()

    settings = BedrockIntakeSettings(
        region=os.getenv("METTLE_AWS_REGION", "us-east-1"),
        profile=os.getenv("METTLE_AWS_PROFILE") or None,
        model_id="amazon.nova-micro-v1:0",
    )

    def bedrock_intake(text: str):
        return extract_notice_with_bedrock(text, settings=settings)

    vision_settings = BedrockVisionSettings(
        region=settings.region,
        profile=settings.profile,
    )

    def photo_assessor(**kwargs):
        return assess_photo_with_bedrock(**kwargs, settings=vision_settings)

    return WorkflowRegistry(
        bedrock_intake=bedrock_intake,
        photo_assessor=photo_assessor,
    )


def configured_agentcore_gateway() -> AgentCoreWorkflowGateway | DurableAgentCoreWorkflowGateway | None:
    """Build the paid cloud boundary only after an explicit server opt-in."""
    if os.getenv("METTLE_AGENTCORE_ENABLED") != "1":
        return None
    runtime_arn = os.getenv("METTLE_AGENTCORE_RUNTIME_ARN", "")
    if not runtime_arn:
        raise ValueError(
            "METTLE_AGENTCORE_RUNTIME_ARN is required when AgentCore is enabled"
        )
    region = os.getenv("METTLE_AWS_REGION", "us-east-1")
    profile = os.getenv("METTLE_AWS_PROFILE") or None
    session = boto3.Session(profile_name=profile, region_name=region)
    table_name = os.getenv("METTLE_DYNAMODB_TABLE")
    packet_bucket_name = os.getenv("METTLE_PACKET_BUCKET")
    if table_name and packet_bucket_name:
        campaign_scheduler = None
        if os.getenv("METTLE_SCHEDULER_ENABLED") == "1":
            target_arn = os.getenv("METTLE_SCHEDULER_TARGET_ARN", "")
            execution_role_arn = os.getenv("METTLE_SCHEDULER_ROLE_ARN", "")
            schedule_group = os.getenv("METTLE_SCHEDULER_GROUP", "")
            dlq_arn = os.getenv("METTLE_SCHEDULER_DLQ_ARN", "")
            if not all(
                (target_arn, execution_role_arn, schedule_group, dlq_arn)
            ):
                raise ValueError(
                    "scheduler target, role, group, and DLQ are required when automation is enabled"
                )
            delay = os.getenv("METTLE_SCHEDULER_DEMO_DELAY_SECONDS")
            campaign_scheduler = EventBridgeCampaignScheduler(
                client=session.client("scheduler"),
                target_arn=target_arn,
                execution_role_arn=execution_role_arn,
                schedule_group=schedule_group,
                dlq_arn=dlq_arn,
                timezone_name=os.getenv(
                    "METTLE_SCHEDULER_TIMEZONE", "America/Denver"
                ),
                demo_delay_seconds=int(delay) if delay else None,
            )
        return DurableAgentCoreWorkflowGateway(
            client=session.client("bedrock-agentcore"),
            runtime_arn=runtime_arn,
            table=session.resource("dynamodb").Table(table_name),
            packet_bucket=session.resource("s3").Bucket(packet_bucket_name),
            campaign_scheduler=campaign_scheduler,
        )
    return AgentCoreWorkflowGateway(client=session.client("bedrock-agentcore"), runtime_arn=runtime_arn)


def configured_demo_sessions(*, first_store: DemoStore | None = None):
    table_name = os.getenv("METTLE_DYNAMODB_TABLE")
    if not table_name or os.getenv("METTLE_DEMO_DURABLE", "0") != "1":
        return InMemoryDemoSessions(first_store=first_store)
    region = os.getenv("METTLE_AWS_REGION", "us-east-1")
    profile = os.getenv("METTLE_AWS_PROFILE") or None
    session = boto3.Session(profile_name=profile, region_name=region)
    return DynamoDemoSessions(table=session.resource("dynamodb").Table(table_name))


def _verified_subject(request: Request) -> str | None:
    event = request.scope.get("aws.event")
    if not isinstance(event, dict):
        return None
    request_context = event.get("requestContext")
    authorizer = request_context.get("authorizer") if isinstance(request_context, dict) else None
    jwt = authorizer.get("jwt") if isinstance(authorizer, dict) else None
    claims = jwt.get("claims") if isinstance(jwt, dict) else None
    subject = claims.get("sub") if isinstance(claims, dict) else None
    if isinstance(subject, str) and 1 <= len(subject) <= 128:
        return subject
    return None


def create_app(
    *,
    store: DemoStore | None = None,
    workflows: WorkflowRegistry | None = None,
    agentcore: AgentCoreWorkflowGateway | None = None,
    demo_sessions=None,
) -> FastAPI:
    app = FastAPI(
        title="Mettle local demo",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.demo_sessions = demo_sessions or configured_demo_sessions(first_store=store)
    app.state.workflows = workflows or configured_workflow_registry()
    app.state.agentcore = agentcore or configured_agentcore_gateway()

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        raw_session = request.cookies.get(DEMO_SESSION_COOKIE, "")
        new_session = not DEMO_SESSION_PATTERN.fullmatch(raw_session)
        if new_session:
            raw_session = secrets.token_urlsafe(24)
        request.state.demo_session_key = sha256(raw_session.encode("ascii")).hexdigest()
        principal_token = set_principal(_verified_subject(request))
        try:
            response = await call_next(request)
        finally:
            reset_principal(principal_token)
        cognito_domain = os.getenv("METTLE_COGNITO_DOMAIN", "").rstrip("/")
        connect_sources = "'self'" + (f" {cognito_domain}" if cognito_domain else "")
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            f"script-src 'self'; connect-src {connect_sources}; base-uri 'none'; "
            "frame-ancestors 'self'; form-action 'self'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        if new_session:
            response.set_cookie(
                key=DEMO_SESSION_COOKIE,
                value=raw_session,
                max_age=2 * 60 * 60,
                path="/",
                secure=request.url.scheme == "https",
                httponly=True,
                samesite="lax",
            )
        return response

    @app.exception_handler(AuthenticationRequired)
    async def authentication_required(_request: Request, exc: AuthenticationRequired):
        return JSONResponse(
            status_code=401,
            content={"error": {"code": "authentication_required", "message": str(exc)}},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        fields = [".".join(str(part) for part in item["loc"]) for item in exc.errors()]
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_request",
                    "message": "Request validation failed.",
                    "fields": fields,
                }
            },
        )

    @app.exception_handler(DemoNotFound)
    async def not_found(_request: Request, exc: DemoNotFound):
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "not_found", "message": str(exc)}},
        )

    @app.exception_handler(DemoConflict)
    async def conflict(_request: Request, exc: DemoConflict):
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "conflict", "message": str(exc)}},
        )

    @app.exception_handler(WorkflowNotFound)
    async def workflow_not_found(_request: Request, exc: WorkflowNotFound):
        return JSONResponse(
            status_code=404,
            content={
                "error": {"code": "workflow_not_found", "message": str(exc)}
            },
        )

    @app.exception_handler(WorkflowConflict)
    async def workflow_conflict(_request: Request, exc: WorkflowConflict):
        return JSONResponse(
            status_code=409,
            content={
                "error": {"code": "idempotency_conflict", "message": str(exc)}
            },
        )

    @app.exception_handler(WorkflowCapacityReached)
    async def workflow_capacity(_request: Request, exc: WorkflowCapacityReached):
        return JSONResponse(
            status_code=503,
            content={
                "error": {"code": "workflow_capacity_reached", "message": str(exc)}
            },
            headers={"Retry-After": "60"},
        )

    @app.exception_handler(WorkflowConfigurationError)
    async def workflow_configuration(
        _request: Request,
        exc: WorkflowConfigurationError,
    ):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "workflow_configuration_error",
                    "message": str(exc),
                }
            },
        )

    @app.exception_handler(NoticeParseError)
    async def unsupported_notice_format(_request: Request, _exc: NoticeParseError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "unsupported_notice_format",
                    "message": (
                        "Mettle could not identify the notice schedule or correction lines. "
                        "Keep the permit or record ID, inspection date, reinspection deadline, "
                        "property address, and numbered correction text in the paste."
                    ),
                }
            },
        )

    @app.exception_handler(BedrockIntakeError)
    async def bedrock_intake_error(_request: Request, exc: BedrockIntakeError):
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "code": "bedrock_intake_failed",
                    "message": str(exc),
                }
            },
            headers={"Retry-After": "5"},
        )

    @app.exception_handler(BedrockVisionError)
    async def bedrock_vision_error(_request: Request, exc: BedrockVisionError):
        return JSONResponse(
            status_code=502,
            content={"error": {"code": "bedrock_vision_failed", "message": str(exc)}},
            headers={"Retry-After": "5"},
        )

    @app.exception_handler(PhotoUploadError)
    async def photo_upload_error(_request: Request, exc: PhotoUploadError):
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "invalid_photo", "message": str(exc)}},
        )

    @app.exception_handler(NoticeUploadError)
    async def notice_upload_error(_request: Request, exc: NoticeUploadError):
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "invalid_notice_file", "message": str(exc)}},
        )

    @app.exception_handler(AgentCoreGatewayError)
    async def agentcore_gateway_error(_request: Request, exc: AgentCoreGatewayError):
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "code": "agentcore_invocation_failed",
                    "message": str(exc),
                }
            },
            headers={"Retry-After": "5"},
        )

    @app.exception_handler(EvidenceSubmissionError)
    async def evidence_submission(
        _request: Request,
        exc: EvidenceSubmissionError,
    ):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_evidence_submission",
                    "message": str(exc),
                }
            },
        )

    @app.exception_handler(PacketNotReady)
    async def packet_not_ready(_request: Request, exc: PacketNotReady):
        return JSONResponse(
            status_code=422,
            content={
                "error": {"code": "packet_not_ready", "message": str(exc)}
            },
        )

    @app.exception_handler(PacketNotApproved)
    async def packet_not_approved(_request: Request, exc: PacketNotApproved):
        return JSONResponse(
            status_code=409,
            content={
                "error": {"code": "packet_not_approved", "message": str(exc)}
            },
        )

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> FileResponse:
        return FileResponse(STATIC_DIR / "mettle-icon.png", media_type="image/png")

    @app.get("/api/campaign", response_model=DemoCampaign)
    async def get_campaign(request: Request) -> DemoCampaign:
        return await run_in_threadpool(
            request.app.state.demo_sessions.snapshot,
            request.state.demo_session_key,
        )

    @app.get("/api/capabilities", response_model=CapabilitiesResponse)
    async def get_capabilities(request: Request) -> CapabilitiesResponse:
        return CapabilitiesResponse(
            bedrock_intake=request.app.state.workflows.bedrock_enabled,
            agentcore_runtime=request.app.state.agentcore is not None,
            photo_evidence=(
                request.app.state.workflows.vision_enabled
                or request.app.state.agentcore is not None
            ),
            max_photo_bytes=min(
                MAX_UPLOAD_BYTES,
                int(os.getenv("METTLE_MAX_UPLOAD_BYTES", str(MAX_UPLOAD_BYTES))),
            ),
        )

    @app.get("/api/config", response_model=PublicConfigResponse)
    async def get_public_config() -> PublicConfigResponse:
        return PublicConfigResponse(
            cognito_domain=os.getenv("METTLE_COGNITO_DOMAIN") or None,
            cognito_client_id=os.getenv("METTLE_COGNITO_CLIENT_ID") or None,
            notice_ocr=os.getenv("METTLE_NOTICE_OCR_ENABLED") == "1",
        )

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/notices/text", response_model=NoticeTextResponse)
    async def notice_text(payload: EncodedNoticeRequest) -> NoticeTextResponse:
        try:
            raw = base64.b64decode(payload.file_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise NoticeUploadError("The report file encoding is invalid.") from exc
        if len(raw) > MAX_NOTICE_BYTES:
            raise NoticeUploadError("The report must be 5 MB or smaller.")
        text = await run_in_threadpool(
            extract_notice_text,
            raw,
            filename=payload.filename,
        )
        return NoticeTextResponse(text=text)

    @app.post("/api/agentcore/notices/ocr", response_model=NoticeTextResponse)
    async def notice_ocr(payload: EncodedNoticeRequest) -> NoticeTextResponse:
        require_principal()
        if os.getenv("METTLE_NOTICE_OCR_ENABLED") != "1":
            raise NoticeUploadError("Photo reading is not enabled. Paste the inspection comments instead.")
        try:
            raw = base64.b64decode(payload.file_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise NoticeUploadError("The report file encoding is invalid.") from exc
        try:
            client = boto3.client("textract", region_name=os.getenv("AWS_REGION", "us-east-1"),
                                  config=AWSClientConfig(connect_timeout=3, read_timeout=20,
                                                         retries={"total_max_attempts": 1}))
            text = await run_in_threadpool(extract_notice_ocr, raw, filename=payload.filename, client=client)
        except (BotoCoreError, ClientError) as exc:
            raise NoticeUploadError("Photo reading could not finish. Your pasted text has not changed. Try again or paste the comments.") from exc
        return NoticeTextResponse(text=text)

    async def read_photo(request: Request) -> bytes:
        upload_limit = min(
            MAX_UPLOAD_BYTES,
            int(os.getenv("METTLE_MAX_UPLOAD_BYTES", str(MAX_UPLOAD_BYTES))),
        )
        content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
        if content_type not in {"image/jpeg", "image/png", "application/json"}:
            raise PhotoUploadError(
                "photo must be uploaded as image/jpeg, image/png, or encoded JSON"
            )
        body_limit = (
            4 * ((upload_limit + 2) // 3) + 1024
            if content_type == "application/json"
            else upload_limit
        )
        declared = request.headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > body_limit:
                    raise PhotoUploadError("photo exceeds the configured upload limit")
            except ValueError as exc:
                raise PhotoUploadError("photo has an invalid content length") from exc
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > body_limit:
                raise PhotoUploadError("photo exceeds the configured upload limit")
        raw = bytes(body)
        if content_type == "application/json":
            try:
                payload = EncodedPhotoRequest.model_validate_json(raw)
            except ValueError as exc:
                raise PhotoUploadError("photo payload is invalid") from exc
            try:
                raw = base64.b64decode(payload.image_base64, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise PhotoUploadError("photo encoding is invalid") from exc
            if len(raw) > upload_limit:
                raise PhotoUploadError("photo exceeds the configured upload limit")
        return await run_in_threadpool(normalize_photo, raw)

    @app.post("/api/demo/advance", response_model=DemoCampaign)
    async def advance_demo(payload: AdvanceRequest, request: Request) -> DemoCampaign:
        return await run_in_threadpool(
            request.app.state.demo_sessions.advance,
            request.state.demo_session_key,
            idempotency_key=payload.idempotency_key,
        )

    @app.post("/api/demo/reset", response_model=DemoCampaign)
    async def reset_demo(request: Request) -> DemoCampaign:
        return await run_in_threadpool(
            request.app.state.demo_sessions.reset,
            request.state.demo_session_key,
        )

    @app.get("/api/demo/packet.pdf")
    async def download_demo_packet(request: Request) -> Response:
        pdf = await run_in_threadpool(
            request.app.state.demo_sessions.render_packet,
            request.state.demo_session_key,
            evidence_dir=STATIC_DIR / "evidence",
        )
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    'attachment; filename="mettle-guided-reinspection-packet.pdf"'
                )
            },
        )

    @app.get("/api/demo/packet/preview.pdf")
    async def preview_demo_packet(request: Request) -> Response:
        pdf = await run_in_threadpool(
            request.app.state.demo_sessions.render_packet,
            request.state.demo_session_key,
            evidence_dir=STATIC_DIR / "evidence",
        )
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    'inline; filename="mettle-guided-reinspection-packet.pdf"'
                )
            },
        )

    @app.post("/api/judgments/{judgment_id}/resolve", response_model=DemoCampaign)
    async def resolve_judgment(
        judgment_id: str,
        payload: ResolveJudgmentRequest,
        request: Request,
    ) -> DemoCampaign:
        if not judgment_id or len(judgment_id) > 64:
            raise DemoNotFound("judgment does not exist")
        return await run_in_threadpool(
            request.app.state.demo_sessions.resolve_judgment,
            request.state.demo_session_key,
            judgment_id,
            decision=payload.decision,
        )

    @app.post("/api/workflows", response_model=WorkflowEnvelope)
    def create_workflow(
        payload: CreateWorkflowRequest,
        request: Request,
        response: Response,
        idempotency_key: str = Header(
            min_length=8,
            max_length=64,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ) -> WorkflowEnvelope:
        envelope, replayed = request.app.state.workflows.create(
            payload,
            idempotency_key=idempotency_key,
        )
        response.status_code = 200 if replayed else 201
        return envelope

    @app.get("/api/workflows/{workflow_id}", response_model=WorkflowEnvelope)
    def get_workflow(workflow_id: str, request: Request) -> WorkflowEnvelope:
        if not workflow_id or len(workflow_id) > 64:
            raise WorkflowNotFound("workflow does not exist")
        return request.app.state.workflows.get(workflow_id)

    @app.post(
        "/api/workflows/{workflow_id}/review",
        response_model=WorkflowEnvelope,
    )
    def review_workflow(
        workflow_id: str,
        payload: ReviewWorkflowRequest,
        request: Request,
        idempotency_key: str = Header(
            min_length=8,
            max_length=64,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ) -> WorkflowEnvelope:
        if not workflow_id or len(workflow_id) > 64:
            raise WorkflowNotFound("workflow does not exist")
        return request.app.state.workflows.review(
            workflow_id,
            payload,
            idempotency_key=idempotency_key,
        )

    @app.post(
        "/api/workflows/{workflow_id}/resume",
        response_model=WorkflowEnvelope,
    )
    def resume_workflow(
        workflow_id: str,
        payload: ResumeWorkflowRequest,
        request: Request,
        idempotency_key: str = Header(
            min_length=8,
            max_length=64,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ) -> WorkflowEnvelope:
        if not workflow_id or len(workflow_id) > 64:
            raise WorkflowNotFound("workflow does not exist")
        return request.app.state.workflows.resume(
            workflow_id,
            payload,
            idempotency_key=idempotency_key,
        )

    def require_agentcore(request: Request) -> AgentCoreWorkflowGateway:
        gateway = request.app.state.agentcore
        if gateway is None:
            raise WorkflowConfigurationError(
                "AgentCore execution is not enabled on this server"
            )
        return gateway

    @app.post("/api/agentcore/workflows", response_model=WorkflowEnvelope)
    def create_agentcore_workflow(
        payload: CreateWorkflowRequest,
        request: Request,
        response: Response,
        idempotency_key: str = Header(
            min_length=8,
            max_length=64,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ) -> WorkflowEnvelope:
        if payload.intake_provider is not IntakeProvider.BEDROCK:
            raise WorkflowConfigurationError(
                "AgentCore execution requires live Bedrock notice intake"
            )
        envelope, replayed = require_agentcore(request).create(
            payload,
            idempotency_key=idempotency_key,
        )
        response.status_code = 200 if replayed else 201
        return envelope

    @app.get(
        "/api/agentcore/workflows/{workflow_id}",
        response_model=WorkflowEnvelope,
    )
    def get_agentcore_workflow(
        workflow_id: str,
        request: Request,
    ) -> WorkflowEnvelope:
        if not workflow_id or len(workflow_id) > 64:
            raise WorkflowNotFound("AgentCore workflow does not exist on this server")
        return require_agentcore(request).get(workflow_id)

    @app.post(
        "/api/agentcore/workflows/{workflow_id}/resume",
        response_model=WorkflowEnvelope,
    )
    def resume_agentcore_workflow(
        workflow_id: str,
        payload: ResumeWorkflowRequest,
        request: Request,
        idempotency_key: str = Header(
            min_length=8,
            max_length=64,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ) -> WorkflowEnvelope:
        if not workflow_id or len(workflow_id) > 64:
            raise WorkflowNotFound("AgentCore workflow does not exist on this server")
        return require_agentcore(request).resume(
            workflow_id,
            payload,
            idempotency_key=idempotency_key,
        )

    @app.post(
        "/api/agentcore/workflows/{workflow_id}/review",
        response_model=WorkflowEnvelope,
    )
    def review_agentcore_workflow(
        workflow_id: str,
        payload: ReviewWorkflowRequest,
        request: Request,
        idempotency_key: str = Header(
            min_length=8,
            max_length=64,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ) -> WorkflowEnvelope:
        if not workflow_id or len(workflow_id) > 64:
            raise WorkflowNotFound("AgentCore workflow does not exist")
        return require_agentcore(request).review(
            workflow_id,
            payload,
            idempotency_key=idempotency_key,
        )

    @app.post(
        "/api/agentcore/workflows/{workflow_id}/evidence",
        response_model=WorkflowEnvelope,
    )
    def submit_agentcore_evidence(
        workflow_id: str,
        payload: SubmitEvidenceRequest,
        request: Request,
        idempotency_key: str = Header(
            min_length=8,
            max_length=64,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ) -> WorkflowEnvelope:
        return require_agentcore(request).submit_evidence(
            workflow_id,
            payload,
            idempotency_key=idempotency_key,
        )

    @app.post(
        "/api/agentcore/workflows/{workflow_id}/evidence/photo",
        response_model=WorkflowEnvelope,
    )
    async def submit_agentcore_photo_evidence(
        workflow_id: str,
        request: Request,
        citation_id: str,
        idempotency_key: str = Header(
            min_length=8,
            max_length=64,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ) -> WorkflowEnvelope:
        payload = SubmitPhotoEvidenceRequest(citation_id=citation_id)
        image = await read_photo(request)
        return await run_in_threadpool(
            require_agentcore(request).submit_photo_evidence,
            workflow_id,
            payload,
            image=image,
            idempotency_key=idempotency_key,
        )

    @app.post(
        "/api/agentcore/workflows/{workflow_id}/packet/prepare",
        response_model=WorkflowEnvelope,
    )
    def prepare_agentcore_packet(
        workflow_id: str,
        payload: PreparePacketRequest,
        request: Request,
        idempotency_key: str = Header(
            min_length=8,
            max_length=64,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ) -> WorkflowEnvelope:
        return require_agentcore(request).prepare_packet(
            workflow_id,
            payload,
            idempotency_key=idempotency_key,
        )

    @app.post(
        "/api/agentcore/workflows/{workflow_id}/evidence/review",
        response_model=WorkflowEnvelope,
    )
    def review_agentcore_evidence(
        workflow_id: str,
        payload: ReviewEvidenceRequest,
        request: Request,
        idempotency_key: str = Header(
            min_length=8,
            max_length=64,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ) -> WorkflowEnvelope:
        return require_agentcore(request).review_evidence(
            workflow_id,
            payload,
            idempotency_key=idempotency_key,
        )

    @app.post(
        "/api/agentcore/workflows/{workflow_id}/checks/next",
        response_model=WorkflowEnvelope,
    )
    def run_agentcore_next_check(
        workflow_id: str,
        payload: RunNextCheckRequest,
        request: Request,
        idempotency_key: str = Header(
            min_length=8,
            max_length=64,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ) -> WorkflowEnvelope:
        return require_agentcore(request).run_next_check(
            workflow_id,
            payload,
            idempotency_key=idempotency_key,
        )

    @app.post(
        "/api/agentcore/workflows/{workflow_id}/packet/approve",
        response_model=WorkflowEnvelope,
    )
    def approve_agentcore_packet(
        workflow_id: str,
        payload: ApprovePacketRequest,
        request: Request,
        idempotency_key: str = Header(
            min_length=8,
            max_length=64,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ) -> WorkflowEnvelope:
        return require_agentcore(request).approve_packet(
            workflow_id,
            payload,
            idempotency_key=idempotency_key,
        )

    @app.get("/api/agentcore/workflows/{workflow_id}/evidence/{assessment_id}/photo")
    def read_agentcore_photo(workflow_id: str, assessment_id: str, request: Request) -> Response:
        require_principal()
        image = require_agentcore(request).read_evidence_photo(workflow_id, assessment_id)
        return JSONResponse({"image_base64": base64.b64encode(image).decode("ascii")},
                            headers={"Cache-Control": "no-store"})

    @app.get("/api/agentcore/workflows/{workflow_id}/packet.pdf")
    def download_agentcore_packet(workflow_id: str, request: Request) -> Response:
        pdf = require_agentcore(request).render_packet(workflow_id)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    'attachment; filename="mettle-reinspection-packet.pdf"'
                ),
                "Cache-Control": "no-store",
            },
        )

    @app.get("/api/agentcore/workflows/{workflow_id}/packet-url")
    def get_agentcore_packet_url(workflow_id: str, request: Request) -> dict[str, str]:
        gateway = require_agentcore(request)
        packet_download_url = getattr(gateway, "packet_download_url", None)
        if not callable(packet_download_url):
            raise WorkflowConfigurationError(
                "Private packet links are available only on the serverless deployment"
            )
        return {"download_url": packet_download_url(workflow_id)}

    @app.post(
        "/api/workflows/{workflow_id}/evidence",
        response_model=WorkflowEnvelope,
    )
    def submit_evidence(
        workflow_id: str,
        payload: SubmitEvidenceRequest,
        request: Request,
        idempotency_key: str = Header(
            min_length=8,
            max_length=64,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ) -> WorkflowEnvelope:
        if not workflow_id or len(workflow_id) > 64:
            raise WorkflowNotFound("workflow does not exist")
        return request.app.state.workflows.submit_evidence(
            workflow_id,
            payload,
            idempotency_key=idempotency_key,
        )

    @app.post(
        "/api/workflows/{workflow_id}/evidence/photo",
        response_model=WorkflowEnvelope,
    )
    async def submit_photo_evidence(
        workflow_id: str,
        request: Request,
        citation_id: str,
        idempotency_key: str = Header(
            min_length=8,
            max_length=64,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ) -> WorkflowEnvelope:
        if not workflow_id or len(workflow_id) > 64:
            raise WorkflowNotFound("workflow does not exist")
        payload = SubmitPhotoEvidenceRequest(citation_id=citation_id)
        image = await read_photo(request)
        return await run_in_threadpool(
            request.app.state.workflows.submit_photo_evidence,
            workflow_id,
            payload,
            image=image,
            idempotency_key=idempotency_key,
        )

    @app.post(
        "/api/workflows/{workflow_id}/packet/prepare",
        response_model=WorkflowEnvelope,
    )
    def prepare_packet(
        workflow_id: str,
        _payload: PreparePacketRequest,
        request: Request,
        idempotency_key: str = Header(
            min_length=8,
            max_length=64,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ) -> WorkflowEnvelope:
        return request.app.state.workflows.prepare_packet(
            workflow_id,
            idempotency_key=idempotency_key,
        )

    @app.post(
        "/api/workflows/{workflow_id}/evidence/review",
        response_model=WorkflowEnvelope,
    )
    def review_evidence(
        workflow_id: str,
        payload: ReviewEvidenceRequest,
        request: Request,
        idempotency_key: str = Header(
            min_length=8,
            max_length=64,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ) -> WorkflowEnvelope:
        return request.app.state.workflows.review_evidence(
            workflow_id,
            payload,
            idempotency_key=idempotency_key,
        )

    @app.post(
        "/api/workflows/{workflow_id}/checks/next",
        response_model=WorkflowEnvelope,
    )
    def run_next_check(
        workflow_id: str,
        _payload: RunNextCheckRequest,
        request: Request,
        idempotency_key: str = Header(
            min_length=8,
            max_length=64,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ) -> WorkflowEnvelope:
        return request.app.state.workflows.run_next_check(
            workflow_id,
            idempotency_key=idempotency_key,
        )

    @app.post(
        "/api/workflows/{workflow_id}/packet/approve",
        response_model=WorkflowEnvelope,
    )
    def approve_packet(
        workflow_id: str,
        payload: ApprovePacketRequest,
        request: Request,
        idempotency_key: str = Header(
            min_length=8,
            max_length=64,
            pattern=r"^[A-Za-z0-9_-]+$",
        ),
    ) -> WorkflowEnvelope:
        return request.app.state.workflows.approve_packet(
            workflow_id,
            payload,
            idempotency_key=idempotency_key,
        )

    @app.get("/api/workflows/{workflow_id}/evidence/{assessment_id}/photo")
    def read_local_photo(workflow_id: str, assessment_id: str, request: Request) -> Response:
        image = request.app.state.workflows.read_evidence_photo(workflow_id, assessment_id)
        return JSONResponse({"image_base64": base64.b64encode(image).decode("ascii")},
                            headers={"Cache-Control": "no-store"})

    @app.get("/api/workflows/{workflow_id}/packet.pdf")
    def download_packet(workflow_id: str, request: Request) -> Response:
        pdf = request.app.state.workflows.render_packet(
            workflow_id,
            evidence_dir=STATIC_DIR / "evidence",
        )
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    'attachment; filename="mettle-reinspection-packet.pdf"'
                ),
                "Cache-Control": "no-store",
            },
        )

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
