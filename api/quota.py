from fastapi import APIRouter, HTTPException, Depends, Query, Header
from typing import Optional, List
from datetime import date
import os

# Add Firebase admin import
import firebase_admin
from firebase_admin import auth

from models.quota_info import QuotaInfo, QuotaUsageStats
from services.quota_service import QuotaService

router = APIRouter()

# Service instance
quota_service = QuotaService()

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

@router.get("/quota/{domain}", response_model=QuotaInfo)
async def get_domain_quota(
    domain: str,
    target_date: Optional[str] = None,
    user_id: str = Depends(get_current_user)
):
    """Get quota information for a specific domain"""
    try:
        parsed_date = None
        if target_date:
            try:
                parsed_date = date.fromisoformat(target_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        quota_info = await quota_service.get_quota_info(user_id, domain, parsed_date)
        return quota_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/quota/{domain}/limits")
async def set_domain_limits(
    domain: str,
    daily_limit: int,
    priority_reserve: int,
    user_id: str = Depends(get_current_user)
):
    """Set custom quota limits for a domain"""
    try:
        if daily_limit < 1 or daily_limit > 10000:
            raise HTTPException(
                status_code=400, 
                detail="Daily limit must be between 1 and 10000"
            )
        
        if priority_reserve < 0 or priority_reserve > daily_limit:
            raise HTTPException(
                status_code=400, 
                detail="Priority reserve must be between 0 and daily limit"
            )
        
        success = await quota_service.set_domain_limits(
            user_id, domain, daily_limit, priority_reserve
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update quota limits")
        
        return {
            "message": "Quota limits updated successfully",
            "domain": domain,
            "daily_limit": daily_limit,
            "priority_reserve": priority_reserve
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/quota/{domain}/stats", response_model=List[QuotaUsageStats])
async def get_quota_stats(
    domain: str,
    days: int = Query(7, ge=1, le=30),
    user_id: str = Depends(get_current_user)
):
    """Get quota usage statistics for a domain over the last N days"""
    try:
        stats = await quota_service.get_quota_stats(user_id, domain, days)
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/quota/domains")
async def get_all_domains(user_id: str = Depends(get_current_user)):
    """Get all domains with quota information for the user"""
    try:
        domains = await quota_service.get_user_domains(user_id)
        
        # Get current quota info for each domain
        domain_quotas = []
        for domain in domains:
            quota_info = await quota_service.get_quota_info(user_id, domain)
            domain_quotas.append({
                "domain": domain,
                "daily_limit": quota_info.daily_limit,
                "total_used": quota_info.total_used,
                "remaining": quota_info.remaining_quota,
                "priority_remaining": quota_info.priority_remaining
            })
        
        return {"domains": domain_quotas}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quota/check")
async def check_quota_availability(
    url: str,
    priority: str = "medium",
    user_id: str = Depends(get_current_user)
):
    """Check if quota is available for a URL submission"""
    try:
        from models.indexing_entry import IndexingPriority
        
        # Validate priority
        try:
            priority_enum = IndexingPriority(priority)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Invalid priority. Must be one of: low, medium, high, critical"
            )
        
        available, message = await quota_service.check_quota_availability(
            user_id, url, priority_enum
        )
        
        return {
            "available": available,
            "message": message,
            "url": url,
            "priority": priority
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/quota/summary")
async def get_quota_summary(user_id: str = Depends(get_current_user)):
    """Get a summary of quota usage across all domains"""
    try:
        domains = await quota_service.get_user_domains(user_id)
        
        # If no domains found, return empty summary quickly
        if not domains:
            return {
                "total_limits": 0,
                "total_used": 0,
                "total_remaining": 0,
                "overall_usage_percentage": 0,
                "domains": [],
                "domain_count": 0
            }
        
        total_limits = 0
        total_used = 0
        total_remaining = 0
        domain_summaries = []
        
        # Limit to first 10 domains to prevent timeouts
        for domain in domains[:10]:
            try:
                quota_info = await quota_service.get_quota_info(user_id, domain)
                
                total_limits += quota_info.daily_limit
                total_used += quota_info.total_used
                total_remaining += quota_info.remaining_quota
                
                domain_summaries.append({
                    "domain": domain,
                    "daily_limit": quota_info.daily_limit,
                    "used": quota_info.total_used,
                    "remaining": quota_info.remaining_quota,
                    "usage_percentage": (quota_info.total_used / quota_info.daily_limit) * 100 if quota_info.daily_limit > 0 else 0
                })
            except Exception as e:
                # If individual domain fails, skip it but continue
                print(f"Error getting quota for domain {domain}: {e}")
                continue
        
        return {
            "total_limits": total_limits,
            "total_used": total_used,
            "total_remaining": total_remaining,
            "overall_usage_percentage": (total_used / total_limits) * 100 if total_limits > 0 else 0,
            "domains": domain_summaries,
            "domain_count": len(domains)
        }
        
    except Exception as e:
        # Return a basic response if there's a general error
        return {
            "total_limits": 0,
            "total_used": 0,
            "total_remaining": 0,
            "overall_usage_percentage": 0,
            "domains": [],
            "domain_count": 0,
            "error": str(e)
        }
