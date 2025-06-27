from fastapi import APIRouter, HTTPException, Body, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import HttpUrl
from services.storage_uptime import uptime_storage
from services.uptime_checker import uptime_checker
from models.monitor import Monitor, AlertConfig
from models.uptime_log import UptimeLog

router = APIRouter(tags=["Uptime Monitoring"])

# 🚀 Add a monitor
@router.post("/monitor", response_model=str)
async def add_monitor(
    url: HttpUrl = Body(...),
    name: Optional[str] = Body(None),
    frequency: int = Body(5, ge=1, le=10),
    alerts: Optional[AlertConfig] = Body(None),
    is_public: bool = Body(False)
):
    """Add a new URL to monitor.
    - frequency: Check interval in minutes (1, 5, or 10)
    - alerts: Optional email/webhook configuration
    - is_public: Whether to show on public status page
    """
    try:
        monitor_id = uptime_storage.create_monitor(
            url=str(url),
            name=name,
            frequency=frequency,
            alerts=alerts,
            is_public=is_public
        )
        
        # Perform initial check
        result = await uptime_checker.check(str(url))
        uptime_storage.update_monitor_status(
            monitor_id,
            result.status,
            result.response_time,
            result.http_status,
            result.timestamp
        )
        
        return monitor_id
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🔄 Update a monitor
@router.put("/monitor/{monitor_id}")
async def update_monitor(
    monitor_id: str,
    name: Optional[str] = Body(None),
    frequency: Optional[int] = Body(None, ge=1, le=10),
    alerts: Optional[AlertConfig] = Body(None),
    is_public: Optional[bool] = Body(None)
):
    """Update monitor configuration"""
    try:
        updates = {}
        if name is not None:
            updates["name"] = name
        if frequency is not None:
            updates["frequency"] = frequency
        if alerts is not None:
            updates["alerts"] = alerts.dict()
        if is_public is not None:
            updates["is_public"] = is_public
            
        uptime_storage.update_monitor(monitor_id, **updates)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ❌ Delete a monitor
@router.delete("/monitor/{monitor_id}")
async def delete_monitor(monitor_id: str):
    """Delete a monitor"""
    try:
        uptime_storage.delete_monitor(monitor_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 📊 Get current status of all monitors
@router.get("/monitor/status", response_model=List[Monitor])
async def get_all_status():
    """Get current status of all monitors"""
    try:
        return uptime_storage.get_all_monitors()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 📜 Get logs for a monitor
@router.get("/monitor/{monitor_id}/history", response_model=List[UptimeLog])
async def get_monitor_history(
    monitor_id: str,
    hours: Optional[int] = Query(24, ge=1, le=720)
):
    """Get historical logs for a monitor"""
    try:
        return uptime_storage.get_logs(monitor_id, since_minutes=hours * 60)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🌐 Get public status page data
@router.get("/status/public", response_model=List[Monitor])
async def get_public_status():
    """Get status of all public monitors for status page"""
    try:
        return uptime_storage.get_public_monitors()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🔍 Get detailed monitor stats
@router.get("/monitor/{monitor_id}/stats")
async def get_monitor_stats(monitor_id: str) -> Dict[str, Any]:
    """Get detailed statistics for a monitor"""
    try:
        monitor = uptime_storage.get_monitor(monitor_id)
        if not monitor:
            raise HTTPException(status_code=404, detail="Monitor not found")
            
        # Get recent logs
        logs = uptime_storage.get_logs(monitor_id, since_minutes=1440)  # Last 24h
        
        # Calculate response time stats
        response_times = [log.response_time for log in logs if log.response_time is not None]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Get current incident if any
        current_incident = None
        incidents = uptime_storage.get_active_incidents(monitor_id)
        if incidents:
            current_incident = incidents[0].dict()
            
        return {
            "monitor": monitor.dict(),
            "stats": {
                "uptime": monitor.uptime_stats,
                "average_response_time": round(avg_response_time, 2),
                "total_checks": len(logs),
                "current_incident": current_incident
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
