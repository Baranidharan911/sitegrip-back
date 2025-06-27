from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
# Import all API routers
from api import crawl as crawl_api
from api import history as history_api
from api import discover as discover_api
from api import export
from api import sitemap
from api import keywords
from api import ranking
from api import auth as auth_api
from api import monitor as monitor_api  # Add monitor router import
from db.firestore import initialize_firestore
import os
import json

# Firebase Admin SDK initialization
import firebase_admin
from firebase_admin import credentials

# Custom middleware to add CORS headers to redirects
class CORSRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add CORS headers to redirect responses
        if isinstance(response, RedirectResponse):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Expose-Headers"] = "*"
            print(f"Added CORS headers to redirect to: {response.headers.get('location')}")
        
        return response

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

# Add our custom middleware for redirects
app.add_middleware(CORSRedirectMiddleware)

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        # Check if Firebase is already initialized
        if firebase_admin._apps:
            print("Firebase Admin SDK already initialized")
            return
        
        # Try to get service account from environment variable first
        service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        
        if service_account_json:
            # Parse JSON from environment variable
            service_account_dict = json.loads(service_account_json)
            cred = credentials.Certificate(service_account_dict)
            print("Using Firebase credentials from environment variable")
        else:
            # Fall back to service account file
            service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'serviceAccountKey.json')
            if os.path.exists(service_account_file):
                cred = credentials.Certificate(service_account_file)
                print(f"Using Firebase credentials from file: {service_account_file}")
            else:
                print("Warning: No Firebase credentials found. Authentication will not work.")
                return
        
        firebase_admin.initialize_app(cred)
        print("Firebase Admin SDK initialized successfully")
        
    except Exception as e:
        print(f"Failed to initialize Firebase Admin SDK: {e}")
        print("Authentication will not work without proper Firebase configuration")

@app.on_event("startup")
async def startup_event():
    """
    Event handler for application startup.
    Initializes Firebase and Firestore connections.
    """
    print("Application starting up...")
    try:
        # Initialize Firebase Admin SDK first
        initialize_firebase()
        
        # Initialize Firestore
        initialize_firestore()
        print("Firestore initialized successfully")
        
    except Exception as e:
        print(f"Failed to initialize services on startup: {e}")
        print("Server will start with limited functionality")

# Include all routers in the application
app.include_router(monitor_api.router, prefix="/api")  # Add monitor router first
app.include_router(crawl_api.router, prefix="/api")
app.include_router(history_api.router, prefix="/api")
app.include_router(discover_api.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(sitemap.router, prefix="/api")
app.include_router(keywords.router, prefix="/api/keywords")
app.include_router(ranking.router, prefix="/api/ranking")
app.include_router(auth_api.router, prefix="/api/auth")

# Include indexing and quota management routers
from api import indexing as indexing_api
from api import quota as quota_api
from api import gsc as gsc_api
app.include_router(indexing_api.router, prefix="/api/indexing")
app.include_router(quota_api.router, prefix="/api")
app.include_router(gsc_api.router, prefix="/api/gsc")

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