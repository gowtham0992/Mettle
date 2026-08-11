from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from mettle.demo import DemoCampaign, DemoConflict, DemoNotFound, DemoStore


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


def create_app(*, store: DemoStore | None = None) -> FastAPI:
    app = FastAPI(
        title="Mettle local demo",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.store = store or DemoStore()

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

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> FileResponse:
        return FileResponse(STATIC_DIR / "mettle-icon.png", media_type="image/png")

    @app.get("/api/campaign", response_model=DemoCampaign)
    async def get_campaign(request: Request) -> DemoCampaign:
        return request.app.state.store.snapshot()

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

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
