"""
ASGI entry point for the FastAPI application.
This file is used by App Engine to properly run the FastAPI app.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import (
    auth, crawl, discover, export, gsc, history, 
    indexing, keywords, monitor, quota, ranking, 
    sitemap, monitoring
)

app = FastAPI(
    title="Indexing API",
    description="API for submitting URLs to Google's Indexing API",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(crawl.router, prefix="/crawl", tags=["Crawling"])
app.include_router(discover.router, prefix="/discover", tags=["Discovery"])
app.include_router(export.router, prefix="/export", tags=["Export"])
app.include_router(gsc.router, prefix="/gsc", tags=["Google Search Console"])
app.include_router(history.router, prefix="/history", tags=["History"])
app.include_router(indexing.router, prefix="/indexing", tags=["Indexing"])
app.include_router(keywords.router, prefix="/keywords", tags=["Keywords"])
app.include_router(monitor.router, prefix="/monitor", tags=["Monitoring"])
app.include_router(quota.router, prefix="/quota", tags=["Quota"])
app.include_router(ranking.router, prefix="/ranking", tags=["Ranking"])
app.include_router(sitemap.router, prefix="/sitemap", tags=["Sitemap"])
app.include_router(monitoring.router, prefix="/monitoring", tags=["Indexing Monitoring"])

@app.get("/")
async def root():
    return {"message": "Welcome to the Indexing API"}

# Export the app for ASGI servers
application = app

# For App Engine compatibility
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port) 