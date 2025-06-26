"""
ASGI entry point for the FastAPI application.
This file is used by App Engine to properly run the FastAPI app.
"""

from main import app

# Export the app for ASGI servers
application = app

# For App Engine compatibility
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port) 