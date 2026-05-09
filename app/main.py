import io
import json
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
from app.business_context import get_business_name, load_business_context
from app.config import Settings, get_settings
from app.context_store import router as context_router
from app.escalation_rules import list_active_rules
from app.escalation_rules import router as escalation_rules_router
from app.escalation_queue import broadcast_ticket, create_ticket_internal
from app.escalation_queue import router as escalation_queue_router
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

# Maps conv_id → {"session_id": str, "escalated": bool} (in-memory, reset on server restart)
_opencode_sessions: dict[str, dict] = {}

# ── Tool-calling schema for escalation decision ───────────────────────────────

ESCALATION_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "create_escalation_ticket",
        "description": (
            "Create a task queue entry to transfer the caller to a human support agent. "
            "Call this whenever your reply indicated that a human agent will assist the caller."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Brief reason for escalation (e.g. 'billing dispute', 'technical issue')",
                },
                "priority": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Urgency level of the escalation",
                },
                "rule_triggered": {
                    "type": "string",
                    "description": "The escalation rule that triggered this, if any",
                },
            },
            "required": ["reason", "priority"],
        },
    },
}


async def _run_tool_decision(
    llm_adapter_url: str,
    conversation_history: list[dict],
    agent_reply: str,
) -> dict | None:
    """Ask the LLM adapter whether the given agent_reply implies escalation.

    Returns the parsed tool-call arguments dict if create_escalation_ticket
    was called, or None otherwise.
    """
    system_prompt = (
        "You are evaluating whether an AI agent's reply to a phone caller indicates "
        "that the caller is being transferred to a human agent. "
        "If the reply says the caller will speak with a human, be connected to a human, "
        "or that a human agent will assist them, call create_escalation_ticket. "
        "Otherwise do nothing."
    )
    check_message = (
        f"The AI agent just said to the caller: '{agent_reply}'\n"
        "Self-check: Does this reply indicate the caller is being transferred to a human agent? "
        "If yes, call create_escalation_ticket with an appropriate reason and priority."
    )
    payload = {
        "prompt": check_message,
        "system_prompt": system_prompt,
        "history": conversation_history,
        "tools": [ESCALATION_TOOL_SCHEMA],
        "tool_choice": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as c:
            resp = await c.post(f"{llm_adapter_url}/v1/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
        tool_calls = data.get("tool_calls") or []
        if not tool_calls:
            # Keyword-based safety net: if the LLM adapter returned no tool call
            # but the agent reply clearly indicates a transfer to a human agent,
            # synthesise a tool-call result so the ticket is still created.
            _ESC_PATTERNS = [
                "human agent", "real agent", "real person", "live agent",
                "live representative", "connecting you", "transfer you",
                "connect you to", "put you through", "hold the line",
                "stay on the line", "please hold", "a human will",
                "human support", "specialist agent", "transferring you",
            ]
            reply_lower = agent_reply.lower()
            if any(p in reply_lower for p in _ESC_PATTERNS):
                logger.info("keyword_escalation_detected", extra={"reply": agent_reply[:120]})
                return {"reason": "Caller transferred to human agent (keyword match)", "priority": "medium"}
            return None
        first = tool_calls[0]
        if first.get("function", {}).get("name") != "create_escalation_ticket":
            return None
        args_raw = first["function"].get("arguments", "{}")
        args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
        priority = args.get("priority", "medium")
        if priority not in ("high", "medium", "low"):
            args["priority"] = "medium"
        return args
    except Exception as exc:
        logger.warning("tool_decision_error", extra={"error": str(exc)})
        return None


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    setup_logging(active_settings.log_level)

    app = FastAPI(title="CALLSUP Audio Engine API", version=active_settings.service_version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:8081",
            "http://127.0.0.1:8081",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router)
    app.include_router(context_router)
    app.include_router(escalation_rules_router)
    app.include_router(escalation_queue_router)
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
        """LLM conversation turn via OpenCode server. Returns {reply, history, escalated}."""
        opencode_url = os.environ.get("OPENCODE_SERVER_URL", "http://127.0.0.1:4096")

        # If the session is already escalated, short-circuit immediately
        session_meta = _opencode_sessions.get(body.conv_id, {})
        if session_meta.get("escalated"):
            return {
                "reply": "You are currently being connected to a human agent. Please hold.",
                "history": [m.model_dump() for m in body.history],
                "escalated": True,
            }

        # Resolve real business name and load all context items
        data_dir = active_settings.data_dir
        business_name = get_business_name(body.business_id, data_dir)
        context_text = load_business_context(body.business_id, data_dir)

        # Build escalation rules block for system prompt injection
        active_rules = list_active_rules(body.business_id)
        escalation_block = ""
        if active_rules:
            rules_lines = "\n".join(
                f"{i + 1}. {r.ai_refined_text or r.rule_text} [Priority: {r.priority}]"
                for i, r in enumerate(active_rules)
            )
            escalation_block = (
                "\n\nESCALATION RULES - IMPORTANT:\n"
                "When any of the following conditions is met, tell the caller naturally that "
                "a human agent will assist them and they should hold the line. "
                "Speak naturally — do NOT emit any XML or JSON tags.\n\n"
                f"Rules:\n{rules_lines}"
            )

        system_prompt = (
            f"You are a professional customer support agent for {business_name}.\n\n"
            f"Business Information:\n{context_text if context_text else 'No additional context provided.'}\n\n"
            "Guidelines:\n"
            "- You are on a phone call — be natural and conversational\n"
            "- Be helpful, polite, and concise (2-4 sentences per response)\n"
            f"- Always refer to the business as '{business_name}'"
            f"{escalation_block}"
        )

        # On first turn: return the hardcoded greeting immediately (fast, no LLM latency)
        if body.first_turn:
            _opencode_sessions[body.conv_id] = {"session_id": None, "escalated": False}
            greeting = f"Hello, this is {business_name}, how may I assist you today?"
            history = [{"role": "assistant", "content": greeting}]
            logger.info(
                "voice_chat_first_turn",
                extra={"conv_id": body.conv_id, "business_name": business_name},
            )
            return {"reply": greeting, "history": history, "escalated": False}

        async def _get_or_create_opencode_session() -> str:
            meta = _opencode_sessions.get(body.conv_id, {})
            existing_id = meta.get("session_id")
            async with httpx.AsyncClient(timeout=60.0) as c:
                if existing_id:
                    return existing_id
                resp = await c.post(
                    f"{opencode_url}/session",
                    json={"title": f"callsup-{body.conv_id}"},
                )
                resp.raise_for_status()
                session_id = resp.json()["id"]
                # Inject system prompt silently (no AI reply)
                await c.post(
                    f"{opencode_url}/session/{session_id}/message",
                    json={"noReply": True, "parts": [{"type": "text", "text": system_prompt}]},
                )
                _opencode_sessions.setdefault(body.conv_id, {})["session_id"] = session_id
                return session_id

        try:
            session_id = await _get_or_create_opencode_session()
            async with httpx.AsyncClient(timeout=60.0) as c:
                resp = await c.post(
                    f"{opencode_url}/session/{session_id}/message",
                    json={"parts": [{"type": "text", "text": body.message}]},
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error("voice_chat_opencode_http_error", extra={"status": exc.response.status_code, "error": str(exc)})
            raise HTTPException(status_code=502, detail=f"OpenCode error: {exc}") from exc
        except Exception as exc:
            logger.error("voice_chat_opencode_error", extra={"error": str(exc)})
            raise HTTPException(status_code=502, detail=f"OpenCode error: {exc}") from exc

        # Extract text reply from OpenCode response parts
        parts = data.get("parts") or []
        reply = " ".join(p.get("text", "") for p in parts if p.get("type") == "text").strip()
        if not reply:
            reply = data.get("info", {}).get("text", "")

        if not _opencode_sessions.get(body.conv_id):
            _opencode_sessions[body.conv_id] = {"session_id": session_id, "escalated": False}

        # ── Primary: tool-calling self-check via LLM adapter ────────────────────
        # Build conversation history up to (but not including) the assistant reply
        check_history = [m.model_dump() for m in body.history] + [
            {"role": "user", "content": body.message},
        ]
        tool_args = await _run_tool_decision(active_settings.llm_adapter_url, check_history, reply)

        if tool_args:
            reason = tool_args.get("reason") or "Escalation requested"
            priority = tool_args.get("priority", "medium")
            rule_triggered = tool_args.get("rule_triggered") or None

            ticket = create_ticket_internal(
                business_id=body.business_id,
                session_id=body.conv_id,
                reason=reason,
                priority=priority,
                rule_triggered=rule_triggered,
                conv_id=body.conv_id,
                conversation_history=check_history,
            )
            await broadcast_ticket(ticket.model_dump())
            _opencode_sessions[body.conv_id]["escalated"] = True

            clean_reply = re.sub(r"<escalate[^>]*/?>", "", reply).strip()
            if not clean_reply:
                clean_reply = "I've opened a support ticket for you. A human agent will be with you shortly — please hold the line."

            new_history = check_history + [{"role": "assistant", "content": clean_reply}]
            logger.info(
                "voice_chat_escalated",
                extra={"conv_id": body.conv_id, "reason": reason, "priority": priority},
            )
            return {"reply": clean_reply, "history": new_history, "escalated": True}

        # ── Fallback: XML marker detection (belt-and-suspenders) ─────────────────
        escalate_match = re.search(r"<escalate\s+([^/]+)/>", reply, re.IGNORECASE)
        if escalate_match:
            attrs_str = escalate_match.group(1)

            def _attr(name: str) -> str:
                m = re.search(rf"{name}=['\"]([^'\"]*)['\"]", attrs_str)
                return m.group(1) if m else ""

            reason = _attr("reason") or "Escalation requested"
            priority = _attr("priority") or "medium"
            if priority not in ("high", "medium", "low"):
                priority = "medium"
            rule_triggered = _attr("rule") or None

            ticket = create_ticket_internal(
                business_id=body.business_id,
                session_id=body.conv_id,
                reason=reason,
                priority=priority,
                rule_triggered=rule_triggered,
                conv_id=body.conv_id,
                conversation_history=check_history,
            )
            await broadcast_ticket(ticket.model_dump())
            _opencode_sessions[body.conv_id]["escalated"] = True

            escalation_reply = re.sub(r"<escalate[^>]*/?>", "", reply).strip()
            if not escalation_reply:
                escalation_reply = "I've opened a support ticket for you. A human agent will be with you shortly — please hold the line."

            new_history = check_history + [{"role": "assistant", "content": escalation_reply}]
            logger.info(
                "voice_chat_escalated_xml",
                extra={"conv_id": body.conv_id, "reason": reason, "priority": priority},
            )
            return {"reply": escalation_reply, "history": new_history, "escalated": True}

        # ── Non-escalated turn ────────────────────────────────────────────────────
        clean_reply = re.sub(r"<escalate[^>]*/?>", "", reply).strip()

        new_history = check_history + [{"role": "assistant", "content": clean_reply}]
        logger.info(
            "voice_chat_turn",
            extra={"conv_id": body.conv_id, "first_turn": False, "reply_len": len(clean_reply)},
        )
        return {"reply": clean_reply, "history": new_history, "escalated": False}

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

