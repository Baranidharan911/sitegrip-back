import json
import asyncio
from datetime import datetime, timedelta
import datetime as dt
from typing import Dict, List, Optional
from urllib.parse import urlparse
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
import requests
from dotenv import load_dotenv
import os

from db.firestore import get_or_create_firestore_client
from models.user import GoogleCredentials, SearchConsoleProperty

class GoogleAuthService:
    def __init__(self):
        load_dotenv()
        self.db = get_or_create_firestore_client()
        self.client_id = os.getenv('GOOGLE_CLIENT_ID', 'your-google-client-id')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET', 'your-google-client-secret')
        self.redirect_uri = os.getenv('GSC_REDIRECT_URI', 'http://localhost:3000/auth/callback')
        self.auth_base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"

    async def get_auth_url(self, user_id: str) -> str:
        """Generate Google OAuth URL for user authentication"""
        scopes = [
            "https://www.googleapis.com/auth/webmasters.readonly",
            "https://www.googleapis.com/auth/webmasters"
        ]
        scope_string = " ".join(scopes)
        
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": scope_string,
            "access_type": "offline",
            "prompt": "consent",
            "state": user_id
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.auth_base_url}?{query_string}"

    async def exchange_code_for_tokens(self, code: str, user_id: str) -> Dict[str, any]:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri
        }
        try:
            response = requests.post(self.token_url, data=data)
            token_data = response.json()
            if "error" in token_data:
                return {"success": False, "error": token_data.get("error_description", "Token exchange failed")}

            expiry = dt.datetime.utcnow() + dt.timedelta(seconds=token_data.get("expires_in", 3600))
            google_creds = GoogleCredentials(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=[
                    "https://www.googleapis.com/auth/webmasters.readonly",
                    "https://www.googleapis.com/auth/webmasters"
                ],
                expiry=expiry
            )

            await self._save_user_credentials(user_id, google_creds)
            properties = await self._fetch_search_console_properties(google_creds)
            await self._save_user_properties(user_id, properties)

            return {
                "success": True,
                "message": "Authentication successful",
                "properties": [prop.dict() for prop in properties]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_user_credentials(self, user_id: str) -> Optional[Credentials]:
        try:
            print(f"🔍 [GoogleAuthService] Getting credentials for user: {user_id}")
            
            user_doc = self.db.collection('users').document(user_id).get()
            if not user_doc.exists:
                print(f"❌ [GoogleAuthService] User document not found: {user_id}")
                return None

            user_data = user_doc.to_dict()
            creds_data = user_data.get("google_credentials")
            if not creds_data:
                print(f"❌ [GoogleAuthService] No Google credentials found for user: {user_id}")
                return None

            print(f"✅ [GoogleAuthService] Found credentials for user: {user_id}")
            
            # Handle expiry date conversion
            expiry = creds_data.get("expiry")
            if expiry:
                if isinstance(expiry, str):
                    try:
                        expiry = dt.datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                    except:
                        expiry = dt.datetime.utcnow() + timedelta(hours=1)  # Default 1 hour
                elif hasattr(expiry, "ToDatetime"):
                    expiry = expiry.ToDatetime()
                elif hasattr(expiry, "timestamp"):
                    expiry = dt.datetime.fromtimestamp(expiry.timestamp())
                else:
                    expiry = dt.datetime.utcnow() + timedelta(hours=1)  # Default 1 hour
            else:
                expiry = dt.datetime.utcnow() + timedelta(hours=1)  # Default 1 hour

            # Get token_uri with fallback
            token_uri = creds_data.get("token_uri", "https://oauth2.googleapis.com/token")
            
            # Create credentials object
            credentials = Credentials(
                token=creds_data.get("access_token"),
                refresh_token=creds_data.get("refresh_token"),
                token_uri=token_uri,
                client_id=creds_data.get("client_id", self.client_id),
                client_secret=creds_data.get("client_secret", self.client_secret),
                scopes=creds_data.get("scopes", [
                    "https://www.googleapis.com/auth/webmasters.readonly",
                    "https://www.googleapis.com/auth/webmasters"
                ]),
                expiry=expiry
            )

            # Check if credentials need refresh
            if credentials.expired and credentials.refresh_token:
                print(f"🔄 [GoogleAuthService] Refreshing expired credentials for user: {user_id}")
                try:
                    credentials.refresh(Request())
                    
                    # Update the credentials in database
                    updated_creds = GoogleCredentials(
                        access_token=credentials.token,
                        refresh_token=credentials.refresh_token,
                        token_uri=credentials.token_uri,
                        client_id=credentials.client_id,
                        client_secret=credentials.client_secret,
                        scopes=credentials.scopes,
                        expiry=credentials.expiry
                    )
                    await self._save_user_credentials(user_id, updated_creds)
                    print(f"✅ [GoogleAuthService] Credentials refreshed for user: {user_id}")
                except RefreshError as refresh_error:
                    print(f"❌ [GoogleAuthService] Failed to refresh credentials: {refresh_error}")
                    return None

            return credentials

        except RefreshError as e:
            print(f"❌ [GoogleAuthService] RefreshError: {e}")
            await self._clear_user_credentials(user_id)
            return None
        except Exception as e:
            print(f"❌ [GoogleAuthService] Error getting credentials: {e}")
            return None

    async def _save_user_credentials(self, user_id: str, credentials: GoogleCredentials):
        self.db.collection('users').document(user_id).set({
            'google_credentials': credentials.dict(),
            'last_login_at': dt.datetime.utcnow()
        }, merge=True)
        print(f"[✅] Saved credentials for {user_id}")

    async def _save_user_properties(self, user_id: str, properties: List[SearchConsoleProperty]):
        self.db.collection('users').document(user_id).set({
            'search_console_properties': [p.dict() for p in properties]
        }, merge=True)

    async def _fetch_search_console_properties(self, credentials: GoogleCredentials) -> List[SearchConsoleProperty]:
        try:
            creds = Credentials(
                token=credentials.access_token,
                refresh_token=credentials.refresh_token,
                token_uri=credentials.token_uri,
                client_id=credentials.client_id,
                client_secret=credentials.client_secret,
                scopes=credentials.scopes
            )
            service = build("searchconsole", "v1", credentials=creds)
            response = service.sites().list().execute()
            return [
                SearchConsoleProperty(
                    property_url=site['siteUrl'],
                    property_type="DOMAIN" if site['siteUrl'].startswith("sc-domain:") else "URL_PREFIX",
                    permission_level=site['permissionLevel']
                )
                for site in response.get("siteEntry", [])
            ]
        except Exception as e:
            print(f"[⚠️] Failed to fetch Search Console properties: {e}")
            return []

    async def _clear_user_credentials(self, user_id: str):
        self.db.collection('users').document(user_id).update({"google_credentials": None})

    def _extract_domain(self, url: str) -> str:
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return "unknown"

    async def _user_owns_domain(self, user_id: str, domain: str) -> bool:
        try:
            user_doc = self.db.collection('users').document(user_id).get()
            if not user_doc.exists:
                return False
            properties = user_doc.to_dict().get("search_console_properties", [])
            for prop in properties:
                prop_url = prop.get("property_url", "").lower().strip()
                if prop_url.startswith("sc-domain:"):
                    root_domain = prop_url.replace("sc-domain:", "")
                    if domain == root_domain or domain.endswith("." + root_domain):
                        return True
                elif self._extract_domain(prop_url) == domain:
                    return True
            return False
        except Exception as e:
            print(f"[❌] Domain check failed: {e}")
            return False


# Singleton instance
google_auth_service = GoogleAuthService()