from __future__ import annotations

import os
from pathlib import Path

import boto3
from fastapi import FastAPI, Header, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from mettle.agents.bedrock import (
    BedrockIntakeError,
    BedrockIntakeSettings,
    extract_notice_with_bedrock,
)
from mettle.agentcore_gateway import (
    AgentCoreGatewayError,
    AgentCoreWorkflowGateway,
)
from mettle.demo import DemoCampaign, DemoConflict, DemoNotFound, DemoStore
from mettle.workflow import WorkflowConfigurationError
from mettle.workflow_registry import (
    ApprovePacketRequest,
    CreateWorkflowRequest,
    EvidenceSubmissionError,
    IntakeProvider,
    PacketNotApproved,
    PacketNotReady,
    PreparePacketRequest,
    ResumeWorkflowRequest,
    SubmitEvidenceRequest,
    WorkflowCapacityReached,
    WorkflowConflict,
    WorkflowEnvelope,
    WorkflowNotFound,
    WorkflowRegistry,
)


STATIC_DIR = Path(__file__).with_name("static")


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

    return WorkflowRegistry(bedrock_intake=bedrock_intake)


def configured_agentcore_gateway() -> AgentCoreWorkflowGateway | None:
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
    return AgentCoreWorkflowGateway(
        client=session.client("bedrock-agentcore"),
        runtime_arn=runtime_arn,
    )


def create_app(
    *,
    store: DemoStore | None = None,
    workflows: WorkflowRegistry | None = None,
    agentcore: AgentCoreWorkflowGateway | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Mettle local demo",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.store = store or DemoStore()
    app.state.workflows = workflows or configured_workflow_registry()
    app.state.agentcore = agentcore or configured_agentcore_gateway()

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

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
        return request.app.state.store.snapshot()

    @app.get("/api/capabilities", response_model=CapabilitiesResponse)
    async def get_capabilities(request: Request) -> CapabilitiesResponse:
        return CapabilitiesResponse(
            bedrock_intake=request.app.state.workflows.bedrock_enabled,
            agentcore_runtime=request.app.state.agentcore is not None,
        )

    @app.post("/api/demo/advance", response_model=DemoCampaign)
    async def advance_demo(payload: AdvanceRequest, request: Request) -> DemoCampaign:
        return request.app.state.store.advance(idempotency_key=payload.idempotency_key)

    @app.post("/api/demo/reset", response_model=DemoCampaign)
    async def reset_demo(request: Request) -> DemoCampaign:
        return request.app.state.store.reset()

    @app.post("/api/judgments/{judgment_id}/resolve", response_model=DemoCampaign)
    async def resolve_judgment(
        judgment_id: str,
        payload: ResolveJudgmentRequest,
        request: Request,
    ) -> DemoCampaign:
        if not judgment_id or len(judgment_id) > 64:
            raise DemoNotFound("judgment does not exist")
        return request.app.state.store.resolve_judgment(
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
