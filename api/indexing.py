from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query, Header, Body
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import io
import os

# Add Firebase admin import
import firebase_admin
from firebase_admin import auth

from models.indexing_entry import (
    IndexingEntry, BulkIndexingRequest, IndexingStatsResponse, 
    IndexingHistoryResponse, IndexingPriority, IndexingAction, IndexingStatus
)
from services.indexer import IndexingService
from services.quota_service import QuotaService
from services.google_auth_service import google_auth_service
from pydantic import BaseModel

router = APIRouter()

# Service instances
indexing_service = IndexingService()
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

class SingleUrlRequest(BaseModel):
    url: str
    priority: Optional[IndexingPriority] = IndexingPriority.MEDIUM
    action: Optional[IndexingAction] = IndexingAction.URL_UPDATED

class BulkUrlRequest(BaseModel):
    urls: List[str]
    priority: Optional[IndexingPriority] = IndexingPriority.MEDIUM
    action: Optional[IndexingAction] = IndexingAction.URL_UPDATED

class IndexingResponse(BaseModel):
    success: bool
    message: str
    entries: List[Dict[str, Any]]
    total_submitted: int
    total_success: int
    total_failed: int

@router.post("/submit")
async def submit_urls(
    user_id: str = Query(..., description="User ID"),
    request: BulkUrlRequest = Body(...)
) -> IndexingResponse:
    """Submit URLs for indexing (supports both single and bulk submission)"""
    try:
        # Check if user has valid credentials
        creds = await google_auth_service.get_user_credentials(user_id)
        if not creds:
            raise HTTPException(status_code=401, detail="User not authenticated with Google")
        
        # Submit URLs using batch API
        entries = await indexing_service.submit_bulk_urls(
            user_id=user_id,
            urls=request.urls,
            priority=request.priority,
            action=request.action
        )
        
        # Calculate statistics
        total_success = sum(1 for e in entries if e.status == IndexingStatus.SUCCESS)
        total_failed = sum(1 for e in entries if e.status in [IndexingStatus.FAILED, IndexingStatus.QUOTA_EXCEEDED])
        
        # Convert entries to dict format
        entries_data = []
        for entry in entries:
            entries_data.append({
                "id": entry.id,
                "url": entry.url,
                "status": entry.status.value,
                "error": entry.error_message,
                "submitted_at": entry.submitted_at.isoformat() if entry.submitted_at else None,
                "completed_at": entry.completed_at.isoformat() if entry.completed_at else None
            })
        
        return IndexingResponse(
            success=True,
            message=f"Submitted {len(request.urls)} URLs for indexing",
            entries=entries_data,
            total_submitted=len(entries),
            total_success=total_success,
            total_failed=total_failed
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/submit/single")
async def submit_single_url(
    user_id: str = Query(..., description="User ID"),
    request: SingleUrlRequest = Body(...),

) -> Dict[str, Any]:
    """Submit a single URL for indexing"""
    try:
        # Check if user has valid credentials
        creds = await google_auth_service.get_user_credentials(user_id)
        if not creds:
            raise HTTPException(status_code=401, detail="User not authenticated with Google")
        
        entry = await indexing_service.submit_url(
            user_id=user_id,
            url=request.url,
            priority=request.priority,
            action=request.action
        )
        
        return {
            "success": entry.status == IndexingStatus.SUCCESS,
            "entry_id": entry.id,
            "status": entry.status.value,
            "error": entry.error_message,
            "message": f"URL submission {'successful' if entry.status == IndexingStatus.SUCCESS else 'failed'}",
            "url": entry.url,
            "google_response": entry.google_response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_indexing_history(
    user_id: str = Query(..., description="User ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[IndexingStatus] = None,
    domain: Optional[str] = None
) -> Dict[str, Any]:
    """Get indexing history for a user"""
    try:
        entries, total_count = await indexing_service.get_indexing_history(
            user_id=user_id,
            page=page,
            page_size=page_size,
            status_filter=status,
            domain_filter=domain
        )
        
        # Convert entries to dict format
        entries_data = []
        for entry in entries:
            entries_data.append({
                "id": entry.id,
                "url": entry.url,
                "domain": entry.domain,
                "status": entry.status.value,
                "priority": entry.priority.value if entry.priority else None,
                "action": entry.action.value if entry.action else None,
                "error_message": entry.error_message,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
                "submitted_at": entry.submitted_at.isoformat() if entry.submitted_at else None,
                "completed_at": entry.completed_at.isoformat() if entry.completed_at else None,
                "quota_used": entry.quota_used
            })
        
        return {
            "entries": entries_data,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_indexing_stats(
    user_id: str = Query(..., description="User ID"),
    days: int = Query(30, ge=1, le=365)
) -> Dict[str, Any]:
    """Get indexing statistics for a user"""
    try:
        stats = await indexing_service.get_indexing_stats(user_id, days)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/entry/{entry_id}")
async def delete_indexing_entry(
    entry_id: str,
    user_id: str = Query(..., description="User ID")
) -> Dict[str, Any]:
    """Delete an indexing entry"""
    try:
        success = await indexing_service.delete_indexing_entry(user_id, entry_id)
        if not success:
            raise HTTPException(status_code=404, detail="Entry not found or access denied")
        
        return {
            "success": True,
            "message": "Entry deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/indexing/entry/{entry_id}", response_model=IndexingEntry)
async def get_indexing_entry(
    entry_id: str,
    user_id: str = Depends(get_current_user)
):
    """Get details of a specific indexing entry"""
    try:
        # Get entry from database
        from db.firestore import get_or_create_firestore_client
        db = get_or_create_firestore_client()
        
        doc_ref = db.collection("indexing_entries").document(entry_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        data = doc.to_dict()
        data['id'] = entry_id
        
        # Verify ownership
        if data.get('user_id') != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return IndexingEntry(**data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/indexing/domains")
async def get_user_domains(user_id: str = Depends(get_current_user)):
    """Get all domains that have indexing entries for the user"""
    try:
        domains = await quota_service.get_user_domains(user_id)
        return {"domains": domains}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
