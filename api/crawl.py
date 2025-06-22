# backend/api/crawl.py

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
import uuid
import multiprocessing
import asyncio
from typing import List, Optional

from crawlers.process_crawler import crawl_in_process
from services.ai_summary import ai_summary_service 
from models.page_data import PageData
from analyzers.analyzer import SEOAnalyzer
from analyzers.summarizer import summarizer_service
from services.storage import storage_service
from models.crawl_result import CrawlResult
from ai.ai import ai_service

router = APIRouter()

class CrawlRequest(BaseModel):
    url: str
    depth: int = 1
    selectedUrls: Optional[List[str]] = None  # ✅ NEW FIELD

@router.post("/crawl", response_model=CrawlResult)
async def trigger_crawl(request: CrawlRequest = Body(...)):
    """
    Initiates a full crawl:
    - Launches a subprocess to crawl pages
    - Optionally filters by selectedUrls
    - Analyzes and uses AI to suggest improvements
    - Saves final result to Firestore
    """
    if not (request.url.startswith("http://") or request.url.startswith("https://")):
        raise HTTPException(status_code=400, detail="Invalid URL. Must start with http:// or https://")

    ctx = multiprocessing.get_context("spawn")
    queue = ctx.Queue()

    process = ctx.Process(
        target=crawl_in_process,
        args=(queue, request.url, request.depth)
    )

    try:
        process.start()
        crawl_process_result = await asyncio.wait_for(
            asyncio.to_thread(queue.get),
            timeout=900.0  # 5-minute timeout
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Crawl process timed out after 5 minutes.")
    finally:
        if process.is_alive():
            process.terminate()
        process.join()

    if isinstance(crawl_process_result, Exception):
        print(f"Crawl process failed: {crawl_process_result}")
        raise HTTPException(status_code=500, detail=str(crawl_process_result))

    raw_pages_data_dicts = crawl_process_result.get("pages", [])
    sitemap_urls = set(crawl_process_result.get("sitemap_urls", []))

    if not raw_pages_data_dicts:
        raise HTTPException(status_code=404, detail="No pages were crawled.")

    # Convert to PageData objects
    all_pages = [PageData(**data) for data in raw_pages_data_dicts]

    # ✅ Filter by selectedUrls (if given)
    if request.selectedUrls:
        selected_set = set(request.selectedUrls)
        filtered_pages = [page for page in all_pages if page.url in selected_set]
    else:
        filtered_pages = all_pages

    if not filtered_pages:
        raise HTTPException(status_code=400, detail="None of the selected URLs matched the crawled data.")

    analyzer = SEOAnalyzer(all_pages_data=filtered_pages)
    analyzed_pages = analyzer.run_analysis()

    suggestions = await ai_service.analyze_batch(analyzed_pages)
    for i, page in enumerate(analyzed_pages):
        page.suggestions = suggestions[i]

    crawled_urls = {page.url for page in analyzed_pages}
    summary = summarizer_service.generate_summary(analyzed_pages, sitemap_urls, crawled_urls)
    ai_summary_text = await ai_summary_service.summarize_crawl(analyzed_pages)

    crawl_id = str(uuid.uuid4())
    result = CrawlResult(
        crawlId=crawl_id,
        url=request.url,
        depth=request.depth,
        summary=summary,
        pages=analyzed_pages,
        sitemapUrls=sitemap_urls,
        aiSummaryText=ai_summary_text,
    )

    storage_service.save_crawl_result(result)
    return result
