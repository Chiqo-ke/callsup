from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from callsup_intelligence_engine import __version__
from callsup_intelligence_engine.api.schemas import StepRequest, StepResponse
from callsup_intelligence_engine.core.audit import (
    REDACTIONS_TOTAL,
    VERIFICATION_FAILURES_TOTAL,
    AuditStore,
)
from callsup_intelligence_engine.core.llm_adapter import LLMAdapterClient
from callsup_intelligence_engine.core.redaction import redact_pii
from callsup_intelligence_engine.core.verification import TransactionVerifier

logger = logging.getLogger("callsup.intelligence")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


@dataclass(slots=True)
class ConversationLogRecord:
    business_id: str
    conv_id: str
    segment_id: str
    speaker: str
    start_ts: str
    end_ts: str
    text_redacted: str
    asr_confidence: float
    nlu_intent: str
    action_taken: str
    module_version: str


class ConversationLogStore:
    def __init__(self) -> None:
        self._items: list[dict[str, Any]] = []

    def add(self, record: ConversationLogRecord) -> None:
        payload = asdict(record)
        payload["logged_at"] = datetime.now(timezone.utc).isoformat()
        self._items.append(payload)
        logger.info(json.dumps(payload))

    def list_by_conversation(self, business_id: str, conv_id: str) -> list[dict[str, Any]]:
        return [
            row
            for row in self._items
            if row["business_id"] == business_id and row["conv_id"] == conv_id
        ]


class ConversationService:
    def __init__(
        self,
        llm_client: LLMAdapterClient,
        audit_store: AuditStore,
        verifier: TransactionVerifier,
        logs: ConversationLogStore,
        *,
        model: str = "gpt-4.1-mini",
    ) -> None:
        self.llm_client = llm_client
        self.audit_store = audit_store
        self.verifier = verifier
        self.logs = logs
        self.model = model

    @staticmethod
    def infer_intent(text_redacted: str) -> str:
        lower = text_redacted.lower()
        if "balance" in lower:
            return "balance_inquiry"
        if "pay" in lower or "payment" in lower:
            return "payment"
        if "refund" in lower:
            return "refund_request"
        return "general_support"

    @staticmethod
    def retrieve_context(intent: str, business_id: str) -> str:
        kb = {
            "balance_inquiry": "Use secure account template output and never include sensitive IDs.",
            "payment": "Validate payment account and amount before customer response.",
            "refund_request": "Refunds are reviewed in 5 business days.",
            "general_support": "Provide concise assistance and ask follow-up if needed.",
        }
        return f"business={business_id}; guidance={kb.get(intent, kb['general_support'])}"

    async def process_segment(self, request: StepRequest) -> StepResponse:
        segment = request.segment
        redacted_text, redactions = redact_pii(segment.text)
        if redactions:
            REDACTIONS_TOTAL.inc(redactions)
        intent = self.infer_intent(redacted_text)
        retrieved = self.retrieve_context(intent, request.business_id)
        prompt = (
            f"intent={intent}\n"
            f"context={retrieved}\n"
            f"customer_text={redacted_text}\n"
            "For transactional intents return strict JSON."
        )
        llm = await self.llm_client.generate(prompt, self.model)
        self.audit_store.record(
            business_id=request.business_id,
            conv_id=request.conv_id,
            segment_id=segment.segment_id,
            model=self.model,
            prompt_redacted=prompt,
            usage=llm["usage"],
        )
        verification = self.verifier.verify_and_render(request.business_id, intent, llm["text"])
        escalate = False
        if not verification.ok:
            VERIFICATION_FAILURES_TOTAL.inc()
            escalate = True

        action_type = "transactional_response" if intent in {"balance_inquiry", "payment"} else "assist"
        response_text = (
            verification.response_text
            if verification.ok
            else "I need to connect you to an agent to complete this request safely."
        )
        log_record = ConversationLogRecord(
            business_id=request.business_id,
            conv_id=request.conv_id,
            segment_id=segment.segment_id,
            speaker=segment.speaker,
            start_ts=segment.start_ts.isoformat(),
            end_ts=segment.end_ts.isoformat(),
            text_redacted=redacted_text,
            asr_confidence=segment.confidence,
            nlu_intent=intent,
            action_taken=action_type,
            module_version=__version__,
        )
        self.logs.add(log_record)
        return StepResponse(
            action_type=action_type,
            response_text=response_text,
            tts=True,
            escalate=escalate,
            nlu_intent=intent,
            verification_passed=verification.ok,
            llm_usage=llm["usage"],
        )

    async def generate_summary(self, business_id: str, conv_id: str) -> dict[str, Any]:
        transcript = self.logs.list_by_conversation(business_id, conv_id)
        joined = "\n".join(item["text_redacted"] for item in transcript)
        prompt = (
            f"Generate concise call summary for business={business_id}, conv={conv_id}.\n"
            f"Transcript:\n{joined}"
        )
        llm = await self.llm_client.generate(prompt, self.model)
        self.audit_store.record(
            business_id=business_id,
            conv_id=conv_id,
            segment_id="summary",
            model=self.model,
            prompt_redacted=prompt,
            usage=llm["usage"],
        )
        return {"summary_text": llm["text"], "usage": llm["usage"], "redacted_transcript": transcript}
