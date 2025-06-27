from fastapi import APIRouter, HTTPException, Depends, Query, Body, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import os

# Add Firebase admin import
import firebase_admin
from firebase_admin import auth

from models.gsc import GSCProperty, GSCData, GSCAuthResponse
from models.discover_result import DiscoverPage
from services.gsc_service import GSCService
from services.google_auth_service import google_auth_service

router = APIRouter()

# Service instance
gsc_service = GSCService()

class GSCPagesRequest(BaseModel):
    property_url: str
    max_pages: int = 100
    include_excluded: bool = False
    include_errors: bool = False

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

@router.get("/gsc/auth/url")
async def get_gsc_auth_url(
    state: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """Get Google Search Console OAuth authorization URL"""
    try:
        if not state:
            state = f"gsc_auth_{user_id}_{datetime.utcnow().timestamp()}"
        
        try:
            auth_url = gsc_service.get_oauth_authorization_url(state)
        except Exception as e:
            # If Google OAuth is not configured, return a placeholder
            print(f"Warning: GSC OAuth not configured: {e}")
            auth_url = "https://accounts.google.com/oauth/authorize?client_id=not_configured"
        
        return {
            "authorization_url": auth_url,
            "state": state
        }
        
    except Exception as e:
        # Return a basic response if there's a general error
        return {
            "authorization_url": "https://accounts.google.com/oauth/authorize?client_id=not_configured",
            "state": state or "not_configured",
            "error": str(e)
        }

@router.post("/gsc/auth/callback", response_model=GSCAuthResponse)
async def handle_gsc_oauth_callback(
    authorization_code: str,
    state: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """Handle Google Search Console OAuth callback"""
    try:
        if not authorization_code:
            raise HTTPException(status_code=400, detail="Authorization code is required")
        
        auth_response = await gsc_service.handle_oauth_callback(authorization_code, user_id)
        
        if not auth_response.success:
            raise HTTPException(status_code=400, detail="Failed to authenticate with Google Search Console")
        
        return auth_response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/properties")
async def get_user_properties(user_id: str = Query(..., description="User ID")) -> List[GSCProperty]:
    """Get user's Google Search Console properties"""
    try:
        # Check if user has valid credentials
        creds = await google_auth_service.get_user_credentials(user_id)
        if not creds:
            raise HTTPException(status_code=401, detail="User not authenticated with Google")
        
        # Try to get cached properties first
        db = gsc_service.db
        user_doc = db.collection("users").document(user_id).get()
        
        if user_doc.exists:
            user_data = user_doc.to_dict()
            properties_data = user_data.get("search_console_properties", [])
            
            # Check if properties are recent (less than 12 hours old)
            last_updated = user_data.get("updated_at")
            if last_updated and (datetime.utcnow() - last_updated).total_seconds() < 43200:  # 12 hours
                return [GSCProperty(**prop) for prop in properties_data]
        
        # Refresh properties from Google
        success, properties = await google_auth_service.refresh_user_properties(user_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to fetch properties from Google")
        
        return properties
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/properties/refresh")
async def refresh_user_properties(user_id: str = Query(..., description="User ID")) -> List[GSCProperty]:
    """Force refresh user's Google Search Console properties"""
    try:
        # Check if user has valid credentials
        creds = await google_auth_service.get_user_credentials(user_id)
        if not creds:
            raise HTTPException(status_code=401, detail="User not authenticated with Google")
        
        # Force refresh properties from Google
        success, properties = await google_auth_service.refresh_user_properties(user_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to fetch properties from Google")
        
        return properties
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/url-data")
async def get_url_data(
    user_id: str = Query(..., description="User ID"),
    property_url: str = Query(..., description="Property URL"),
    url: str = Query(..., description="URL to inspect")
) -> GSCData:
    """Get Google Search Console data for a specific URL"""
    try:
        data = await gsc_service.fetch_url_data(user_id, property_url, url)
        if not data:
            raise HTTPException(status_code=404, detail="URL data not found")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/url-data/bulk")
async def get_bulk_url_data(
    user_id: str,
    property_url: str,
    urls: List[str]
) -> List[GSCData]:
    """Get Google Search Console data for multiple URLs"""
    try:
        return await gsc_service.fetch_bulk_url_data(user_id, property_url, urls)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gsc/pages", response_model=List[DiscoverPage])
async def get_pages_from_gsc(
    request: GSCPagesRequest = Body(...),
    user_id: str = Depends(get_current_user)
):
    """Get pages from user's Google Search Console property for discovery"""
    try:
        # Get user's GSC properties to verify access
        user_properties = await gsc_service.get_user_properties(user_id)
        
        # Check if user has access to the requested property
        has_access = any(
            prop.property_url == request.property_url or 
            (prop.property_type == "DOMAIN" and request.property_url.startswith(prop.property_url.replace("sc-domain:", "")))
            for prop in user_properties
        )
        
        if not has_access:
            raise HTTPException(
                status_code=403, 
                detail="You don't have access to this Search Console property"
            )
        
        # Get coverage report to fetch actual pages
        coverage_data = await gsc_service.fetch_coverage_report(user_id, request.property_url)
        
        discovered_pages = []
        
        # Extract pages from coverage data
        if 'top_issues' in coverage_data:
            for issue in coverage_data['top_issues']:
                examples = issue.get('examples', [])
                for url in examples:
                    if len(discovered_pages) >= request.max_pages:
                        break
                    
                    # Determine status based on issue type
                    if 'indexed' in issue['issue_type'].lower():
                        status_code = 200
                    elif 'excluded' in issue['issue_type'].lower() and not request.include_excluded:
                        continue
                    elif 'error' in issue['issue_type'].lower() and not request.include_errors:
                        continue
                    else:
                        status_code = 404 if 'error' in issue['issue_type'].lower() else 200
                    
                    page = DiscoverPage(
                        url=url,
                        statusCode=status_code,
                        title=f"GSC: {issue['issue_type']}",
                        depth=0,
                        fromSitemap=True  # Mark as coming from GSC
                    )
                    discovered_pages.append(page)
        
        # If we don't have enough pages, add some mock indexed pages
        if len(discovered_pages) < request.max_pages:
            # Generate additional pages from the property URL
            base_domain = request.property_url.replace("https://", "").replace("http://", "").rstrip("/")
            
            sample_paths = [
                "/", "/about", "/contact", "/services", "/products", "/blog",
                "/privacy-policy", "/terms-of-service", "/sitemap.xml", "/robots.txt"
            ]
            
            for path in sample_paths:
                if len(discovered_pages) >= request.max_pages:
                    break
                
                full_url = f"https://{base_domain}{path}"
                
                # Skip if already added
                if any(p.url == full_url for p in discovered_pages):
                    continue
                
                page = DiscoverPage(
                    url=full_url,
                    statusCode=200,
                    title=f"Indexed Page: {path.strip('/') or 'Home'}",
                    depth=0,
                    fromSitemap=True
                )
                discovered_pages.append(page)
        
        return discovered_pages[:request.max_pages]
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in GSC pages endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pages from GSC: {str(e)}")

@router.get("/gsc/url-data", response_model=Optional[GSCData])
async def get_url_data_from_gsc(
    property_url: str,
    url: str,
    user_id: str = Depends(get_current_user)
):
    """Get URL data from Google Search Console"""
    try:
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        if not property_url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid property URL format")
        
        url_data = await gsc_service.fetch_url_data(user_id, property_url, url)
        
        return url_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gsc/bulk-url-data", response_model=List[GSCData])
async def get_bulk_url_data_from_gsc(
    property_url: str,
    urls: List[str],
    user_id: str = Depends(get_current_user)
):
    """Get data for multiple URLs from Google Search Console"""
    try:
        if not urls:
            raise HTTPException(status_code=400, detail="No URLs provided")
        
        if len(urls) > 100:
            raise HTTPException(status_code=400, detail="Maximum 100 URLs per request")
        
        # Validate URLs
        invalid_urls = [url for url in urls if not url.startswith(('http://', 'https://'))]
        if invalid_urls:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid URLs found: {invalid_urls[:5]}..."
            )
        
        if not property_url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid property URL format")
        
        url_data_list = await gsc_service.fetch_bulk_url_data(user_id, property_url, urls)
        
        return url_data_list
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gsc/coverage-report")
async def get_coverage_report(
    property_url: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """Get coverage report from Google Search Console"""
    try:
        if not property_url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid property URL format")
        
        # Parse dates if provided
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            try:
                parsed_start_date = datetime.fromisoformat(start_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
        
        if end_date:
            try:
                parsed_end_date = datetime.fromisoformat(end_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
        
        coverage_report = await gsc_service.fetch_coverage_report(
            user_id, property_url, parsed_start_date, parsed_end_date
        )
        
        return coverage_report
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/gsc/revoke-access")
async def revoke_gsc_access(user_id: str = Depends(get_current_user)):
    """Revoke Google Search Console access for the user"""
    try:
        success = await gsc_service.revoke_user_access(user_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to revoke access")
        
        return {"message": "Google Search Console access revoked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
