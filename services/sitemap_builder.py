from typing import List, Dict, Any
from models.page_data import PageData
from urllib.parse import urlparse

def build_visual_sitemap(pages: List[PageData]) -> Dict[str, Any]:
    """
    Converts a list of PageData into a graph-like structure of nodes and edges for visual sitemap.
    """
    nodes = []
    edges = []
    url_to_id = {}
    
    # Assign unique IDs to pages
    for i, page in enumerate(pages):
        url_to_id[page.url] = f"node{i}"
        parsed = urlparse(page.url)
        label = parsed.path or "/"
        nodes.append({
            "id": f"node{i}",
            "label": label,
            "url": page.url,
            "statusCode": page.status_code,
            "title": page.title or "(no title)",
        })

    # Create edges based on internal links
    for page in pages:
        source_id = url_to_id.get(page.url)
        if not source_id:
            continue

        for link in page.internal_links:
            target_id = url_to_id.get(link)
            if target_id:
                edges.append({
                    "from": source_id,
                    "to": target_id
                })

    return {
        "nodes": nodes,
        "edges": edges
    }
