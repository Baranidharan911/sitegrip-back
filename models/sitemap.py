from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class SitemapStatus(str, Enum):
    """Status of sitemap submission"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    SUCCESS = "success"
    ERROR = "error"
    DELETED = "deleted"

class SitemapEntry(BaseModel):
    """Individual sitemap entry"""
    id: Optional[str] = Field(None, description="Unique identifier")
    sitemap_url: str = Field(..., description="URL of the sitemap")
    status: SitemapStatus = Field(SitemapStatus.PENDING, description="Current status")
    domain: str = Field(..., description="Domain the sitemap belongs to")
    auto_sync: bool = Field(False, description="Whether to auto-sync this sitemap")
    urls_count: int = Field(0, description="Number of URLs in the sitemap")
    project_id: str = Field(..., description="Project ID")
    user_id: str = Field(..., description="User ID")
    submitted_at: datetime = Field(default_factory=datetime.utcnow, description="When submitted")
    last_synced_at: Optional[datetime] = Field(None, description="Last sync time")
    error_message: Optional[str] = Field(None, description="Error message if failed")

class IndexingHistory(BaseModel):
    """Historical record of actions"""
    id: Optional[str] = Field(None, description="Unique identifier")
    action_type: str = Field(..., description="Type of action performed")
    target_url: str = Field(..., description="URL the action was performed on")
    status: str = Field(..., description="Status of the action")
    user_id: str = Field(..., description="User who performed the action")
    project_id: str = Field(..., description="Project ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When action occurred")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")

class IndexingResponse(BaseModel):
    """Generic response model for operations"""
    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Human-readable message")
    errors: Optional[List[str]] = Field(None, description="List of errors if any")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional response data") 