from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict

class Monitor(BaseModel):
    id: Optional[str] = None
    url: str
    frequency: int = Field(5, description="Check interval in minutes")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_checked: Optional[datetime] = None
    last_status: Optional[str] = None  # "up" or "down"
    last_response_time: Optional[int] = None  # in ms
    uptime_stats: Dict[str, float] = Field(default_factory=dict)  # {"24h": 99.9, "7d": 98.7}
