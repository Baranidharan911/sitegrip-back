from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum

class IndexingPriority(str, Enum):
    """Indexing priority levels"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"

class IndexingStatus(str, Enum):
    """Indexing request status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    QUOTA_EXCEEDED = "quota_exceeded"

class IndexingAction(str, Enum):
    """Indexing action type"""
    URL_UPDATED = "URL_UPDATED"
    URL_DELETED = "URL_DELETED"

class IndexingEntry(BaseModel):
    """Model for URL indexing entries"""
    id: Optional[str] = Field(None, description="Unique identifier")
    url: str = Field(..., description="URL to be indexed")
    domain: str = Field(..., description="Domain of the URL")
    user_id: str = Field(..., description="User who submitted the request")
    priority: IndexingPriority = Field(IndexingPriority.MEDIUM, description="Indexing priority")
    action: IndexingAction = Field(IndexingAction.URL_UPDATED, description="Indexing action")
    status: IndexingStatus = Field(IndexingStatus.PENDING, description="Current status")
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    submitted_at: Optional[datetime] = Field(None, description="Submission timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    # Google API response data
    google_response: Optional[Dict[str, Any]] = Field(None, description="Google API response")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(0, description="Number of retry attempts")
    max_retries: int = Field(3, description="Maximum retry attempts")
    
    # Quota tracking
    quota_used: bool = Field(False, description="Whether quota was consumed")
    
    class Config:
        use_enum_values = True

class BulkIndexingRequest(BaseModel):
    """Model for bulk indexing requests"""
    urls: List[str] = Field(..., description="List of URLs to index")
    priority: IndexingPriority = Field(IndexingPriority.MEDIUM, description="Priority for all URLs")
    action: IndexingAction = Field(IndexingAction.URL_UPDATED, description="Action for all URLs")

class IndexingStatsResponse(BaseModel):
    """Model for indexing statistics response"""
    total_submitted: int = Field(..., description="Total URLs submitted")
    pending: int = Field(..., description="Pending URLs")
    success: int = Field(..., description="Successfully indexed URLs")
    failed: int = Field(..., description="Failed URLs")
    quota_used: int = Field(..., description="Quota consumed")
    quota_remaining: int = Field(..., description="Quota remaining")
    success_rate: float = Field(..., description="Success rate percentage")
    
class IndexingHistoryResponse(BaseModel):
    """Model for indexing history response"""
    entries: List[IndexingEntry] = Field(..., description="List of indexing entries")
    total_count: int = Field(..., description="Total number of entries")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
