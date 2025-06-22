from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from crawlers.utils import get_root_domain, parse_sitemap, get_sitemap_urls_from_robots
from urllib.parse import urlparse

router = APIRouter()

class SitemapRequest(BaseModel):
    url: str

def build_tree(urls):
    tree = {}
    for full_url in urls:
        parts = urlparse(full_url)
        path_parts = [p for p in parts.path.strip("/").split("/") if p]
        current = tree
        for part in path_parts:
            current = current.setdefault(part, {})
        current["_url"] = full_url
    return tree

def dict_to_nodes(tree_dict):
    def convert(subtree):
        url = subtree.pop("_url", None)
        children = [convert(child) for child in subtree.values()]
        return {"url": url or "", "children": children}
    return convert(tree_dict)

@router.post("/sitemap")
async def get_visual_sitemap(data: SitemapRequest):
    base_url = get_root_domain(data.url)
    robots_url = f"{base_url}/robots.txt"
    sitemap_urls = get_sitemap_urls_from_robots(robots_url)

    if not sitemap_urls:
        sitemap_urls = [f"{base_url}/sitemap.xml"]

    all_urls = set()
    for sitemap in sitemap_urls:
        parsed = parse_sitemap(sitemap)
        if parsed:
            all_urls.update(parsed)

    if not all_urls:
        raise HTTPException(status_code=404, detail="No sitemap found or sitemap is empty.")

    tree_dict = build_tree(all_urls)
    sitemap_tree = dict_to_nodes(tree_dict)
    return sitemap_tree
