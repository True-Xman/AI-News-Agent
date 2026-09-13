from pydantic import BaseModel


class RawSignal(BaseModel):
    url: str
    title: str
    source: str
    source_id: int
    found_at: float
    snippet: str | None = None
    category: str | None = None
    raw_text: str | None = None
    filter_decision: str | None = None
    filter_reason: str | None = None
    filter_confidence: float | None = None
    filter_scores: str | None = None
    filter_processed_at: str | None = None
