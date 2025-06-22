# backend/models/page_data.py
from pydantic import BaseModel, Field
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic import BaseModel, Field

class AISuggestions(BaseModel):
    """
    Defines the structure for AI-generated SEO suggestions.
    """
    title: Optional[str] = Field(None, description="AI suggestion for the page title.")
    description: Optional[str] = Field(None, alias="metaDescription", description="AI suggestion for the meta description.")
    content: Optional[str] = Field(None, description="AI suggestion for the page content.")


class PageData(BaseModel):
    """
    Defines the data structure for a single crawled page.
    """
    url: str
    title: Optional[str] = None
    meta_description: Optional[str] = Field(None, alias="metaDescription")
    word_count: int = Field(0, alias="wordCount")
    h1_count: int = Field(0, alias="h1Count")
    images_without_alt_count: int = Field(0, alias="imageWithoutAltCount")
    status_code: int = Field(..., alias="statusCode")
    internal_links: List[str] = Field([], alias="internalLinks")
    issues: List[str] = []
    linked_from: List[str] = Field(default_factory=list, alias="linkedFrom", description="List of pages that link to this one.")

    # mobile_screenshot: Optional[str] = Field(None, alias="mobileScreenshot")
    # desktop_screenshot: Optional[str] = Field(None, alias="desktopScreenshot")



    # Phase 2 Fields
    redirect_chain: List[str] = Field([], alias="redirectChain", description="List of URLs in a redirect chain, if any.")
    load_time: float = Field(0.0, alias="loadTime", description="Time taken to load the page in seconds.")
    page_size_bytes: int = Field(0, alias="pageSizeBytes", description="Total size of the page in bytes.")
    has_viewport: bool = Field(False, alias="hasViewport", description="Indicates if the page has a mobile viewport meta tag.")

    # Phase 3 Fields
    suggestions: Optional[AISuggestions] = None
    depth: int = Field(0, description="Crawl depth from root URL")

    # Temporary field for AI analysis, not stored in the database
    body_text: Optional[str] = Field(None, exclude=True)
    seo_score: int = Field(100, alias="seoScore")

    console_errors: List[str] = Field(default_factory=list, alias="consoleErrors")

    lcp: float = Field(0.0, alias="lcp")  # Largest Contentful Paint
    cls: float = Field(0.0, alias="cls")  # Cumulative Layout Shift
    ttfb: float = Field(0.0, alias="ttfb")  # Time to First Byte

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "url": "https://example.com/about",
                "title": "About Us",
                "metaDescription": "Learn more about our company.",
                "wordCount": 500,
                "h1Count": 1,
                "imageWithoutAltCount": 0,
                "statusCode": 200,
                "internalLinks": ["https://example.com/", "https://example.com/contact"],
                "issues": [],
                "redirectChain": [],
                "loadTime": 0.8,
                "pageSizeBytes": 150000,
                "hasViewport": True,
                "suggestions": {
                    "title": "Consider 'About Our Company | Example Inc.' for better branding.",
                    "description": "The meta description is good, but could be more engaging.",
                    "content": "The main content is well-written."
                }
            }
        }