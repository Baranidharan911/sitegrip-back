"""
Models for tracking and monitoring indexing status
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class IndexingMetrics(BaseModel):
    """Metrics for a single indexing request"""
    submission_time: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: Optional[int] = None
    queue_time_ms: Optional[int] = None
    google_api_latency_ms: Optional[int] = None
    batch_size: Optional[int] = None
    success_count: int = 0
    failed_count: int = 0
    quota_exceeded_count: int = 0
    error_details: Optional[Dict[str, Any]] = None

class IndexingProgress(BaseModel):
    """Progress tracking for a batch of URLs"""
    total_urls: int
    processed_urls: int = 0
    successful_urls: int = 0
    failed_urls: int = 0
    pending_urls: int = 0
    quota_exceeded_urls: int = 0
    start_time: datetime = Field(default_factory=datetime.utcnow)
    last_update: datetime = Field(default_factory=datetime.utcnow)
    estimated_completion: Optional[datetime] = None
    urls_per_second: float = 0.0
    remaining_time_seconds: Optional[int] = None

class IndexingError(BaseModel):
    """Detailed error information"""
    url: str
    error_code: str
    error_message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    retry_count: int = 0
    last_retry: Optional[datetime] = None
    next_retry: Optional[datetime] = None
    google_api_response: Optional[Dict[str, Any]] = None

class IndexingBatchStatus(BaseModel):
    """Status tracking for a batch indexing operation"""
    batch_id: str
    user_id: str
    domain: str
    total_urls: int
    priority: str
    action: str
    status: str  # QUEUED, PROCESSING, COMPLETED, FAILED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    progress: IndexingProgress
    metrics: IndexingMetrics
    errors: List[IndexingError] = []
    retry_strategy: str = "exponential_backoff"  # or "fixed_interval", "none"
    max_retries: int = 3
    notification_sent: bool = False

class IndexingMonitor(BaseModel):
    """Overall indexing monitoring for a user"""
    user_id: str
    domain: str
    active_batches: List[str] = []  # List of batch_ids
    completed_batches: List[str] = []
    failed_batches: List[str] = []
    total_urls_submitted: int = 0
    total_urls_indexed: int = 0
    total_urls_failed: int = 0
    total_quota_exceeded: int = 0
    last_successful_index: Optional[datetime] = None
    last_failed_index: Optional[datetime] = None
    average_success_rate: float = 0.0
    average_processing_time_ms: float = 0.0
    daily_quota_used: int = 0
    daily_quota_limit: int = 200
    daily_quota_reset: datetime = Field(default_factory=datetime.utcnow)
    alerts_enabled: bool = True
    alert_thresholds: Dict[str, Any] = {
        "success_rate": 80.0,  # Alert if below 80%
        "error_rate": 20.0,    # Alert if above 20%
        "quota_usage": 90.0,   # Alert at 90% quota usage
        "processing_time": 60000  # Alert if above 60 seconds
    } 