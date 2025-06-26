from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class GSCCoverageStatus(str, Enum):
    """GSC Coverage status"""
    DISCOVERED = "discovered"
    CRAWLED = "crawled"
    INDEXED = "indexed"
    ERROR = "error"
    EXCLUDED = "excluded"

class GSCProperty(BaseModel):
    """Google Search Console property"""
    property_url: str = Field(..., description="Property URL")
    permission_level: str = Field("OWNER", description="Permission level")
    verified: bool = Field(True, description="Whether property is verified")

class GSCData(BaseModel):
    """GSC URL data"""
    url: str = Field(..., description="URL being analyzed")
    coverage_status: GSCCoverageStatus = Field(..., description="Coverage status")
    last_crawled: Optional[datetime] = Field(None, description="Last crawl date")
    discovered_date: Optional[datetime] = Field(None, description="Discovery date")
    indexing_state: Optional[str] = Field(None, description="Detailed indexing state")
    crawl_errors: List[str] = Field(default_factory=list, description="Crawl errors")
    mobile_usability_issues: List[str] = Field(default_factory=list, description="Mobile issues")
    page_experience_signals: Dict[str, Any] = Field(default_factory=dict, description="Page experience data")
    referring_urls: List[str] = Field(default_factory=list, description="Referring URLs")

class GSCAuthResponse(BaseModel):
    """GSC authentication response"""
    success: bool = Field(..., description="Whether auth was successful")
    properties: List[GSCProperty] = Field(default_factory=list, description="User's GSC properties")
    access_token: Optional[str] = Field(None, description="OAuth access token")
    expires_in: Optional[int] = Field(None, description="Token expiry in seconds") 