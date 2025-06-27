import datetime
from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any

import firebase_admin
from firebase_admin import auth

from db.firestore import get_or_create_firestore_client
from models.user import User, GoogleCredentials, SearchConsoleProperty
from services.google_auth_service import google_auth_service
from services.user_initialization import user_initialization_service

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

class AuthResponse(BaseModel):
    success: bool
    message: str
    uid: Optional[str] = None
    email: Optional[str] = None
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    google_auth_enabled: bool = False
    database_status: str = "unknown"
    error: Optional[str] = None

def get_database_status(db) -> str:
    """Check database connection and return status"""
    try:
        # Check if it's a mock client
        if hasattr(db, 'collections') and isinstance(db.collections, dict):
            return "mock_client_active"
        
        # Try to perform a test write and read
        test_doc_ref = db.collection('_test_connection').document('test')
        test_data = {"test": True, "timestamp": datetime.datetime.utcnow()}
        test_doc_ref.set(test_data)
        
        # Verify the write
        test_doc = test_doc_ref.get()
        if test_doc.exists:
            # Clean up test document
            test_doc_ref.delete()
            return "connected_and_verified"
        else:
            return "write_verification_failed"
    except Exception as e:
        print(f"Database status check failed: {e}")
        return "connection_failed"

# ========== Routes ==========

