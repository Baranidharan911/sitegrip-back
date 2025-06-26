# backend/api/history.py
from fastapi import APIRouter, HTTPException, Query
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

@router.get("/history/user/{user_id}", response_model=List[CrawlResult], tags=["History"])
async def get_user_crawl_history(user_id: str):
    """
    Retrieves crawl history for a specific user.
    """
    try:
        history = storage_service.get_crawls_by_user(user_id)
        return history
    except Exception as e:
        print(f"Error fetching user crawl history for {user_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while retrieving user crawl history."
        )

@router.get("/history/crawl/{crawl_id}", response_model=CrawlResult, tags=["History"])
async def get_crawl_by_id(crawl_id: str):
    """
    Retrieves a specific crawl by its ID.
    """
    try:
        crawl = storage_service.get_crawl_by_id(crawl_id)
        if not crawl:
            raise HTTPException(status_code=404, detail=f"Crawl not found: {crawl_id}")
        return crawl
    except Exception as e:
        print(f"Error fetching crawl {crawl_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while fetching the crawl data."
        )

@router.delete("/history/crawl/{crawl_id}", tags=["History"])
async def delete_crawl(crawl_id: str):
    """
    Deletes a specific crawl by its ID.
    """
    try:
        success = storage_service.delete_crawl(crawl_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Crawl not found: {crawl_id}")
        return {"success": True, "message": f"Crawl {crawl_id} deleted successfully"}
    except Exception as e:
        print(f"Error deleting crawl {crawl_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while deleting the crawl."
        )

@router.get("/history/latest", response_model=CrawlResult, tags=["History"])
async def get_latest_crawl_for_url(url: str = Query(..., description="The URL to get the latest crawl for")):
    """
    Retrieves the most recent completed crawl result for a specific URL.
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required.")
    try:
        latest_crawl = storage_service.get_latest_crawl_by_url(url)
        if not latest_crawl:
            raise HTTPException(status_code=404, detail=f"No completed crawl found for URL: {url}")
        return latest_crawl
    except Exception as e:
        print(f"Error fetching latest crawl for {url}: {e}")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while fetching the latest crawl data."
        )