from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict
import datetime

class GoogleCredentials(BaseModel):
    """Google OAuth credentials for API access"""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_uri: str = "https://oauth2.googleapis.com/token"
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    expiry: Optional[datetime.datetime] = None

class SearchConsoleProperty(BaseModel):
    """Google Search Console property information"""
    property_url: str
    property_type: str = "URL_PREFIX"  # or "DOMAIN"
    permission_level: str = "OWNER"
    verified: bool = True

class User(BaseModel):
    uid: str
    email: EmailStr
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    last_login_at: Optional[datetime.datetime] = None
    
    # Google API Integration
    google_credentials: Optional[GoogleCredentials] = None
    search_console_properties: List[SearchConsoleProperty] = Field(default_factory=list) 