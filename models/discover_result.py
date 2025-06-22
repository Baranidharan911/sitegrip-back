# models/discover_result.py
from pydantic import BaseModel
from typing import Optional

class DiscoverPage(BaseModel):
    url: str
    statusCode: int
    title: Optional[str] = None
    depth: int
    fromSitemap: bool
