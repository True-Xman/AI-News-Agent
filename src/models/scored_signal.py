from typing import Optional

from pydantic import BaseModel

from ..intelligence.contracts import ScoreBreakdown


class ScoredSignal(BaseModel):
    id: Optional[int] = None
    url_hash: str
    title: str
    url: str
    organization: str
    score: float
    score_breakdown: ScoreBreakdown
    what_happened: str
    why_it_matters: str
    plain_english_explanation: str
    x_discussion_angle: str
    found_at: float
