import io
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import requests as _requests

from app.models import TranscriptSegment
from app.pii_redaction import redact_text

logger = logging.getLogger("callsup.transcription")

# Load .env if present (so OPENAI_API_KEY is available without env var export)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass


def mock_third_party_transcribe(redacted_payload: str) -> list[dict]:
    chunks = [chunk.strip() for chunk in redacted_payload.split(".") if chunk.strip()]
    if not chunks:
        chunks = ["Audio received and processed."]
    return [{"speaker": "customer", "text": item, "confidence": 0.95} for item in chunks]


def rapidapi_whisper_transcribe(audio_bytes: bytes) -> list[dict]:
    """Transcribe audio bytes using the RapidAPI Whisper speech-to-text service."""
    from app.config import get_settings

    settings = get_settings()
    api_key = settings.rapidapi_whisper_key or ""
    if not api_key:
        raise ValueError("CALLSUP_AUDIO_ENGINE_RAPIDAPI_WHISPER_KEY is not configured")

    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": settings.rapidapi_whisper_host,
    }
    params = {
        "lang": settings.rapidapi_whisper_lang,
        "task": "transcribe",
    }
    files = {"file": ("audio.wav", audio_bytes, "audio/wav")}

    response = _requests.post(
        settings.rapidapi_whisper_url,
        headers=headers,
        params=params,
        files=files,
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()

    # The API returns {"results": [{"transcript": "..."}]} or {"text": "..."}
    if isinstance(data, dict):
        if "results" in data and isinstance(data["results"], list):
            segments = []
            for item in data["results"]:
                text = (item.get("transcript") or item.get("text") or "").strip()
                if text:
                    segments.append({"speaker": "customer", "text": text, "confidence": 0.95})
            return segments or [{"speaker": "customer", "text": str(data), "confidence": 0.95}]
        if "text" in data:
            return [{"speaker": "customer", "text": data["text"].strip(), "confidence": 0.95}]
    return [{"speaker": "customer", "text": str(data), "confidence": 0.95}]


def whisper_transcribe(audio_bytes: bytes) -> list[dict]:
    """Transcribe audio bytes using OpenAI Whisper API."""
    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        logger.warning("openai package not installed — falling back to mock transcriber")
        return mock_third_party_transcribe(audio_bytes.decode("utf-8", errors="ignore"))

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-replace"):
        logger.warning("OPENAI_API_KEY not set — falling back to mock transcriber")
        return mock_third_party_transcribe(audio_bytes.decode("utf-8", errors="ignore"))

    client = OpenAI(api_key=api_key)
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.wav"  # OpenAI requires a filename hint
    response = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="verbose_json",
    )
    # verbose_json returns segments with timestamps when available
    if hasattr(response, "segments") and response.segments:
        return [
            {
                "speaker": "customer",
                "text": seg.get("text", "").strip() if isinstance(seg, dict) else seg.text.strip(),
                "confidence": seg.get("no_speech_prob", 0.95) if isinstance(seg, dict) else 0.95,
            }
            for seg in response.segments
            if (seg.get("text") if isinstance(seg, dict) else seg.text).strip()
        ] or [{"speaker": "customer", "text": response.text, "confidence": 0.95}]
    return [{"speaker": "customer", "text": response.text, "confidence": 0.95}]


def _select_transcriber(audio_bytes: bytes) -> list[dict]:
    """Use RapidAPI Whisper first, then OpenAI Whisper, then mock."""
    from app.config import get_settings

    settings = get_settings()

    if settings.rapidapi_whisper_key:
        logger.info("Using RapidAPI Whisper transcriber")
        try:
            return rapidapi_whisper_transcribe(audio_bytes)
        except Exception as exc:
            logger.warning("RapidAPI Whisper failed (%s) — falling back", exc)

    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key and not api_key.startswith("sk-replace"):
        logger.info("Using OpenAI Whisper transcriber")
        return whisper_transcribe(audio_bytes)

    logger.info("Using mock transcriber (configure a Whisper backend to enable real ASR)")
    decoded = audio_bytes.decode("utf-8", errors="ignore").strip()
    if not decoded:
        decoded = "Customer shared 555-555-5555 and test@example.com for follow up."
    return mock_third_party_transcribe(redact_text(decoded))


def transcribe_audio(
    business_id: str,
    conv_id: str,
    audio_bytes: bytes,
    *,
    third_party_transcriber=None,
) -> list[TranscriptSegment]:
    if third_party_transcriber is not None:
        # Allow injecting a custom transcriber (used in tests)
        raw_payload = audio_bytes.decode("utf-8", errors="ignore").strip()
        if not raw_payload:
            raw_payload = "Customer shared 555-555-5555 and test@example.com for follow up."
        redacted_payload = redact_text(raw_payload)
        rows = third_party_transcriber(redacted_payload)
    else:
        rows = _select_transcriber(audio_bytes)

    current = datetime.now(UTC)
    segments: list[TranscriptSegment] = []
    for row in rows:
        start = current
        end = current + timedelta(seconds=4)
        current = end
        segments.append(
            TranscriptSegment(
                business_id=business_id,
                conv_id=conv_id,
                segment_id=str(uuid4()),
                speaker=row.get("speaker"),
                start_ts=start,
                end_ts=end,
                text=row["text"],
                confidence=row.get("confidence"),
            )
        )
    return segments

