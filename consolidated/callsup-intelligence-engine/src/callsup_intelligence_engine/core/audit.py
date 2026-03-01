from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from prometheus_client import Counter

LLM_CALLS_TOTAL = Counter("callsup_llm_calls_total", "Total LLM calls")
REDACTIONS_TOTAL = Counter("callsup_redaction_events_total", "Total redaction events")
VERIFICATION_FAILURES_TOTAL = Counter(
    "callsup_verification_failures_total",
    "Total transactional verification failures",
)


@dataclass(slots=True)
class AuditRecord:
    timestamp: str
    business_id: str
    conv_id: str
    segment_id: str
    model: str
    prompt_redacted: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class AuditStore:
    def __init__(self) -> None:
        self._records: list[AuditRecord] = []
        self._lock = Lock()

    def record(
        self,
        business_id: str,
        conv_id: str,
        segment_id: str,
        model: str,
        prompt_redacted: str,
        usage: dict[str, int],
    ) -> AuditRecord:
        record = AuditRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            business_id=business_id,
            conv_id=conv_id,
            segment_id=segment_id,
            model=model,
            prompt_redacted=prompt_redacted,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        )
        with self._lock:
            self._records.append(record)
        LLM_CALLS_TOTAL.inc()
        return record

    def all_records(self) -> list[dict[str, Any]]:
        with self._lock:
            return [asdict(r) for r in self._records]
