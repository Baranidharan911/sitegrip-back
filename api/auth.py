import datetime
from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel
from typing import Optional

import firebase_admin
from firebase_admin import auth

from db.firestore import get_or_create_firestore_client
from models.user import User, GoogleCredentials, SearchConsoleProperty
from services.google_auth_service import google_auth_service

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

# ========== Request Models ==========

class TokenVerificationRequest(BaseModel):
    idToken: str

class GoogleTokenVerificationRequest(BaseModel):
    idToken: str
    googleAccessToken: Optional[str] = None
    googleRefreshToken: Optional[str] = None

class GoogleCallbackRequest(BaseModel):
    code: str
    state: str  # user_id

class UserResponse(BaseModel):
    uid: str
    email: str | None = None
    display_name: str | None = None
    photo_url: str | None = None

# ========== Routes ==========

@router.post("/verify-token", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def verify_token(payload: TokenVerificationRequest = Body(...)):
    """Verify Firebase token and update Firestore user."""
    try:
        decoded_token = auth.verify_id_token(payload.idToken)
        uid = decoded_token["uid"]
        db = get_or_create_firestore_client()
        user_ref = db.collection("users").document(uid)
        user_doc = user_ref.get()

        if user_doc.exists:
            user_ref.update({"last_login_at": datetime.datetime.utcnow()})
            user_data = user_doc.to_dict()
            return UserResponse(**user_data)
        else:
            firebase_user = auth.get_user(uid)
            new_user = User(
                uid=uid,
                email=firebase_user.email,
                display_name=firebase_user.display_name,
                photo_url=firebase_user.photo_url,
                last_login_at=datetime.datetime.utcnow()
            )
            user_ref.set(new_user.dict())
            return UserResponse(**new_user.dict())
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired ID token.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.post("/verify-token-with-google")
async def verify_firebase_token_with_google_auth(request: GoogleTokenVerificationRequest):
    """Verify Firebase token and optionally store Google credentials."""
    try:
        decoded_token = auth.verify_id_token(request.idToken)
        uid = decoded_token["uid"]
        email = decoded_token.get("email", "")
        name = decoded_token.get("name", "")
        picture = decoded_token.get("picture", "")
        db = get_or_create_firestore_client()

        user_data = {
            "uid": uid,
            "email": email,
            "display_name": name,
            "photo_url": picture,
            "last_login_at": datetime.datetime.utcnow()
        }

        if request.googleAccessToken:
            google_creds = GoogleCredentials(
                access_token=request.googleAccessToken,
                refresh_token=request.googleRefreshToken,
                client_id=google_auth_service.client_id,
                client_secret=google_auth_service.client_secret,
                scopes=[
                    "https://www.googleapis.com/auth/webmasters.readonly",
                    "https://www.googleapis.com/auth/webmasters"
                ],
                expiry=datetime.datetime.utcnow()  # Temporary
            )
            user_data["google_credentials"] = google_creds.dict()

            try:
                properties = await google_auth_service._fetch_search_console_properties(google_creds)
                user_data["search_console_properties"] = [prop.dict() for prop in properties]
            except Exception as e:
                print(f"[⚠️] Search Console fetch error: {e}")
                user_data["search_console_properties"] = []

        user_ref = db.collection("users").document(uid)
        if user_ref.get().exists:
            user_ref.update(user_data)
        else:
            user_data["created_at"] = datetime.datetime.utcnow()
            user_ref.set(user_data)

        return {
            "success": True,
            "uid": uid,
            "email": email,
            "display_name": name,
            "photo_url": picture,
            "google_auth_enabled": bool(request.googleAccessToken),
            "google_integration": bool(request.googleAccessToken),
            "message": "Authentication successful with Google API access" if request.googleAccessToken else "Authentication successful"
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Verification failed: {str(e)}")

@router.post("/google/callback")
async def handle_google_callback(request: GoogleCallbackRequest):
    """Exchange code for tokens and store credentials in Firestore."""
    try:
        result = await google_auth_service.exchange_code_for_tokens(request.code, request.state)
        if result.get("success"):
            return {
                "success": True,
                "user": {
                    "uid": request.state,
                    "google_auth_enabled": True,
                    "search_console_properties": result.get("properties", [])
                },
                "message": "Authentication successful with Google API access"
            }
        else:
            return {
                "success": False,
                "message": result.get("error", "Unknown error during Google callback")
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Callback error: {str(e)}")

@router.get("/google/url")
async def get_google_oauth_url(user_id: str):
    """Generate Google OAuth URL for login flow."""
    try:
        url = await google_auth_service.get_auth_url(user_id)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate URL: {str(e)}")

@router.get("/google/status")
async def check_google_auth_status(user_id: str):
    """Check if user is authenticated with Google and has valid credentials."""
    try:
        creds = await google_auth_service.get_user_credentials(user_id)
        if creds:
            return {"authenticated": True, "message": "User is authenticated with Google APIs"}
        return {"authenticated": False, "message": "User needs to authenticate with Google"}
    except Exception as e:
        return {"authenticated": False, "message": f"Auth check failed: {e}"}

@router.get("/user/{user_id}")
async def get_user_profile(user_id: str):
    """Fetch Firestore-stored user profile info."""
    try:
        db = get_or_create_firestore_client()
        user_doc = db.collection("users").document(user_id).get()
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        user_data = user_doc.to_dict()
        return {
            "success": True,
            "uid": user_data.get("uid"),
            "email": user_data.get("email"),
            "display_name": user_data.get("display_name"),
            "photo_url": user_data.get("photo_url"),
            "google_auth_enabled": bool(user_data.get("google_credentials")),
            "search_console_properties": user_data.get("search_console_properties", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
