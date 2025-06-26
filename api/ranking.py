"""
Ranking & Advanced Keyword API

Provides endpoints for keyword ranking, volume, history, domain profiling,
and scored keyword comparisons.
"""

from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import BaseModel
from typing import List, Optional

from services.ranking_service import ranking_service
from services.keyword_comparison_service import keyword_comparison_service
from models.page_data import KeywordRankingHistory, KeywordVolume, DomainKeywordProfile, KeywordComparisonScore, SearchEngineRanking

router = APIRouter()

class KeywordTrackingRequest(BaseModel):
    keyword: str
    url: str
    domain: str

class KeywordComparisonRequest(BaseModel):
    current_keyword: str
    proposed_keyword: str
    page_content: Optional[str] = None

@router.post("/track", response_model=SearchEngineRanking)
async def track_keyword(request: KeywordTrackingRequest):
    """
    Track a keyword's ranking for a specific URL and domain.
    This will generate a new ranking data point.
    """
    try:
        ranking = ranking_service.track_keyword_ranking(
            keyword=request.keyword,
            url=request.url,
            domain=request.domain
        )
        return ranking
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track keyword: {str(e)}")

@router.get("/volume/{keyword}", response_model=KeywordVolume)
async def get_keyword_volume(keyword: str):
    """
    Get estimated search volume and competition data for a keyword.
    """
    try:
        volume_data = ranking_service.get_keyword_volume_data(keyword)
        return volume_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get volume data: {str(e)}")

@router.get("/history", response_model=KeywordRankingHistory)
async def get_ranking_history(
    keyword: str = Query(..., description="The keyword to get history for"),
    url: str = Query(..., description="The URL the keyword is tracked for"),
    days: int = Query(30, ge=7, le=365, description="Number of days to look back")
):
    """
    Get the ranking history for a keyword on a specific URL.
    """
    try:
        history = ranking_service.get_ranking_history(keyword, url, days)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ranking history: {str(e)}")

@router.get("/domain-profile/{domain}", response_model=DomainKeywordProfile)
async def get_domain_keyword_profile(domain: str):
    """
    Get a comprehensive keyword profile for an entire domain.
    """
    try:
        profile = ranking_service.get_domain_profile(domain)
        return profile
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get domain profile: {str(e)}")

@router.post("/compare-score", response_model=KeywordComparisonScore)
async def compare_keywords_with_score(request: KeywordComparisonRequest):
    """
    Compare a current keyword with a proposed one and get a detailed score.
    """
    try:
        comparison_score = await keyword_comparison_service.compare_and_score(
            current_keyword=request.current_keyword,
            proposed_keyword=request.proposed_keyword,
            page_content=request.page_content
        )
        return comparison_score
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare keywords: {str(e)}") 