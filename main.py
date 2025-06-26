from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Import both of your API routers
from api import crawl as crawl_api
from api import history as history_api # <-- ADD THIS LINE
from db.firestore import initialize_firestore
from api import discover as discover_api
from api import export
from api import sitemap
from api import keywords
from api import ranking
from api import auth as auth_api
import os

app = FastAPI(
    title="SEO Crawler API",
    description="An API to crawl websites and analyze SEO metrics.",
    version="1.0.0"
)

# Updated CORS configuration for Cloud Run deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.sitegrip.com",
        "https://sitegrip.com",
        "http://localhost:3000",  # For local development
        "http://localhost:5173",  # For Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "*"  # Allow all origins for Cloud Run (you can restrict this later)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.on_event("startup")
async def startup_event():
    """
    Event handler for application startup.
    Initializes the Firestore connection.
    """
    print("Application starting up...")
    try:
        initialize_firestore()
        print("Firestore initialized successfully")
        
    except Exception as e:
        print(f"Failed to initialize services on startup: {e}")
        print("Server will start with limited functionality")

# Include both the crawl and history routers in the application
app.include_router(crawl_api.router, prefix="/api")
app.include_router(history_api.router, prefix="/api") # <-- ADD THIS LINE
app.include_router(discover_api.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(sitemap.router, prefix="/api")
app.include_router(keywords.router, prefix="/api/keywords")
app.include_router(ranking.router, prefix="/api/ranking")
app.include_router(auth_api.router, prefix="/api")

@app.get("/", tags=["Root"])
def read_root():
    """
    Root endpoint to check if the API is running.
    """
    return {"status": "ok", "message": "Welcome to the SEO Crawler API"}

@app.get("/health")
def health_check():
    """
    Health check endpoint for deployment monitoring
    """
    return {"status": "healthy", "service": "webwatch-api"}

@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """
    Handle OPTIONS requests for CORS preflight
    """
    return {"message": "OK"}

# This is required for App Engine
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)