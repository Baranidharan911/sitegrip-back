# api/discover.py
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel
import asyncio
import requests
from urllib.parse import urljoin, urlparse
from models.discover_result import DiscoverPage
from crawlers.utils import normalize_url, is_same_origin, get_root_domain, HEADERS
from bs4 import BeautifulSoup
from typing import List

router = APIRouter()

class DiscoverRequest(BaseModel):
    url: str
    depth: int = 2

@router.post("/discover", response_model=List[DiscoverPage])
async def discover_pages(request: DiscoverRequest = Body(...)):
    """
    Simplified discovery endpoint that works in App Engine.
    Uses basic HTTP requests instead of multiprocessing/Playwright.
    """
    try:
        discovered_pages = await discover_pages_simple(request.url, request.depth)
        return discovered_pages
    except Exception as e:
        print(f"Error in discover endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")

async def discover_pages_simple(base_url: str, max_depth: int) -> List[DiscoverPage]:
    """
    Simple page discovery using HTTP requests instead of Playwright.
    """
    discovered = set()
    to_crawl = [(base_url, 0)]  # (url, depth)
    results = []
    
    while to_crawl and len(results) < 50:  # Limit to prevent timeout
        url, depth = to_crawl.pop(0)
        
        if url in discovered or depth > max_depth:
            continue
            
        discovered.add(url)
        
        try:
            # Make HTTP request
            response = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
            
            # Create result
            page_result = DiscoverPage(
                url=response.url,  # Final URL after redirects
                statusCode=response.status_code,
                title=extract_title(response.content),
                depth=depth,
                fromSitemap=False  # We'll enhance this later
            )
            results.append(page_result)
            
            # Extract links if depth allows
            if depth < max_depth and response.status_code == 200:
                try:
                    links = extract_links(response.content, response.url, base_url)
                    for link in links[:20]:  # Limit links per page
                        if link not in discovered:
                            to_crawl.append((link, depth + 1))
                except Exception as e:
                    print(f"Error extracting links from {url}: {e}")
                    
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            # Still add to results with error status
            page_result = DiscoverPage(
                url=url,
                statusCode=0,  # Indicate connection error
                title="Connection Error",
                depth=depth,
                fromSitemap=False
            )
            results.append(page_result)
            
    return results

def extract_title(content: bytes) -> str:
    """Extract title from HTML content."""
    try:
        soup = BeautifulSoup(content, 'html.parser')
        title_tag = soup.find('title')
        return title_tag.get_text().strip() if title_tag else "No Title"
    except Exception:
        return "No Title"

def extract_links(content: bytes, base_url: str, origin_url: str) -> List[str]:
    """Extract internal links from HTML content."""
    try:
        soup = BeautifulSoup(content, 'html.parser')
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if not href or href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
                continue
                
            absolute_url = normalize_url(base_url, href)
            
            # Only include same-origin links
            if is_same_origin(origin_url, absolute_url):
                links.append(absolute_url)
                
        return list(set(links))  # Remove duplicates
    except Exception:
        return []
