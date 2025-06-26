from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional
from services.storage_uptime import uptime_storage
from models.monitor import Monitor
from models.uptime_log import UptimeLog
from datetime import datetime

router = APIRouter(tags=["Uptime Monitoring"])

# 🚀 Add a monitor
@router.post("/monitor", response_model=str)
def add_monitor(url: str = Body(...), frequency: int = Body(5)):
    try:
        monitor_id = uptime_storage.create_monitor(url, frequency)
        return monitor_id
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ❌ Delete a monitor
@router.delete("/monitor/{monitor_id}")
def delete_monitor(monitor_id: str):
    try:
        uptime_storage.delete_monitor(monitor_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 📊 Get current status of all monitors
@router.get("/monitor/status", response_model=List[Monitor])
def get_all_status():
    try:
        return uptime_storage.get_all_monitors()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 📜 Get logs for a monitor
@router.get("/monitor/{monitor_id}/history", response_model=List[UptimeLog])
def get_monitor_history(monitor_id: str, since_minutes: Optional[int] = 1440):
    try:
        return uptime_storage.get_logs(monitor_id, since_minutes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
