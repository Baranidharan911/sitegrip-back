# api/discover.py
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel
from multiprocessing import Queue, get_context
import asyncio
from crawlers.process_crawler import discover_in_process
from models.discover_result import DiscoverPage

router = APIRouter()

class DiscoverRequest(BaseModel):
    url: str
    depth: int = 2

@router.post("/discover", response_model=list[DiscoverPage])
async def discover_pages(request: DiscoverRequest = Body(...)):
    ctx = get_context("spawn")
    queue = ctx.Queue()
    process = ctx.Process(target=discover_in_process, args=(queue, request.url, request.depth))

    try:
        process.start()
        result = await asyncio.wait_for(asyncio.to_thread(queue.get), timeout=280)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Discovery process timed out.")
    finally:
        if process.is_alive():
            process.terminate()
        process.join()

    if isinstance(result, Exception):
        raise HTTPException(status_code=500, detail=str(result))

    return result
