# backend/crawlers/process_crawler.py
import asyncio
from multiprocessing import Queue
from crawlers.crawler import SiteCrawler
from models.discover_result import DiscoverPage

def crawl_in_process(queue: Queue, url: str, depth: int):
    """
    This function is designed to be run in a separate, isolated process.
    It initializes its own asyncio event loop and runs the Playwright crawler.
    The result is put into the provided multiprocessing.Queue.
    """
    try:
        result = asyncio.run(run_crawl(url, depth))
        queue.put(result)
    except Exception as e:
        print(f"Exception in crawl process: {e}")
        queue.put(e)

async def run_crawl(url: str, depth: int):
    """Helper async function to instantiate and run the crawler."""
    crawler = SiteCrawler(base_url=url, depth=depth)
    pages, sitemap_urls = await crawler.crawl_site()
    # Convert Pydantic models to dicts to send them across the process boundary.
    pages_as_dicts = [page.dict(by_alias=True) for page in pages]
    return {"pages": pages_as_dicts, "sitemap_urls": list(sitemap_urls)}

def discover_in_process(queue: Queue, url: str, depth: int):
    """
    This function runs a lightweight site discovery crawl in a separate process.
    It skips AI and analysis — only returns basic info like URL, status, title.
    """
    try:
        result = asyncio.run(discover_lightweight(url, depth))
        queue.put(result)
    except Exception as e:
        print(f"Exception in discover process: {e}")
        queue.put(e)

async def discover_lightweight(url: str, depth: int):
    """
    Runs the crawler and returns a simplified result for discovery.
    """
    crawler = SiteCrawler(base_url=url, depth=depth)
    pages, sitemap_urls = await crawler.crawl_site()

    # Convert to lightweight format (DiscoverPage)
    discover_pages = []
    for page in pages:
        discover_pages.append({
            "url": page.url,
            "statusCode": page.status_code,
            "title": page.title,
            "depth": 0,  # You can enhance this to reflect actual depth later
            "fromSitemap": page.url in sitemap_urls
        })

    return discover_pages