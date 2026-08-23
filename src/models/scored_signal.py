from pydantic import BaseModel
from typing import Optional, Dict

class ScoredSignal(BaseModel):
    id: Optional[int] = None
    title: str
    url: str
    source: str
    score: float
    topic_fingerprint: str
    analysis: Dict
    is_top5: bool = False
    reported_at: Optional[float] = None