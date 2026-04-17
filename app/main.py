import logging
from contextlib import nullcontext

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth import router as auth_router
from app.config import Settings, get_settings
from app.context_store import router as context_router
from app.logging_config import setup_logging
from app.metrics import (
    AUDIO_INGEST_REQUESTS,
    INGEST_PROCESSING_SECONDS,
    TRANSCRIPT_FETCH_REQUESTS,
    metrics_app,
)
from app.models import TranscriptSegment
from app.storage import AudioRepository
from app.transcription import transcribe_audio

logger = logging.getLogger("callsup.audio_engine")


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    setup_logging(active_settings.log_level)

    app = FastAPI(title="CALLSUP Audio Engine API", version=active_settings.service_version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8081"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router)
    app.include_router(context_router)
    app.mount("/metrics", metrics_app)
    app.state.repository = AudioRepository(
        data_dir=active_settings.data_dir,
        encryption_key=active_settings.get_encryption_key(),
    )

    @app.middleware("http")
    async def tls_and_security_headers(request: Request, call_next):
        if active_settings.enforce_tls_in_transit and not active_settings.allow_insecure_http:
            if request.url.scheme != "https":
                return JSONResponse(status_code=400, content={"detail": "TLS is required"})
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": active_settings.service_version}

    @app.post("/audio/ingest", status_code=202)
    async def ingest_audio(
        business_id: str = Form(...),
        conv_id: str = Form(...),
        file: UploadFile = File(...),
    ) -> dict[str, str]:
        AUDIO_INGEST_REQUESTS.inc()
        context = INGEST_PROCESSING_SECONDS.time() if INGEST_PROCESSING_SECONDS else nullcontext()
        with context:
            payload = await file.read()
            app.state.repository.save_audio(conv_id, payload)
            segments = transcribe_audio(business_id=business_id, conv_id=conv_id, audio_bytes=payload)
            app.state.repository.save_transcript(conv_id, segments)
            logger.info(
                "audio_ingest_accepted",
                extra={"business_id": business_id, "conv_id": conv_id, "segments": len(segments)},
            )
        return {"status": "accepted", "conv_id": conv_id}

    @app.get("/audio/transcript/{conv_id}", response_model=list[TranscriptSegment])
    async def get_transcript(conv_id: str) -> list[TranscriptSegment]:
        TRANSCRIPT_FETCH_REQUESTS.inc()
        try:
            return app.state.repository.get_transcript(conv_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="conversation not found") from exc

    return app


app = create_app()

