# backend/models/page_data.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from pydantic import BaseModel, Field
from datetime import datetime

class KeywordAnalysis(BaseModel):
    """
    Defines keyword analysis data structure.
    """
    primary_keywords: List[str] = Field(default_factory=list, description="Primary keywords found in content")
    suggested_keywords: List[str] = Field(default_factory=list, description="AI-suggested keywords for better SEO")
    keyword_density: Dict[str, float] = Field(default_factory=dict, description="Keyword density percentages")
    missing_keywords: List[str] = Field(default_factory=list, description="Important keywords missing from content")
    competitor_keywords: List[str] = Field(default_factory=list, description="Keywords used by competitors")
    long_tail_suggestions: List[str] = Field(default_factory=list, description="Long-tail keyword suggestions")

class ContentSuggestions(BaseModel):
    """
    Detailed content improvement suggestions.
    """
    structure_improvements: List[str] = Field(default_factory=list, description="Content structure recommendations")
    readability_score: int = Field(0, description="Content readability score (0-100)")
    content_gaps: List[str] = Field(default_factory=list, description="Missing content topics")
    optimization_tips: List[str] = Field(default_factory=list, description="Specific optimization recommendations")

class TechnicalSEO(BaseModel):
    """
    Technical SEO recommendations.
    """
    schema_markup_suggestions: List[str] = Field(default_factory=list, description="Schema markup recommendations")
    performance_suggestions: List[str] = Field(default_factory=list, description="Performance optimization suggestions")
    accessibility_improvements: List[str] = Field(default_factory=list, description="Accessibility improvements")
    mobile_optimizations: List[str] = Field(default_factory=list, description="Mobile-specific optimizations")

class AISuggestions(BaseModel):
    """
    Enhanced structure for AI-generated SEO suggestions.
    """
    # Basic suggestions (existing)
    title: Optional[str] = Field(None, description="AI suggestion for the page title")
    description: Optional[str] = Field(None, alias="metaDescription", description="AI suggestion for the meta description")
    content: Optional[str] = Field(None, description="AI suggestion for the page content")
    
    # Enhanced suggestions
    title_alternatives: List[str] = Field(default_factory=list, description="Alternative title suggestions")
    description_alternatives: List[str] = Field(default_factory=list, description="Alternative meta description suggestions")
    
    # Keyword analysis
    keyword_analysis: Optional[KeywordAnalysis] = Field(None, description="Detailed keyword analysis")
    
    # Content suggestions
    content_suggestions: Optional[ContentSuggestions] = Field(None, description="Detailed content improvement suggestions")
    
    # Technical SEO
    technical_seo: Optional[TechnicalSEO] = Field(None, description="Technical SEO recommendations")
    
    # Priority and scores
    priority_score: int = Field(0, description="Priority score for implementing changes (1-10)")
    potential_impact: str = Field("medium", description="Potential impact of implementing suggestions (low/medium/high)")
    
    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="When suggestions were generated")
    confidence_score: float = Field(0.0, description="AI confidence in suggestions (0.0-1.0)")

class KeywordComparison(BaseModel):
    """
    Keyword comparison data structure for competitor analysis.
    """
    target_url: str = Field(..., description="URL being analyzed")
    competitor_urls: List[str] = Field(default_factory=list, description="Competitor URLs")
    shared_keywords: List[str] = Field(default_factory=list, description="Keywords shared with competitors")
    unique_opportunities: List[str] = Field(default_factory=list, description="Unique keyword opportunities")
    keyword_gaps: List[str] = Field(default_factory=list, description="Keywords competitors use but target doesn't")
    competitive_strength: Dict[str, float] = Field(default_factory=dict, description="Competitive strength by keyword")

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

class SearchEngineRanking(BaseModel):
    """
    Search engine ranking data for keywords.
    """
    keyword: str = Field(..., description="The keyword being tracked")
    google_rank: Optional[int] = Field(None, description="Google ranking position (1-100+)")
    bing_rank: Optional[int] = Field(None, description="Bing ranking position (1-100+)")
    mobile_rank: Optional[int] = Field(None, description="Mobile ranking position (1-100+)")
    search_volume: int = Field(0, description="Estimated monthly search volume")
    competition_level: str = Field("medium", description="Competition level (low/medium/high)")
    cpc_estimate: float = Field(0.0, description="Estimated cost per click")
    ranking_date: datetime = Field(default_factory=datetime.utcnow, description="When ranking was recorded")
    ranking_change: Optional[int] = Field(None, description="Change from previous ranking (+/- positions)")

