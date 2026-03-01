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

