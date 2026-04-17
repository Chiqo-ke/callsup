from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from callsup_intelligence_engine import __version__
from callsup_intelligence_engine.api.schemas import (
    E2EDemoRequest,
    E2EDemoResponse,
    HealthResponse,
    ReadinessResponse,
    StepRequest,
    StepResponse,
)
from callsup_intelligence_engine.core.audit import AuditStore
from callsup_intelligence_engine.core.conversation import ConversationLogStore, ConversationService
from callsup_intelligence_engine.core.llm_adapter import LLMAdapterClient
from callsup_intelligence_engine.core.pipeline import run_e2e_demo
from callsup_intelligence_engine.core.verification import TransactionVerifier


def build_service() -> ConversationService:
    llm_base_url = os.getenv("CALLSUP_INTELLIGENCE_ENGINE_LLM_ADAPTER_URL", "http://localhost:9000")
    model = os.getenv("CALLSUP_INTELLIGENCE_ENGINE_MODEL", "gpt-4.1-mini")
    llm = LLMAdapterClient(base_url=llm_base_url)
    return ConversationService(
        llm_client=llm,
        audit_store=AuditStore(),
        verifier=TransactionVerifier(),
        logs=ConversationLogStore(),
        model=model,
    )


def create_app(service: ConversationService | None = None) -> FastAPI:
    active_service = service or build_service()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.service = active_service
        yield
        await app.state.service.llm_client.close()

    app = FastAPI(title="CALLSUP Intelligence Engine API", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", version=__version__)

    @app.get("/readiness", response_model=ReadinessResponse)
    async def readiness() -> ReadinessResponse:
        checks = {
            "llm_adapter_url": app.state.service.llm_client.base_url,
            "status": "configured",
        }
        return ReadinessResponse(status="ready", checks=checks)

    @app.get("/metrics")
    async def metrics() -> PlainTextResponse:
        return PlainTextResponse(generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST)

    @app.post("/intelligence/step", response_model=StepResponse)
    async def intelligence_step(request: StepRequest) -> StepResponse:
        try:
            return await app.state.service.process_segment(request)
        except Exception as exc:  # surface explicit upstream failure
            raise HTTPException(status_code=502, detail=f"LLM adapter call failed: {exc}") from exc

    @app.post("/intelligence/e2e-demo", response_model=E2EDemoResponse)
    async def intelligence_e2e_demo(request: E2EDemoRequest) -> E2EDemoResponse:
        try:
            stages = await run_e2e_demo(
                service=app.state.service,
                business_id=request.business_id,
                conv_id=request.conv_id,
                audio_text=request.audio_text,
            )
            return E2EDemoResponse(
                stages=stages,
                redacted_transcript=stages["summary"]["redacted_transcript"],
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"E2E pipeline failed: {exc}") from exc

    return app


app = create_app()