@router.post("/verify-token", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def verify_token(payload: TokenVerificationRequest = Body(...)):
    """Verify Firebase token and update Firestore user."""
    try:
        decoded_token = auth.verify_id_token(payload.idToken)
        uid = decoded_token["uid"]
        email = decoded_token.get("email", "")
        name = decoded_token.get("name", "")
        picture = decoded_token.get("picture", "")
        
        db = get_or_create_firestore_client()
        database_status = get_database_status(db)
        
        user_ref = db.collection("users").document(uid)
        user_doc = user_ref.get()

        user_data = {
            "uid": uid,
            "email": email,
            "display_name": name,
            "photo_url": picture,
            "last_login_at": datetime.datetime.utcnow()
        }

        is_new_user = False
        if user_doc.exists:
            # Update existing user, preserve important data
            existing_data = user_doc.to_dict()
            
            # Preserve Google credentials and Search Console properties
            user_data.update({
                "google_credentials": existing_data.get("google_credentials"),
                "search_console_properties": existing_data.get("search_console_properties", []),
                "created_at": existing_data.get("created_at", datetime.datetime.utcnow()),
                "account_type": existing_data.get("account_type", "free"),
                "indexing_enabled": existing_data.get("indexing_enabled", True),
                "preferences": existing_data.get("preferences", {}),
                "successful_submissions": existing_data.get("successful_submissions", 0),
                "failed_submissions": existing_data.get("failed_submissions", 0),
                "total_submissions": existing_data.get("total_submissions", 0),
                "last_activity": existing_data.get("last_activity", user_data["last_login_at"])
            })
            
            # Update the document with merged data
            user_ref.update(user_data)
            

        else:
            # Create new user
            is_new_user = True
            try:
                firebase_user = auth.get_user(uid)
                user_data.update({
                    "email": firebase_user.email or email,
                    "display_name": firebase_user.display_name or name,
                    "photo_url": firebase_user.photo_url or picture,
                    "created_at": datetime.datetime.utcnow(),
                    "google_credentials": None,
                    "search_console_properties": []
                })
            except Exception as e:
                print(f"Warning: Could not fetch Firebase user details: {e}")
                user_data.update({
                    "created_at": datetime.datetime.utcnow(),
                    "google_credentials": None,
                    "search_console_properties": []
                })
            
            user_ref.set(user_data)
            
            # Initialize new user with all necessary collections
            if database_status == "connected_and_verified":
                await user_initialization_service.initialize_new_user(user_data)

        # Final response with proper Google auth status
        final_google_auth_enabled = bool(user_data.get("google_credentials"))
        
        return AuthResponse(
            success=True,
            message="Authentication successful with Google API access" if final_google_auth_enabled else "Authentication successful",
            uid=uid,
            email=user_data.get("email"),
            display_name=user_data.get("display_name"),
            photo_url=user_data.get("photo_url"),
            google_auth_enabled=final_google_auth_enabled,
            database_status=database_status
        )
    except auth.InvalidIdTokenError:
        return AuthResponse(
            success=False,
            message="Invalid or expired ID token",
            database_status="auth_error",
            error="Invalid or expired ID token"
        )
    except Exception as e:
        return AuthResponse(
            success=False,
            message=f"Unexpected error: {str(e)}",
            database_status="error",
            error=str(e)
        )

@router.post("/verify-token-with-google", response_model=AuthResponse)
async def verify_firebase_token_with_google_auth(request: GoogleTokenVerificationRequest):
    """Verify Firebase token and optionally store Google credentials."""
    try:
        decoded_token = auth.verify_id_token(request.idToken)
        uid = decoded_token["uid"]
        email = decoded_token.get("email", "")
        name = decoded_token.get("name", "")
        picture = decoded_token.get("picture", "")
        
        db = get_or_create_firestore_client()
        database_status = get_database_status(db)

        user_data = {
            "uid": uid,
            "email": email,
            "display_name": name,
            "photo_url": picture,
            "last_login_at": datetime.datetime.utcnow()
        }

        # Handle Google credentials if provided
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
        user_doc = user_ref.get()
        is_new_user = not user_doc.exists
        
        if user_doc.exists:
            # Update existing user, preserve other data
            existing_data = user_doc.to_dict()
            
            # Only update Google credentials if new ones are provided
            if not request.googleAccessToken and existing_data.get("google_credentials"):
                # Keep existing Google credentials if no new ones provided
                user_data["google_credentials"] = existing_data.get("google_credentials")
                user_data["search_console_properties"] = existing_data.get("search_console_properties", [])

            
            # Preserve other important data
            user_data.update({
                "created_at": existing_data.get("created_at", datetime.datetime.utcnow()),
                "account_type": existing_data.get("account_type", "free"),
                "indexing_enabled": existing_data.get("indexing_enabled", True),
                "preferences": existing_data.get("preferences", {}),
                "successful_submissions": existing_data.get("successful_submissions", 0),
                "failed_submissions": existing_data.get("failed_submissions", 0),
                "total_submissions": existing_data.get("total_submissions", 0),
                "last_activity": user_data["last_login_at"]
            })
            
            user_ref.update(user_data)
        else:
            # Create new user
            user_data["created_at"] = datetime.datetime.utcnow()
            if "search_console_properties" not in user_data:
                user_data["search_console_properties"] = []
            user_ref.set(user_data)
            
            # Initialize new user with all necessary collections
            if database_status == "connected_and_verified":
                await user_initialization_service.initialize_new_user(user_data)

        # Check final Google auth status (either new tokens or existing ones)
        final_google_auth_enabled = bool(user_data.get("google_credentials"))
        
        return AuthResponse(
            success=True,
            message="Authentication successful with Google API access" if final_google_auth_enabled else "Authentication successful",
            uid=uid,
            email=email,
            display_name=name,
            photo_url=picture,
            google_auth_enabled=final_google_auth_enabled,
            database_status=database_status
        )
    except auth.InvalidIdTokenError as e:
        return AuthResponse(
            success=False,
            message="Invalid or expired ID token",
            database_status="auth_error",
            error="Invalid or expired ID token"
        )
    except Exception as e:
        return AuthResponse(
            success=False,
            message=f"Verification failed: {str(e)}",
            database_status="error",
            error=str(e)
        )

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
        # Get user data from Firestore
        db = get_or_create_firestore_client()
        user_doc = db.collection("users").document(user_id).get()
        
        if not user_doc.exists:
            return {
                "isAuthenticated": False,
                "user": None,
                "properties": [],
                "indexStatuses": [],
                "selectedProperty": None,
                "message": "User not found"
            }
        
        user_data = user_doc.to_dict()
        
        # Check if user has Google credentials
        google_creds = user_data.get("google_credentials")
        search_console_properties = user_data.get("search_console_properties", [])
        
        is_authenticated = bool(google_creds and google_creds.get("access_token"))
        
        # Format user data for response
        user_response = {
            "uid": user_data.get("uid"),
            "email": user_data.get("email"),
            "display_name": user_data.get("display_name"),
            "photo_url": user_data.get("photo_url")
        }
        
        # Format properties for response
        properties_response = []
        if search_console_properties:
            for prop in search_console_properties:
                if isinstance(prop, dict):
                    properties_response.append({
                        "property_url": prop.get("property_url", ""),
                        "site_url": prop.get("property_url", ""),  # Legacy compatibility
                        "property_type": prop.get("property_type", "URL_PREFIX"),
                        "permission_level": prop.get("permission_level", "siteOwner"),
                        "verified": prop.get("verified", True)
                    })
        
        selected_property = properties_response[0] if properties_response else None
        
        return {
            "isAuthenticated": is_authenticated,
            "user": user_response,
            "properties": properties_response,
            "indexStatuses": [],  # This could be populated with actual index status data
            "selectedProperty": selected_property,
            "message": "Authentication status retrieved successfully"
        }
        
    except Exception as e:
        return {
            "isAuthenticated": False,
            "user": None,
            "properties": [],
            "indexStatuses": [],
            "selectedProperty": None,
            "message": f"Auth check failed: {str(e)}"
        }

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

@router.put("/user/{user_id}")
async def update_user_profile(user_id: str, updates: Dict[str, Any] = Body(...)):
    """Update user profile in Firestore."""
    try:
        db = get_or_create_firestore_client()
        user_ref = db.collection("users").document(user_id)
        
        # Check if user exists
        if not user_ref.get().exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Filter allowed fields for update
        allowed_fields = {
            "display_name", "photo_url", "preferences", 
            "avatar", "notifications", "personalization"
        }
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        # Add update timestamp
        filtered_updates["updated_at"] = datetime.datetime.utcnow()
        
        # Update user document
        user_ref.update(filtered_updates)
        
        # Get updated user data
        updated_user = user_ref.get().to_dict()
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "uid": updated_user.get("uid"),
            "email": updated_user.get("email"),
            "display_name": updated_user.get("display_name"),
            "photo_url": updated_user.get("photo_url"),
            "avatar": updated_user.get("avatar"),
            "preferences": updated_user.get("preferences", {}),
            "updated_at": updated_user.get("updated_at")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))