class KeywordVolume(BaseModel):
    """
    Keyword search volume and competition data.
    """
    keyword: str = Field(..., description="The keyword")
    monthly_volume: int = Field(0, description="Estimated monthly search volume")
    volume_trend: str = Field("stable", description="Volume trend (growing/stable/declining)")
    competition_score: float = Field(0.5, description="Competition score (0.0-1.0)")
    difficulty_score: int = Field(50, description="SEO difficulty score (0-100)")
    related_keywords: List[str] = Field(default_factory=list, description="Related keyword suggestions")
    seasonal_data: Dict[str, int] = Field(default_factory=dict, description="Seasonal volume variations")

class KeywordRankingHistory(BaseModel):
    """
    Historical ranking data for a keyword.
    """
    keyword: str = Field(..., description="The keyword being tracked")
    url: str = Field(..., description="URL being tracked")
    rankings: List[SearchEngineRanking] = Field(default_factory=list, description="Historical rankings")
    best_ranking: Optional[int] = Field(None, description="Best ranking achieved")
    worst_ranking: Optional[int] = Field(None, description="Worst ranking recorded")
    average_ranking: float = Field(0.0, description="Average ranking over time")
    ranking_trend: str = Field("stable", description="Overall trend (improving/stable/declining)")
    tracking_start_date: datetime = Field(default_factory=datetime.utcnow, description="When tracking started")

class KeywordComparisonScore(BaseModel):
    """
    Detailed comparison between current and proposed keywords with scoring.
    """
    current_keyword: str = Field(..., description="Current keyword")
    proposed_keyword: str = Field(..., description="Proposed replacement keyword")
    
    # Volume comparison
    current_volume: int = Field(0, description="Current keyword search volume")
    proposed_volume: int = Field(0, description="Proposed keyword search volume")
    volume_improvement: float = Field(0.0, description="Volume improvement percentage")
    volume_score: int = Field(0, description="Volume improvement score (0-100)")
    
    # Competition comparison
    current_competition: float = Field(0.5, description="Current keyword competition (0.0-1.0)")
    proposed_competition: float = Field(0.5, description="Proposed keyword competition (0.0-1.0)")
    competition_improvement: float = Field(0.0, description="Competition improvement (negative is better)")
    competition_score: int = Field(0, description="Competition improvement score (0-100)")
    
    # Ranking potential
    current_difficulty: int = Field(50, description="Current keyword difficulty (0-100)")
    proposed_difficulty: int = Field(50, description="Proposed keyword difficulty (0-100)")
    difficulty_improvement: int = Field(0, description="Difficulty improvement")
    difficulty_score: int = Field(0, description="Difficulty improvement score (0-100)")
    
    # Relevance scoring
    content_relevance: int = Field(0, description="How well proposed keyword fits content (0-100)")
    user_intent_match: int = Field(0, description="User intent alignment score (0-100)")
    brand_alignment: int = Field(0, description="Brand/business alignment score (0-100)")
    
    # Overall scoring
    overall_score: int = Field(0, description="Overall improvement score (0-100)")
    recommendation: str = Field("neutral", description="Recommendation (strong_yes/yes/neutral/no/strong_no)")
    confidence_level: float = Field(0.0, description="Confidence in recommendation (0.0-1.0)")
    
    # Additional insights
    estimated_traffic_change: float = Field(0.0, description="Estimated traffic change percentage")
    implementation_effort: str = Field("medium", description="Implementation effort (low/medium/high)")
    expected_timeframe: str = Field("3-6 months", description="Expected time to see results")

class DomainKeywordProfile(BaseModel):
    """
    Comprehensive keyword profile for a domain.
    """
    domain: str = Field(..., description="Domain name")
    total_tracked_keywords: int = Field(0, description="Total keywords being tracked")
    keywords_ranking_top10: int = Field(0, description="Keywords ranking in top 10")
    keywords_ranking_top50: int = Field(0, description="Keywords ranking in top 50")
    total_search_volume: int = Field(0, description="Total estimated monthly search volume")
    average_ranking_position: float = Field(0.0, description="Average ranking across all keywords")
    keyword_distribution: Dict[str, int] = Field(default_factory=dict, description="Distribution by difficulty")
    top_performing_keywords: List[str] = Field(default_factory=list, description="Best performing keywords")
    improvement_opportunities: List[str] = Field(default_factory=list, description="Keywords with potential")
    competitive_gaps: List[str] = Field(default_factory=list, description="Competitor keywords to target")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last profile update")