import asyncio
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List
from urllib.parse import urlparse

from db.firestore import get_or_create_firestore_client
from models.quota_info import QuotaInfo, QuotaUsageStats
from models.indexing_entry import IndexingPriority

class QuotaService:
    """Service for managing indexing quota"""
    
    def __init__(self):
        self.db = get_or_create_firestore_client()
        self.quota_collection = "quota_info"
        
        # Default quota limits
        self.default_daily_limit = 200
        self.default_priority_reserve = 50
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return url.lower()
    
    async def get_quota_info(self, user_id: str, domain: str, target_date: Optional[date] = None) -> QuotaInfo:
        """Get quota information for a domain and date"""
        try:
            if target_date is None:
                target_date = date.today()
            
            quota_id = f"{user_id}_{domain}_{target_date.isoformat()}"
            
            # Try to get existing quota info
            doc_ref = self.db.collection(self.quota_collection).document(quota_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                data['id'] = quota_id
                data['date'] = target_date.isoformat()
                return QuotaInfo(**data)
            else:
                # Create new quota info
                quota_info = QuotaInfo(
                    id=quota_id,
                    domain=domain,
                    user_id=user_id,
                    date=target_date.isoformat(),
                    daily_limit=self.default_daily_limit,
                    priority_reserve=self.default_priority_reserve
                )
                
                # Store in database
                doc_ref.set(quota_info.model_dump(exclude={'id'}))
                return quota_info
                
        except Exception as e:
            print(f"Error getting quota info: {e}")
            # Return default quota info
            return QuotaInfo(
                domain=domain,
                user_id=user_id,
                date=(target_date or date.today()).isoformat()
            )
    
    async def check_quota_availability(
        self, 
        user_id: str, 
        url: str, 
        priority: IndexingPriority
    ) -> tuple[bool, str]:
        """Check if quota is available for a URL submission"""
        try:
            domain = self._extract_domain(url)
            quota_info = await self.get_quota_info(user_id, domain)
            
            # Check based on priority
            if priority in [IndexingPriority.HIGH, IndexingPriority.CRITICAL]:
                if not quota_info.can_submit_priority:
                    return False, f"Priority quota exceeded for domain {domain}"
            else:
                if not quota_info.can_submit_regular:
                    return False, f"Regular quota exceeded for domain {domain}"
            
            if quota_info.remaining_quota <= 0:
                return False, f"Daily quota exceeded for domain {domain}"
            
            return True, "Quota available"
            
        except Exception as e:
            print(f"Error checking quota availability: {e}")
            return False, "Error checking quota"
    
    async def consume_quota(
        self, 
        user_id: str, 
        url: str, 
        priority: IndexingPriority,
        success: bool = True
    ) -> bool:
        """Consume quota for a URL submission"""
        try:
            domain = self._extract_domain(url)
            quota_info = await self.get_quota_info(user_id, domain)
            
            # Update usage counters
            quota_info.total_used += 1
            quota_info.updated_at = datetime.utcnow()
            
            # Update priority-specific counters
            if priority == IndexingPriority.LOW:
                quota_info.low_priority_used += 1
            elif priority == IndexingPriority.MEDIUM:
                quota_info.medium_priority_used += 1
            elif priority == IndexingPriority.HIGH:
                quota_info.high_priority_used += 1
            elif priority == IndexingPriority.CRITICAL:
                quota_info.critical_priority_used += 1
            
            # Update in database
            doc_ref = self.db.collection(self.quota_collection).document(quota_info.id)
            doc_ref.update(quota_info.model_dump(exclude={'id', 'date'}))
            
            return True
            
        except Exception as e:
            print(f"Error consuming quota: {e}")
            return False
    
    async def get_quota_stats(self, user_id: str, domain: str, days: int = 7) -> List[QuotaUsageStats]:
        """Get quota usage statistics for the last N days"""
        try:
            stats = []
            
            for i in range(days):
                target_date = date.today() - timedelta(days=i)
                quota_info = await self.get_quota_info(user_id, domain, target_date)
                
                # Calculate success rate (would need to query indexing entries)
                success_rate = 85.0  # Placeholder
                
                usage_by_priority = {
                    "low": quota_info.low_priority_used,
                    "medium": quota_info.medium_priority_used,
                    "high": quota_info.high_priority_used,
                    "critical": quota_info.critical_priority_used
                }
                
                stat = QuotaUsageStats(
                    domain=domain,
                    date=target_date.isoformat(),
                    daily_limit=quota_info.daily_limit,
                    total_used=quota_info.total_used,
                    remaining=quota_info.remaining_quota,
                    usage_by_priority=usage_by_priority,
                    success_rate=success_rate
                )
                
                stats.append(stat)
            
            return stats
            
        except Exception as e:
            print(f"Error getting quota stats: {e}")
            return []
    
    async def reset_daily_quotas(self, target_date: Optional[date] = None) -> int:
        """Reset quotas for a specific date (used in background jobs)"""
        try:
            if target_date is None:
                target_date = date.today()
            
            # This would be implemented based on your specific requirements
            # For now, we don't need to reset as we create new quota entries daily
            return 0
            
        except Exception as e:
            print(f"Error resetting quotas: {e}")
            return 0
    
    async def get_user_domains(self, user_id: str) -> List[str]:
        """Get all domains that have quota info for a user"""
        try:
            # Query quota collection for user's domains
            query = self.db.collection(self.quota_collection).where('user_id', '==', user_id)
            docs = query.stream()
            
            domains = set()
            for doc in docs:
                data = doc.to_dict()
                if 'domain' in data:
                    domains.add(data['domain'])
            
            return list(domains)
            
        except Exception as e:
            print(f"Error getting user domains: {e}")
            return []
    
    async def set_domain_limits(
        self, 
        user_id: str, 
        domain: str, 
        daily_limit: int, 
        priority_reserve: int
    ) -> bool:
        """Set custom quota limits for a domain"""
        try:
            today = date.today()
            quota_info = await self.get_quota_info(user_id, domain, today)
            
            quota_info.daily_limit = daily_limit
            quota_info.priority_reserve = priority_reserve
            quota_info.updated_at = datetime.utcnow()
            
            # Update in database
            doc_ref = self.db.collection(self.quota_collection).document(quota_info.id)
            doc_ref.update({
                'daily_limit': daily_limit,
                'priority_reserve': priority_reserve,
                'updated_at': quota_info.updated_at
            })
            
            return True
            
        except Exception as e:
            print(f"Error setting domain limits: {e}")
            return False
