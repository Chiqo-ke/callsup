from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models import TranscriptSegment
from app.pii_redaction import redact_text


def mock_third_party_transcribe(redacted_payload: str) -> list[dict]:
    chunks = [chunk.strip() for chunk in redacted_payload.split(".") if chunk.strip()]
    if not chunks:
        chunks = ["Audio received and processed."]
    return [{"speaker": "customer", "text": item, "confidence": 0.95} for item in chunks]


def transcribe_audio(
    business_id: str,
    conv_id: str,
    audio_bytes: bytes,
    *,
    third_party_transcriber=mock_third_party_transcribe,
) -> list[TranscriptSegment]:
    raw_payload = audio_bytes.decode("utf-8", errors="ignore").strip()
    if not raw_payload:
        raw_payload = "Customer shared 555-555-5555 and test@example.com for follow up."
    redacted_payload = redact_text(raw_payload)
    rows = third_party_transcriber(redacted_payload)

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

