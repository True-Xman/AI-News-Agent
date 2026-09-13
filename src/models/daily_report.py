from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DailyReport(BaseModel):
    generated_at: datetime
    signals: list[dict]
    rendered_message: str
    language: Literal["English"] = "English"
    generated_by: str = "AI Signal Scout"
