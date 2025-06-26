# backend/models/crawl_result.py

from pydantic import BaseModel, Field
from typing import List, Optional, Set
from datetime import datetime
from .page_data import PageData

class CrawlSummary(BaseModel):
    total_pages: int = Field(..., alias="totalPages")
    missing_titles: int = Field(..., alias="missingTitles")
    low_word_count_pages: int = Field(..., alias="lowWordCountPages")
    broken_links: int = Field(..., alias="brokenLinks")
    duplicate_titles: int = Field(..., alias="duplicateTitles")
    duplicate_descriptions: int = Field(..., alias="duplicateDescriptions")

    redirect_chains: int = Field(0, alias="redirectChains")
    mobile_friendly_pages: int = Field(0, alias="mobileFriendlyPages")
    non_mobile_pages: int = Field(0, alias="nonMobilePages")
    pages_with_slow_load: int = Field(0, alias="pagesWithSlowLoad")
    orphan_pages: int = Field(0, alias="orphanPages")
    average_seo_score: int = Field(100, alias="averageSeoScore")

class CrawlResult(BaseModel):
    crawl_id: str = Field(..., alias="crawlId")
    url: str
    depth: int
    crawled_at: datetime = Field(default_factory=datetime.utcnow, alias="crawledAt")
    user_id: Optional[str] = Field(None, alias="userId")
    summary: CrawlSummary
    pages: List[PageData]
    sitemap_urls: Set[str] = Field(default_factory=set, alias="sitemapUrls")
    ai_summary_text: Optional[str] = Field(None, alias="aiSummaryText")  # ✅ NEW FIELD

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            set: list
        }
