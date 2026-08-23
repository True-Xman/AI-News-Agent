from pydantic import BaseModel
from typing import Optional

class RawSignal(BaseModel):
    url: str
    title: str
    source: str
    source_id: int
    found_at: float
    snippet: Optional[str] = None
    category: Optional[str] = None
    raw_text: Optional[str] = None
    filter_decision: Optional[str] = None
    filter_reason: Optional[str] = None
    filter_confidence: Optional[float] = None
    filter_scores: Optional[str] = None
    filter_processed_at: Optional[str] = None