from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class SitemapStatus(str, Enum):
    """Sitemap submission status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    SUCCESS = "success"
    FAILED = "failed"
    DELETED = "deleted"

class SitemapEntry(BaseModel):
    """Model for sitemap entries"""
    id: Optional[str] = Field(None, description="Unique identifier")
    sitemap_url: str = Field(..., description="Sitemap URL")
    property_url: str = Field(..., description="Property URL in GSC")
    domain: str = Field(..., description="Domain of the property")
    user_id: str = Field(..., description="User who submitted the sitemap")
    status: SitemapStatus = Field(SitemapStatus.PENDING, description="Current status")
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow(), description="Creation timestamp")
    submitted_at: Optional[datetime] = Field(None, description="Submission timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    last_synced: Optional[datetime] = Field(None, description="Last sync timestamp")
    last_analyzed: Optional[datetime] = Field(None, description="Last content analysis timestamp")
    
    # Google response data
    google_response: Optional[Dict[str, Any]] = Field(None, description="Google GSC response")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Sitemap analysis
    content_analyzed: bool = Field(False, description="Whether content has been analyzed")
    is_sitemap_index: bool = Field(False, description="Whether this is a sitemap index")
    url_count: int = Field(0, description="Number of URLs in sitemap")
    urls_sample: List[str] = Field(default_factory=list, description="Sample of URLs from sitemap")
    
    # Configuration
    auto_sync: bool = Field(True, description="Whether to auto-sync daily")
    
    class Config:
        use_enum_values = True

class SitemapSubmissionRequest(BaseModel):
    """Model for sitemap submission requests"""
    property_url: str = Field(..., description="Property URL in GSC")
    sitemap_url: str = Field(..., description="Sitemap URL to submit")
    auto_sync: bool = Field(True, description="Enable daily auto-sync")

class SitemapHistoryResponse(BaseModel):
    """Model for sitemap history response"""
    entries: List[SitemapEntry] = Field(..., description="List of sitemap entries")
    total_count: int = Field(..., description="Total number of entries")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")

class IndexingHistory(BaseModel):
    """Historical record of actions"""
    id: Optional[str] = Field(None, description="Unique identifier")
    action_type: str = Field(..., description="Type of action performed")
    target_url: str = Field(..., description="URL the action was performed on")
    status: str = Field(..., description="Status of the action")
    user_id: str = Field(..., description="User who performed the action")
    project_id: str = Field(..., description="Project ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow(), description="When action occurred")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")

class SitemapAnalytics(BaseModel):
    """Analytics data for sitemap performance"""
    total_urls: int = Field(0, description="Total URLs in sitemap")
    indexed_urls: int = Field(0, description="Number of indexed URLs")
    indexing_rate: float = Field(0.0, description="Percentage of URLs indexed")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    coverage_issues: List[str] = Field(default_factory=list, description="Coverage issues found")
    crawl_errors: List[str] = Field(default_factory=list, description="Crawl errors found")

class IndexingResponse(BaseModel):
    """Generic response model for operations"""
    success: bool = Field(..., description="Whether operation was successful")
    message: str = Field(..., description="Human-readable message")
    errors: Optional[List[str]] = Field(None, description="List of errors if any")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional response data") 