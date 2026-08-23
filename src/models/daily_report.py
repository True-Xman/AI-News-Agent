from pydantic import BaseModel
from datetime import datetime
from typing import List

class DailyReport(BaseModel):
    date: datetime
    top5_signals: List[str]
    summary: str
    attached_reports: List[str]
    generated_by: str = "AI Signal Scout"