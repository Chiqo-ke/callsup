"""Unified CALLSUP gateway.

Combines the Audio Engine and Intelligence Engine onto a single port (8010),
so the frontend only ever needs to talk to one backend service.

The LLM Adapter (svc-llm-adapter) continues to run separately on port 9100
and is only ever called internally by this gateway.

Usage:
    uvicorn gateway:create_app --factory --host 127.0.0.1 --port 8010
"""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from app.main import create_app as _create_audio_app
from callsup_intelligence_engine.api.schemas import (
    E2EDemoRequest,
    E2EDemoResponse,
    StepRequest,
    StepResponse,
)
from callsup_intelligence_engine.core.audit import AuditStore
from callsup_intelligence_engine.core.conversation import (
    ConversationLogStore,
    ConversationService,
)
from callsup_intelligence_engine.core.llm_adapter import LLMAdapterClient
from callsup_intelligence_engine.core.pipeline import run_e2e_demo
from callsup_intelligence_engine.core.verification import TransactionVerifier


def _build_ie_service() -> ConversationService:
    llm_base_url = os.getenv(
        "CALLSUP_INTELLIGENCE_ENGINE_LLM_ADAPTER_URL", "http://127.0.0.1:9100"
    )
    model = os.getenv("CALLSUP_INTELLIGENCE_ENGINE_MODEL", "gpt-4o")
    llm = LLMAdapterClient(base_url=llm_base_url)
    return ConversationService(
        llm_client=llm,
        audit_store=AuditStore(),
        verifier=TransactionVerifier(),
        logs=ConversationLogStore(),
        model=model,
    )


def create_app() -> FastAPI:
    # ── Build the primary Audio Engine app (auth, audio, queue, rules, context) ──
    app = _create_audio_app()

    # ── Attach Intelligence Engine service to app state ──────────────────────
    ie_service = _build_ie_service()
    app.state.ie_service = ie_service

    llm_base_url = os.getenv(
        "CALLSUP_INTELLIGENCE_ENGINE_LLM_ADAPTER_URL", "http://127.0.0.1:9100"
    )

    # ── Intelligence Engine routes ────────────────────────────────────────────

    @app.get("/readiness")
    async def readiness() -> dict:
        return {
            "status": "ready",
            "checks": {
                "llm_adapter_url": llm_base_url,
                "status": "configured",
            },
        }

    @app.post("/intelligence/step", response_model=StepResponse)
    async def intelligence_step(request: StepRequest) -> StepResponse:
        try:
            return await app.state.ie_service.process_segment(request)
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail=f"LLM adapter call failed: {exc}"
            ) from exc

    @app.post("/intelligence/e2e-demo", response_model=E2EDemoResponse)
    async def intelligence_e2e_demo(request: E2EDemoRequest) -> E2EDemoResponse:
        try:
            stages = await run_e2e_demo(
                service=app.state.ie_service,
                business_id=request.business_id,
                conv_id=request.conv_id,
                audio_text=request.audio_text,
            )
            return E2EDemoResponse(
                stages=stages,
                redacted_transcript=stages["summary"]["redacted_transcript"],
            )
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail=f"E2E pipeline failed: {exc}"
            ) from exc

    return app


# Module-level app instance for uvicorn non-factory usage
app = create_app()
