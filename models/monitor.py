from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import Optional, Dict, List

class AlertConfig(BaseModel):
    email: Optional[str] = None
    webhook: Optional[HttpUrl] = None
    threshold: int = Field(2, description="Number of failures before alerting")

class Monitor(BaseModel):
    id: Optional[str] = None
    url: HttpUrl
    name: Optional[str] = None
    frequency: int = Field(5, description="Check interval in minutes", ge=1, le=10)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_checked: Optional[datetime] = None
    last_status: Optional[str] = None  # "up" or "down"
    last_response_time: Optional[int] = None  # in ms
    http_status: Optional[int] = None  # Last HTTP status code
    failures_in_a_row: int = Field(default=0, description="Number of consecutive failures")
    uptime_stats: Dict[str, float] = Field(
        default_factory=lambda: {"24h": 100.0, "7d": 100.0, "30d": 100.0}
    )
    alerts: Optional[AlertConfig] = None
    is_public: bool = Field(default=False, description="Whether monitor is visible on public status page")
