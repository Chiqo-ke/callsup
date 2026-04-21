import io
import logging
import os
import re
import httpx
from contextlib import nullcontext
from datetime import datetime, timezone

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

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
from app.transcription import transcribe_audio, rapidapi_whisper_transcribe, whisper_transcribe

logger = logging.getLogger("callsup.audio_engine")

# Maps conv_id → OpenCode session ID (in-memory, reset on server restart)
_opencode_sessions: dict[str, str] = {}


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    setup_logging(active_settings.log_level)

    app = FastAPI(title="CALLSUP Audio Engine API", version=active_settings.service_version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8081", "http://127.0.0.1:8081"],
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

    class SimulateRequest(BaseModel):
        business_id: str
        conv_id: str
        script: str

    @app.post("/audio/simulate", status_code=200)
    async def simulate_call(body: SimulateRequest) -> dict:
        """Parse a text script into transcript segments and store them for playback."""
        now = datetime.now(timezone.utc)
        segments: list[TranscriptSegment] = []
        for idx, line in enumerate(body.script.splitlines()):
            line = line.strip()
            if not line:
                continue
            match = re.match(r"^([^:]+):\s*(.+)$", line)
            if not match:
                continue
            raw_speaker, text = match.group(1).strip(), match.group(2).strip()
            speaker_lower = raw_speaker.lower()
            if "agent" in speaker_lower:
                speaker = "agent"
            elif "customer" in speaker_lower or "caller" in speaker_lower:
                speaker = "customer"
            else:
                speaker = None
            start_ts = datetime.fromtimestamp(now.timestamp() + idx * 5, tz=timezone.utc)
            end_ts = datetime.fromtimestamp(now.timestamp() + idx * 5 + 4, tz=timezone.utc)
            segments.append(
                TranscriptSegment(
                    business_id=body.business_id,
                    conv_id=body.conv_id,
                    segment_id=f"{body.conv_id}-{idx}",
                    speaker=speaker,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    text=text,
                    confidence=1.0,
                )
            )
        app.state.repository.save_transcript(body.conv_id, segments)
        logger.info(
            "audio_simulate_accepted",
            extra={"business_id": body.business_id, "conv_id": body.conv_id, "segments": len(segments)},
        )
        return {"status": "accepted", "conv_id": body.conv_id, "segments": len(segments)}

    # ------------------------------------------------------------------ #
    # Voice conversation endpoints (LLM + TTS + STT)                      #
    # ------------------------------------------------------------------ #

    class _ChatMessage(BaseModel):
        role: str  # "system" | "user" | "assistant"
        content: str

    class VoiceChatRequest(BaseModel):
        conv_id: str
        business_id: str
        message: str = ""
        history: list[_ChatMessage] = []
        first_turn: bool = False

    class VoiceTTSRequest(BaseModel):
        text: str
        voice: str = "alloy"

    @app.post("/audio/voice/chat")
    async def voice_chat(body: VoiceChatRequest) -> dict:
        """LLM conversation turn via OpenCode server. Returns {reply, history}."""
        opencode_url = os.environ.get("OPENCODE_SERVER_URL", "http://127.0.0.1:4096")
        system_prompt = (
            f"You are a professional customer service representative answering calls for "
            f"business '{body.business_id}'. Be helpful, polite, and concise (2-4 sentences). "
            "You are speaking on the phone — respond naturally as if speaking aloud."
        )

        async def _get_or_create_session() -> str:
            existing = _opencode_sessions.get(body.conv_id)
            async with httpx.AsyncClient(timeout=60.0) as c:
                if body.first_turn and existing:
                    try:
                        await c.delete(f"{opencode_url}/session/{existing}")
                    except Exception:
                        pass
                    del _opencode_sessions[body.conv_id]
                    existing = None
                if existing:
                    return existing
                resp = await c.post(f"{opencode_url}/session", json={"title": f"callsup-{body.conv_id}"})
                resp.raise_for_status()
                session_id = resp.json()["id"]
                _opencode_sessions[body.conv_id] = session_id
                # Inject system prompt silently (no AI reply)
                await c.post(
                    f"{opencode_url}/session/{session_id}/message",
                    json={"noReply": True, "parts": [{"type": "text", "text": system_prompt}]},
                )
                return session_id

        try:
            session_id = await _get_or_create_session()
            user_text = (
                "[A customer has just called. Please greet them and ask how you can help.]"
                if body.first_turn
                else body.message
            )
            async with httpx.AsyncClient(timeout=60.0) as c:
                resp = await c.post(
                    f"{opencode_url}/session/{session_id}/message",
                    json={"parts": [{"type": "text", "text": user_text}]},
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error("voice_chat_opencode_http_error", extra={"status": exc.response.status_code, "error": str(exc)})
            raise HTTPException(status_code=502, detail=f"OpenCode error: {exc}") from exc
        except Exception as exc:
            logger.error("voice_chat_opencode_error", extra={"error": str(exc)})
            raise HTTPException(status_code=502, detail=f"OpenCode error: {exc}") from exc

        # Extract text from response parts
        parts = data.get("parts") or []
        reply = " ".join(
            p.get("text", "") for p in parts if p.get("type") == "text"
        ).strip()
        if not reply:
            reply = data.get("info", {}).get("text", "")

        new_history = [m.model_dump() for m in body.history]
        if not body.first_turn:
            new_history.append({"role": "user", "content": body.message})
        new_history.append({"role": "assistant", "content": reply})

        logger.info(
            "voice_chat_turn",
            extra={"conv_id": body.conv_id, "first_turn": body.first_turn, "reply_len": len(reply)},
        )
        return {"reply": reply, "history": new_history}

    @app.post("/audio/voice/tts")
    async def voice_tts(body: VoiceTTSRequest) -> Response:
        """Convert text to speech using OpenAI TTS. Returns audio/mpeg bytes."""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured")

        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise HTTPException(status_code=503, detail="openai package not installed") from exc

        client = AsyncOpenAI(api_key=api_key)
        try:
            tts_response = await client.audio.speech.create(
                model="tts-1",
                voice=body.voice,
                input=body.text,
            )
        except Exception as exc:
            logger.error("voice_tts_openai_error", extra={"error": str(exc)})
            raise HTTPException(status_code=502, detail=f"OpenAI TTS error: {exc}") from exc
        audio_bytes = tts_response.content
        return Response(content=audio_bytes, media_type="audio/mpeg")

    @app.post("/audio/voice/stt")
    async def voice_stt(file: UploadFile = File(...)) -> dict:
        """Transcribe audio to text. Tries RapidAPI Whisper first, falls back to OpenAI Whisper."""
        audio_bytes = await file.read()
        settings = get_settings()
        logger.info("voice_stt_received", extra={"audio_filename": file.filename, "content_type": file.content_type, "bytes": len(audio_bytes)})

        if len(audio_bytes) < 100:
            logger.warning("voice_stt_empty_audio", extra={"bytes": len(audio_bytes)})
            return {"text": ""}

        # Attempt 1: RapidAPI Whisper
        if settings.rapidapi_whisper_key:
            try:
                fname = file.filename or "audio.webm"
                # Strip codec suffix (e.g. audio/webm;codecs=opus → audio/webm) so RapidAPI accepts the file
                raw_ctype = file.content_type or "audio/webm"
                ctype = raw_ctype.split(";")[0].strip()
                segments = rapidapi_whisper_transcribe(audio_bytes, filename=fname, content_type=ctype)
                text = " ".join(s.get("text", "") for s in segments).strip()
                if text:
                    logger.info("voice_stt_rapidapi", extra={"chars": len(text)})
                    return {"text": text}
            except Exception as exc:  # noqa: BLE001
                logger.warning("voice_stt_rapidapi_failed", extra={"error": str(exc)})

        # Attempt 2: OpenAI Whisper
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=503, detail="No transcription service available")

        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise HTTPException(status_code=503, detail="openai package not installed") from exc

        client = AsyncOpenAI(api_key=api_key)
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = file.filename or "audio.webm"
        try:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=("audio.webm", audio_file, "audio/webm"),
            )
        except Exception as exc:
            logger.error("voice_stt_openai_error", extra={"error": str(exc)})
            raise HTTPException(status_code=502, detail=f"OpenAI STT error: {exc}") from exc
        text = transcript.text.strip()
        logger.info("voice_stt_openai", extra={"chars": len(text)})
        return {"text": text}

    return app


app = create_app()

