from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class TranscriptSegment(BaseModel):
    event: Literal["transcript.segment"] = "transcript.segment"
    business_id: str
    conv_id: str
    segment_id: str
    speaker: Literal["customer", "agent"]
    start_ts: datetime
    end_ts: datetime
    text: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class StepRequest(BaseModel):
    business_id: str
    conv_id: str
    segment: TranscriptSegment
    session_state: dict[str, Any] = Field(default_factory=dict)
    business_name: str = ""
    business_context: str = ""


class LLMUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class StepResponse(BaseModel):
    action_type: str
    response_text: str
    tts: bool = True
    escalate: bool = False
    nlu_intent: str
    verification_passed: bool = True
    llm_usage: LLMUsage


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, str]


class E2EDemoRequest(BaseModel):
    business_id: str
    conv_id: str
    audio_text: str


class E2EDemoResponse(BaseModel):
    stages: dict[str, Any]
    redacted_transcript: list[dict[str, Any]]
