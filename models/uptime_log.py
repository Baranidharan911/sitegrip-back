from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UptimeLog(BaseModel):
    timestamp: datetime
    status: str  # "up" or "down"
    response_time: Optional[int]  # in ms
    error: Optional[str] = None
