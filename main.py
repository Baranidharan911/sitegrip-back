from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Import both of your API routers
from api import crawl as crawl_api
from api import history as history_api # <-- ADD THIS LINE
from db.firestore import initialize_firestore
from api import discover as discover_api
from api import export
from api import sitemap

app = FastAPI(
    title="SEO Crawler API",
    description="An API to crawl websites and analyze SEO metrics.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    """
    Event handler for application startup.
    Initializes the Firestore connection.
    """
    print("Application starting up...")
    try:
        initialize_firestore()
    except Exception as e:
        print(f"Failed to initialize Firestore on startup: {e}")

# Include both the crawl and history routers in the application
app.include_router(crawl_api.router, prefix="/api")
app.include_router(history_api.router, prefix="/api") # <-- ADD THIS LINE
app.include_router(discover_api.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(sitemap.router, prefix="/api")

@app.get("/", tags=["Root"])
def read_root():
    """
    Root endpoint to check if the API is running.
    """
    return {"status": "ok", "message": "Welcome to the SEO Crawler API"}