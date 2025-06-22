import json
from bs4 import BeautifulSoup
from typing import List

# ✅ List of common schema.org types we care about
COMMON_SCHEMA_TYPES = {
    "Article", "BlogPosting", "Product", "FAQPage", "Recipe",
    "Event", "LocalBusiness", "Organization", "Person", "Review",
    "BreadcrumbList", "HowTo", "VideoObject", "NewsArticle"
}

def extract_schema_from_html(html: str) -> bool:
    """
    Checks if the HTML contains valid structured data via <script type="application/ld+json">
    Returns True if any valid schema.org @type is found.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        script_tags = soup.find_all("script", {"type": "application/ld+json"})
        
        for tag in script_tags:
            try:
                # Some tags may contain arrays or single objects
                data = json.loads(tag.string or "")
                entries = data if isinstance(data, list) else [data]
                
                for entry in entries:
                    if isinstance(entry, dict) and "@type" in entry:
                        type_val = entry["@type"]
                        # Type may be a string or list of types
                        if isinstance(type_val, str) and type_val in COMMON_SCHEMA_TYPES:
                            return True
                        elif isinstance(type_val, list):
                            if any(t in COMMON_SCHEMA_TYPES for t in type_val):
                                return True
            except json.JSONDecodeError:
                continue  # Skip malformed JSON
    except Exception as e:
        print(f"[schema analyzer] Error parsing schema: {e}")
    
    return False
