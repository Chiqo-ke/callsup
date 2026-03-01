from __future__ import annotations

from datetime import datetime, timedelta, timezone

from callsup_intelligence_engine.api.schemas import StepRequest, TranscriptSegment
from callsup_intelligence_engine.core.conversation import ConversationService


async def run_e2e_demo(
    *,
    service: ConversationService,
    business_id: str,
    conv_id: str,
    audio_text: str,
) -> dict:
    ingest = {"audio_bytes": len(audio_text.encode("utf-8")), "status": "ingested"}
    asr_text = audio_text
    asr = {"text": asr_text, "confidence": 0.93}
    now = datetime.now(timezone.utc)
    segment = TranscriptSegment(
        business_id=business_id,
        conv_id=conv_id,
        segment_id="seg-e2e-1",
        speaker="customer",
        start_ts=now,
        end_ts=now + timedelta(seconds=2),
        text=asr_text,
        confidence=asr["confidence"],
    )
    step = await service.process_segment(
        StepRequest(
            business_id=business_id,
            conv_id=conv_id,
            segment=segment,
            session_state={},
        )
    )
    summary = await service.generate_summary(business_id=business_id, conv_id=conv_id)
    return {
        "ingest": ingest,
        "asr": asr,
        "nlu": {"intent": step.nlu_intent},
        "action": {"action_type": step.action_type, "response_text": step.response_text},
        "retrieval": {"context_source": "internal_knowledge"},
        "summary": summary,
    }
