from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class Incident(BaseModel):
    monitor_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    reason: Optional[str] = None
