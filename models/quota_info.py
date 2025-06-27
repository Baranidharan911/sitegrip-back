from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime, date as date_type

class QuotaInfo(BaseModel):
    """Model for tracking daily quota usage"""
    id: Optional[str] = Field(None, description="Unique identifier")
    domain: str = Field(..., description="Domain name")
    user_id: str = Field(..., description="User ID")
    date: str = Field(default_factory=lambda: date_type.today().isoformat(), description="Quota date (ISO format)")
    
    # Quota limits
    daily_limit: int = Field(200, description="Daily quota limit")
    priority_reserve: int = Field(50, description="Reserve for high/critical priority")
    
    # Usage tracking
    total_used: int = Field(0, description="Total quota used today")
    low_priority_used: int = Field(0, description="Quota used for low priority")
    medium_priority_used: int = Field(0, description="Quota used for medium priority")
    high_priority_used: int = Field(0, description="Quota used for high priority")
    critical_priority_used: int = Field(0, description="Quota used for critical priority")
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow(), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.utcnow(), description="Last update timestamp")
    
    @property
    def remaining_quota(self) -> int:
        """Calculate remaining quota"""
        return max(0, self.daily_limit - self.total_used)
    
    @property
    def priority_remaining(self) -> int:
        """Calculate remaining priority quota"""
        priority_used = self.high_priority_used + self.critical_priority_used
        return max(0, self.priority_reserve - priority_used)
    
    @property
    def can_submit_priority(self) -> bool:
        """Check if priority submissions are allowed"""
        return self.priority_remaining > 0
    
    @property
    def can_submit_regular(self) -> bool:
        """Check if regular submissions are allowed"""
        # Regular submissions can use non-priority quota
        non_priority_limit = self.daily_limit - self.priority_reserve
        non_priority_used = self.low_priority_used + self.medium_priority_used
        return non_priority_used < non_priority_limit and self.remaining_quota > 0

class QuotaUsageStats(BaseModel):
    """Model for quota usage statistics"""
    domain: str = Field(..., description="Domain name")
    date: str = Field(..., description="Date (ISO format)")
    daily_limit: int = Field(..., description="Daily limit")
    total_used: int = Field(..., description="Total used")
    remaining: int = Field(..., description="Remaining quota")
    usage_by_priority: Dict[str, int] = Field(..., description="Usage breakdown by priority")
    success_rate: float = Field(..., description="Success rate percentage")
