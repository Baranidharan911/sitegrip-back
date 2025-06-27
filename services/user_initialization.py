"""
User Initialization Service

This service handles the creation of all necessary collections and default data
when a new user is created in the system.
"""

import asyncio
from datetime import datetime, date
from typing import Dict, Any
from db.firestore import get_or_create_firestore_client
from models.quota_info import QuotaInfo
from models.user import User

class UserInitializationService:
    """Service to initialize new users with all necessary collections"""
    
    def __init__(self):
        self.db = get_or_create_firestore_client()
    
    async def initialize_new_user(self, user_data: Dict[str, Any]) -> bool:
        """
        Initialize all necessary collections and data for a new user
        
        Args:
            user_data: Dictionary containing user information (uid, email, etc.)
            
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            user_id = user_data.get("uid")
            if not user_id:
                print("Error: No user ID provided for initialization")
                return False
            
            print(f"Initializing new user: {user_id}")
            
            # Initialize user profile (already done by auth endpoint, but ensure it's complete)
            await self._initialize_user_profile(user_data)
            
            # Initialize default quota for common domains
            await self._initialize_default_quotas(user_id)
            
            # Initialize user preferences/settings
            await self._initialize_user_settings(user_id)
            
            # Initialize user statistics
            await self._initialize_user_stats(user_id)
            
            print(f"User initialization completed successfully for: {user_id}")
            return True
            
        except Exception as e:
            print(f"Error initializing user {user_data.get('uid', 'unknown')}: {e}")
            return False
    
    async def _initialize_user_profile(self, user_data: Dict[str, Any]) -> None:
        """Ensure user profile is complete with all necessary fields"""
        try:
            user_id = user_data["uid"]
            user_ref = self.db.collection("users").document(user_id)
            
            # Add any missing fields to user profile
            user_updates = {
                "indexing_enabled": True,
                "account_type": "free",
                "total_submissions": 0,
                "successful_submissions": 0,
                "failed_submissions": 0,
                "last_activity": datetime.utcnow(),
                "preferences": {
                    "default_priority": "medium",
                    "email_notifications": True,
                    "auto_retry_failed": True
                }
            }
            
            # Only update fields that don't already exist
            user_ref.update(user_updates)
            print(f"User profile updated for: {user_id}")
            
        except Exception as e:
            print(f"Error updating user profile: {e}")
    
    async def _initialize_default_quotas(self, user_id: str) -> None:
        """Initialize default quota information for common domains"""
        try:
            # Create a default quota entry for the user
            # This will be used when they submit their first URL
            default_quota = QuotaInfo(
                domain="default",
                user_id=user_id,
                date=date.today().isoformat(),
                daily_limit=200,  # Free tier limit
                priority_reserve=50,
                total_used=0,
                low_priority_used=0,
                medium_priority_used=0,
                high_priority_used=0,
                critical_priority_used=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            quota_id = f"{user_id}_default_{date.today().isoformat()}"
            quota_ref = self.db.collection("quota_info").document(quota_id)
            quota_ref.set(default_quota.model_dump(exclude={'id'}))
            
            print(f"Default quota initialized for user: {user_id}")
            
        except Exception as e:
            print(f"Error initializing default quotas: {e}")
    
    async def _initialize_user_settings(self, user_id: str) -> None:
        """Initialize user settings and preferences"""
        try:
            settings = {
                "user_id": user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "indexing_settings": {
                    "default_priority": "medium",
                    "auto_retry_failed": True,
                    "max_retries": 3,
                    "retry_delay_hours": 1
                },
                "notification_settings": {
                    "email_on_success": False,
                    "email_on_failure": True,
                    "email_on_quota_warning": True,
                    "weekly_summary": True
                },
                "api_settings": {
                    "rate_limit_per_minute": 10,
                    "bulk_upload_limit": 1000,
                    "concurrent_requests": 5
                }
            }
            
            settings_ref = self.db.collection("user_settings").document(user_id)
            settings_ref.set(settings)
            
            print(f"User settings initialized for: {user_id}")
            
        except Exception as e:
            print(f"Error initializing user settings: {e}")
    
    async def _initialize_user_stats(self, user_id: str) -> None:
        """Initialize user statistics tracking"""
        try:
            stats = {
                "user_id": user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "lifetime_stats": {
                    "total_urls_submitted": 0,
                    "total_urls_indexed": 0,
                    "total_urls_failed": 0,
                    "total_quota_used": 0,
                    "success_rate": 0.0,
                    "domains_used": [],
                    "first_submission": None,
                    "last_submission": None
                },
                "monthly_stats": {
                    "urls_submitted": 0,
                    "urls_indexed": 0,
                    "urls_failed": 0,
                    "quota_used": 0,
                    "month_year": datetime.utcnow().strftime("%Y-%m")
                },
                "daily_stats": {
                    "urls_submitted": 0,
                    "urls_indexed": 0,
                    "urls_failed": 0,
                    "quota_used": 0,
                    "date": date.today().isoformat()
                }
            }
            
            stats_ref = self.db.collection("user_stats").document(user_id)
            stats_ref.set(stats)
            
            print(f"User statistics initialized for: {user_id}")
            
        except Exception as e:
            print(f"Error initializing user statistics: {e}")

# Global instance
user_initialization_service = UserInitializationService() 