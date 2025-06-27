from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel

class IndexStatus(BaseModel):
    """Model for tracking indexing status from Google Search Console"""
    site_url: str
    total_urls: int = 0
    indexed_urls: int = 0
    not_indexed_urls: int = 0
    crawled_urls: int = 0
    last_updated: datetime
    coverage_state: Dict[str, int] = {}  # Detailed coverage states and counts
    mobile_usability: Dict[str, int] = {}  # Mobile usability states
    errors: List[str] = []
    warnings: List[str] = []

class GSCData(BaseModel):
    """Model for Google Search Console data"""
    property_url: str
    clicks: int
    impressions: int
    ctr: float
    position: float
    date: datetime

class GSCQueryData(BaseModel):
    """Model for query-specific GSC data"""
    query: str
    clicks: int
    impressions: int
    ctr: float
    position: float
