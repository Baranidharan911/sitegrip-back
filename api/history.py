# backend/api/history.py
from fastapi import APIRouter, HTTPException
from typing import List
from services.storage import storage_service
from models.crawl_result import CrawlResult

router = APIRouter()

@router.get("/history", response_model=List[CrawlResult], tags=["History"])
async def get_crawl_history():
    """
    Retrieves a list of all past crawl results, ordered by most recent.
    """
    try:
        # This function already exists in our storage service
        history = storage_service.get_all_crawls()
        return history
    except Exception as e:
        # Log the error for debugging
        print(f"Error fetching crawl history from storage: {e}")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while trying to retrieve the crawl history."
        )