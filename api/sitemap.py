from fastapi import APIRouter, HTTPException, Depends, Query, Header
from pydantic import BaseModel
from typing import Optional, List
from crawlers.utils import get_root_domain, parse_sitemap, get_sitemap_urls_from_robots
from urllib.parse import urlparse
from datetime import datetime
import os

# Add Firebase admin import
import firebase_admin
from firebase_admin import auth

from models.sitemap import SitemapEntry, SitemapSubmissionRequest, SitemapHistoryResponse, SitemapAnalytics
from services.sitemap_service import SitemapService

router = APIRouter()

# Service instance
sitemap_service = SitemapService()

# Real user authentication using Firebase tokens
async def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """Extract and validate Firebase ID token from Authorization header"""
    
    # Development/testing fallback - only when no authorization header is provided
    if not authorization:
        # Check if we're in development mode
        if os.getenv('ENVIRONMENT') == 'development' or os.getenv('TESTING') == 'true':
            print("Warning: Using development fallback authentication")
            return "dev_user_123"
        else:
            raise HTTPException(status_code=401, detail="Authorization header required")
    
    try:
        # Extract token from "Bearer <token>" format
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization format")
        
        token = authorization[7:]  # Remove "Bearer " prefix
        
        # Verify the Firebase ID token
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token.get("uid")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID")
        
        return user_id
        
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired ID token")
    except Exception as e:
        # In development, provide more detailed error info
        if os.getenv('ENVIRONMENT') == 'development':
            print(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

class SitemapRequest(BaseModel):
    url: str

def build_tree(urls):
    tree = {}
    for full_url in urls:
        parts = urlparse(full_url)
        path_parts = [p for p in parts.path.strip("/").split("/") if p]
        current = tree
        for part in path_parts:
            current = current.setdefault(part, {})
        current["_url"] = full_url
    return tree

def dict_to_nodes(tree_dict):
    def convert(subtree):
        url = subtree.pop("_url", None)
        children = [convert(child) for child in subtree.values()]
        return {"url": url or "", "children": children}
    return convert(tree_dict)

@router.post("/sitemap")
async def get_visual_sitemap(data: SitemapRequest):
    """Get visual sitemap structure (existing functionality)"""
    base_url = get_root_domain(data.url)
    robots_url = f"{base_url}/robots.txt"
    sitemap_urls = get_sitemap_urls_from_robots(robots_url)

    if not sitemap_urls:
        sitemap_urls = [f"{base_url}/sitemap.xml"]

    all_urls = set()
    for sitemap in sitemap_urls:
        parsed = parse_sitemap(sitemap)
        if parsed:
            all_urls.update(parsed)

    if not all_urls:
        raise HTTPException(status_code=404, detail="No sitemap found or sitemap is empty.")

    tree_dict = build_tree(all_urls)
    sitemap_tree = dict_to_nodes(tree_dict)
    return sitemap_tree

# New Google Search Console sitemap management endpoints

@router.post("/sitemap/submit", response_model=SitemapEntry)
async def submit_sitemap_to_gsc(
    request: SitemapSubmissionRequest,
    user_id: str = Depends(get_current_user)
):
    """Submit a sitemap to Google Search Console"""
    try:
        if not request.sitemap_url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid sitemap URL format")
        
        if not request.property_url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid property URL format")
        
        entry = await sitemap_service.submit_sitemap(
            user_id, request.property_url, request.sitemap_url
        )
        
        return entry
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sitemap/delete")
async def delete_sitemap_from_gsc(
    property_url: str,
    sitemap_url: str,
    user_id: str = Depends(get_current_user)
):
    """Delete a sitemap from Google Search Console"""
    try:
        if not sitemap_url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid sitemap URL format")
        
        if not property_url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid property URL format")
        
        result = await sitemap_service.delete_sitemap(user_id, property_url, sitemap_url)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sitemap/list")
async def get_sitemaps_from_gsc(
    property_url: str,
    user_id: str = Depends(get_current_user)
):
    """Get list of sitemaps from Google Search Console"""
    try:
        if not property_url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid property URL format")
        
        sitemaps = await sitemap_service.get_sitemaps_list(user_id, property_url)
        
        return {"sitemaps": sitemaps}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sitemap/discover")
async def discover_sitemaps(
    property_url: str,
    user_id: str = Depends(get_current_user)
):
    """Auto-discover sitemaps from robots.txt and common locations"""
    try:
        if not property_url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid property URL format")
        
        try:
            sitemap_urls = await sitemap_service.auto_discover_sitemaps(user_id, property_url)
        except Exception as e:
            # If discovery fails, return empty result rather than error
            print(f"Warning: Sitemap discovery failed for {property_url}: {e}")
            sitemap_urls = []
        
        return {
            "property_url": property_url,
            "discovered_sitemaps": sitemap_urls,
            "count": len(sitemap_urls)
        }
        
    except Exception as e:
        # Return empty discovery result if there's a general error
        return {
            "property_url": property_url,
            "discovered_sitemaps": [],
            "count": 0,
            "error": str(e)
        }

@router.get("/sitemap/history", response_model=SitemapHistoryResponse)
async def get_sitemap_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user)
):
    """Get sitemap submission history"""
    try:
        entries, total_count = await sitemap_service.get_sitemap_history(
            user_id, page, page_size
        )
        
        return SitemapHistoryResponse(
            entries=entries,
            total_count=total_count,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sitemap/sync")
async def trigger_sitemap_sync(
    user_id: str = Depends(get_current_user)
):
    """Manually trigger sitemap sync for user's sitemaps"""
    try:
        synced_count = await sitemap_service.sync_sitemaps_daily(user_id)
        
        return {
            "message": f"Synced {synced_count} sitemaps",
            "synced_count": synced_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
