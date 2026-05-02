from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class TranscriptSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str
    conv_id: str
    segment_id: str
    speaker: Literal["customer", "agent"] | None = None
    start_ts: datetime
    end_ts: datetime
    text: str
    confidence: float | None = None


class EscalationRule(BaseModel):
    id: str
    business_id: str
    rule_text: str
    ai_refined_text: str | None = None
    priority: Literal["high", "medium", "low"] = "medium"
    is_active: bool = True
    created_at: str
    updated_at: str


class EscalationTicket(BaseModel):
    id: str
    business_id: str
    conv_id: str | None = None
    session_id: str
    reason: str
    priority: Literal["high", "medium", "low"] = "medium"
    summary: str | None = None
    rule_triggered: str | None = None
    status: Literal["pending", "claimed", "resolved"] = "pending"
    created_at: str
    claimed_by: str | None = None
    resolved_at: str | None = None
    conversation_history: list[dict] = []

