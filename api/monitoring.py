"""
API endpoints for indexing monitoring
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any

from models.indexing_monitor import IndexingBatchStatus, IndexingMonitor
from services.indexing_monitor_service import indexing_monitor_service
from api.auth import get_current_user

router = APIRouter(
    prefix="/monitoring",
    tags=["Monitoring"]
)

@router.get("/batches/active")
async def get_active_batches(
    user_id: str = Depends(get_current_user)
) -> List[IndexingBatchStatus]:
    """Get all active indexing batches for a user"""
    try:
        return await indexing_monitor_service.get_active_batches(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/batches/{batch_id}")
async def get_batch_status(
    batch_id: str,
    user_id: str = Depends(get_current_user)
) -> IndexingBatchStatus:
    """Get status of a specific batch operation"""
    try:
        batch = await indexing_monitor_service.get_batch_status(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        if batch.user_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        return batch
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/batches/history")
async def get_batch_history(
    user_id: str = Depends(get_current_user),
    domain: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100)
) -> List[IndexingBatchStatus]:
    """Get batch history for a user"""
    try:
        return await indexing_monitor_service.get_batch_history(
            user_id=user_id,
            domain=domain,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/domain/{domain}")
async def get_domain_monitor(
    domain: str,
    user_id: str = Depends(get_current_user)
) -> IndexingMonitor:
    """Get monitoring data for a specific domain"""
    try:
        monitor = await indexing_monitor_service.get_user_monitor(user_id, domain)
        if not monitor:
            raise HTTPException(status_code=404, detail="Monitor not found")
        return monitor
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/summary")
async def get_monitoring_summary(
    user_id: str = Depends(get_current_user),
    domain: Optional[str] = None
) -> Dict[str, Any]:
    """Get a summary of monitoring statistics"""
    try:
        # Get active batches
        active_batches = await indexing_monitor_service.get_active_batches(user_id)
        
        # Get recent history
        history = await indexing_monitor_service.get_batch_history(
            user_id=user_id,
            domain=domain,
            limit=10
        )
        
        # Get domain monitor if specified
        domain_monitor = None
        if domain:
            domain_monitor = await indexing_monitor_service.get_user_monitor(user_id, domain)
        
        return {
            "active_batches_count": len(active_batches),
            "active_batches": [
                {
                    "batch_id": batch.batch_id,
                    "domain": batch.domain,
                    "progress": {
                        "total": batch.total_urls,
                        "processed": batch.progress.processed_urls,
                        "successful": batch.progress.successful_urls,
                        "failed": batch.progress.failed_urls,
                        "pending": batch.progress.pending_urls
                    },
                    "status": batch.status,
                    "created_at": batch.created_at
                }
                for batch in active_batches
            ],
            "recent_history": [
                {
                    "batch_id": batch.batch_id,
                    "domain": batch.domain,
                    "total_urls": batch.total_urls,
                    "success_count": batch.metrics.success_count,
                    "failed_count": batch.metrics.failed_count,
                    "status": batch.status,
                    "completed_at": batch.completed_at
                }
                for batch in history
            ],
            "domain_stats": domain_monitor.dict() if domain_monitor else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 