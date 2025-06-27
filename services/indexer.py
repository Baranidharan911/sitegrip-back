import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple, Any
from urllib.parse import urlparse
import os

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import BatchHttpRequest
from googleapiclient.errors import HttpError
import requests

from db.firestore import get_or_create_firestore_client
from models.indexing_entry import IndexingEntry, IndexingStatus, IndexingPriority, IndexingAction
from models.indexing_monitor import IndexingError
from services.quota_service import QuotaService
from services.google_auth_service import google_auth_service
from services.indexing_monitor_service import indexing_monitor_service

class IndexingService:
    """Service for Google Indexing API integration"""
    
    def __init__(self):
        self.db = get_or_create_firestore_client()
        self.quota_service = QuotaService()
        self.indexing_collection = "indexing_entries"
        
        # Google Indexing API configuration
        self.api_name = "indexing"
        self.api_version = "v3"
        self.scopes = ["https://www.googleapis.com/auth/indexing"]
        
        # Initialize fallback service account service (for backward compatibility)
        self.service_account_service = self._initialize_service_account()
    
    def _initialize_service_account(self):
        """Initialize Google Indexing API service with service account (fallback)"""
        try:
            # Load service account credentials from environment or file
            service_account_info = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            
            if service_account_info:
                # Parse JSON from environment variable
                service_account_dict = json.loads(service_account_info)
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_dict, scopes=self.scopes
                )
            else:
                # Load from file
                service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'serviceAccountKey.json')
                if os.path.exists(service_account_file):
                    credentials = service_account.Credentials.from_service_account_file(
                        service_account_file, scopes=self.scopes
                    )
                else:
                    return None
            
            return build(self.api_name, self.api_version, credentials=credentials)
            
        except Exception as e:
            print(f"Error initializing service account: {e}")
            return None
    
    async def _get_user_indexing_service(self, user_id: str):
        """Get Google Indexing API service using user's OAuth credentials"""
        try:
            # Get user's refreshed credentials
            creds = await google_auth_service.get_refreshed_credentials(user_id)
            if not creds:
                # Fallback to service account if user credentials not available
                return self.service_account_service
            
            # Build service with user credentials
            return build(self.api_name, self.api_version, credentials=creds, cache_discovery=False)
            
        except Exception as e:
            print(f"Error getting user indexing service: {e}")
            return self.service_account_service
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return url.lower()
    
    async def submit_url(
        self, 
        user_id: str, 
        url: str, 
        priority: IndexingPriority = IndexingPriority.MEDIUM,
        action: IndexingAction = IndexingAction.URL_UPDATED
    ) -> IndexingEntry:
        """Submit a single URL for indexing"""
        try:
            domain = self._extract_domain(url)
            
            # Check quota availability
            quota_available, quota_message = await self.quota_service.check_quota_availability(
                user_id, url, priority
            )
            
            if not quota_available:
                entry = IndexingEntry(
                    id=str(uuid.uuid4()),
                    url=url,
                    domain=domain,
                    user_id=user_id,
                    priority=priority,
                    action=action,
                    status=IndexingStatus.QUOTA_EXCEEDED,
                    error_message=quota_message
                )
                await self._store_entry(entry)
                return entry
            
            # Create indexing entry
            entry = IndexingEntry(
                id=str(uuid.uuid4()),
                url=url,
                domain=domain,
                user_id=user_id,
                priority=priority,
                action=action,
                status=IndexingStatus.PENDING
            )
            
            # Store entry in database
            await self._store_entry(entry)
            
            # Get user-specific service
            service = await self._get_user_indexing_service(user_id)
            
            # Submit to Google API
            success = await self._submit_to_google_api(entry, service)
            
            if success:
                entry.status = IndexingStatus.SUCCESS
                entry.completed_at = datetime.now(timezone.utc)
                entry.quota_used = True
                
                # Consume quota
                await self.quota_service.consume_quota(user_id, url, priority, True)
            else:
                entry.status = IndexingStatus.FAILED
                entry.completed_at = datetime.now(timezone.utc)
            
            # Update entry in database
            await self._update_entry(entry)
            
            return entry
            
        except Exception as e:
            print(f"Error submitting URL: {e}")
            entry = IndexingEntry(
                id=str(uuid.uuid4()),
                url=url,
                domain=self._extract_domain(url),
                user_id=user_id,
                priority=priority,
                action=action,
                status=IndexingStatus.FAILED,
                error_message=str(e)
            )
            await self._store_entry(entry)
            return entry
    
    async def submit_bulk_urls(
        self, 
        user_id: str, 
        urls: List[str], 
        priority: IndexingPriority = IndexingPriority.MEDIUM,
        action: IndexingAction = IndexingAction.URL_UPDATED
    ) -> List[IndexingEntry]:
        """Submit multiple URLs for indexing using batch requests"""
        try:
            # Get user-specific service
            service = await self._get_user_indexing_service(user_id)
            if not service:
                return []
            
            # Create monitoring batch
            batch = await indexing_monitor_service.create_batch(
                user_id=user_id,
                urls=urls,
                priority=priority.value,
                action=action.value
            )
            
            entries = []
            results = {}
            processed = 0
            successful = 0
            failed = 0
            quota_exceeded = 0
            errors = []
            
            # Callback for batch responses
            def batch_callback(request_id, response, exception):
                nonlocal processed, successful, failed, quota_exceeded
                url = request_id  # We use URL as request_id
                processed += 1
                
                if exception:
                    failed += 1
                    results[url] = (False, str(exception))
                    errors.append(IndexingError(
                        url=url,
                        error_code=str(exception.resp.status) if hasattr(exception, 'resp') else "unknown",
                        error_message=str(exception),
                        google_api_response=exception.content.decode('utf-8') if hasattr(exception, 'content') else None
                    ))
                else:
                    successful += 1
                    results[url] = (True, response)
                
                # Update monitoring progress
                asyncio.create_task(indexing_monitor_service.update_batch_progress(
                    batch_id=batch.batch_id,
                    processed=processed,
                    successful=successful,
                    failed=failed,
                    quota_exceeded=quota_exceeded,
                    errors=errors
                ))
            
            # Process URLs in batches of 100 (Google's limit)
            BATCH_SIZE = 100
            for i in range(0, len(urls), BATCH_SIZE):
                batch_urls = urls[i:i + BATCH_SIZE]
                batch_entries = []
                
                # Create entries and check quotas
                for url in batch_urls:
                    domain = self._extract_domain(url)
                    
                    # Check quota
                    quota_available, quota_message = await self.quota_service.check_quota_availability(
                        user_id, url, priority
                    )
                    
                    entry = IndexingEntry(
                        id=str(uuid.uuid4()),
                        url=url,
                        domain=domain,
                        user_id=user_id,
                        priority=priority,
                        action=action,
                        status=IndexingStatus.PENDING if quota_available else IndexingStatus.QUOTA_EXCEEDED,
                        error_message=None if quota_available else quota_message
                    )
                    
                    await self._store_entry(entry)
                    batch_entries.append(entry)
                    
                    if not quota_available:
                        quota_exceeded += 1
                        processed += 1
                        results[url] = (False, quota_message)
                        errors.append(IndexingError(
                            url=url,
                            error_code="QUOTA_EXCEEDED",
                            error_message=quota_message
                        ))
                
                # Create batch request
                batch = BatchHttpRequest(callback=batch_callback)
                
                # Add requests to batch
                for entry in batch_entries:
                    if entry.status != IndexingStatus.QUOTA_EXCEEDED:
                        body = {
                            "url": entry.url,
                            "type": entry.action.value if hasattr(entry.action, 'value') else entry.action
                        }
                        request = service.urlNotifications().publish(body=body)
                        batch.add(request, request_id=entry.url)
                        entry.submitted_at = datetime.now(timezone.utc)
                        entry.status = IndexingStatus.SUBMITTED
                        await self._update_entry(entry)
                
                # Execute batch
                if batch._requests:  # Only execute if there are requests
                    try:
                        batch.execute()
                    except Exception as e:
                        print(f"Batch execution error: {e}")
                        for entry in batch_entries:
                            if entry.status == IndexingStatus.SUBMITTED:
                                failed += 1
                                processed += 1
                                results[entry.url] = (False, str(e))
                                errors.append(IndexingError(
                                    url=entry.url,
                                    error_code="BATCH_ERROR",
                                    error_message=str(e)
                                ))
                
                # Process results
                for entry in batch_entries:
                    if entry.url in results:
                        success, response_or_error = results[entry.url]
                        if success:
                            entry.status = IndexingStatus.SUCCESS
                            entry.google_response = response_or_error
                            entry.quota_used = True
                            await self.quota_service.consume_quota(user_id, entry.url, priority, True)
                        else:
                            entry.status = IndexingStatus.FAILED
                            entry.error_message = str(response_or_error)
                        entry.completed_at = datetime.now(timezone.utc)
                        await self._update_entry(entry)
                    
                    entries.append(entry)
                
                # Small delay between batches to avoid rate limits
                if i + BATCH_SIZE < len(urls):
                    await asyncio.sleep(0.5)
            
            return entries
            
        except Exception as e:
            print(f"Error submitting bulk URLs: {e}")
            return []
    
    async def _submit_to_google_api(self, entry: IndexingEntry, service=None) -> bool:
        """Submit URL to Google Indexing API"""
        try:
            if not service:
                service = self.service_account_service
                
            if not service:
                entry.error_message = "Google service not initialized"
                return False
            
            # Prepare request body
            action_type = entry.action.value if hasattr(entry.action, 'value') else entry.action
            request_body = {
                "url": entry.url,
                "type": action_type
            }
            
            # Submit to Google API
            entry.submitted_at = datetime.now(timezone.utc)
            entry.status = IndexingStatus.SUBMITTED
            await self._update_entry(entry)
            
            # Make the API call
            request = service.urlNotifications().publish(body=request_body)
            response = request.execute()
            
            # Store Google's response
            entry.google_response = response
            
            # Check if submission was successful
            if response and 'urlNotificationMetadata' in response:
                return True
            else:
                entry.error_message = "Invalid response from Google API"
                return False
                
        except HttpError as e:
            print(f"HTTP Error calling Google API: {e}")
            entry.error_message = f"HTTP {e.resp.status}: {e.content.decode('utf-8')}"
            return False
        except Exception as e:
            print(f"Error calling Google API: {e}")
            entry.error_message = str(e)
            return False
    
    async def retry_failed_entries(self, user_id: Optional[str] = None, limit: int = 100) -> int:
        """Retry failed indexing entries"""
        try:
            # Query failed entries that haven't exceeded max retries
            query = self.db.collection(self.indexing_collection) \
                       .where('status', '==', IndexingStatus.FAILED.value) \
                       .where('retry_count', '<', 3) \
                       .limit(limit)
            
            if user_id:
                query = query.where('user_id', '==', user_id)
            
            docs = query.stream()
            
            retried_count = 0
            for doc in docs:
                try:
                    data = doc.to_dict()
                    data['id'] = doc.id
                    entry = IndexingEntry(**data)
                    
                    # Check if enough time has passed since last attempt
                    if entry.completed_at and datetime.now(timezone.utc) - entry.completed_at < timedelta(hours=1):
                        continue
                    
                    # Increment retry count
                    entry.retry_count += 1
                    entry.status = IndexingStatus.RETRYING
                    await self._update_entry(entry)
                    
                    # Retry submission
                    success = await self._submit_to_google_api(entry)
                    
                    if success:
                        entry.status = IndexingStatus.SUCCESS
                        entry.completed_at = datetime.now(timezone.utc)
                        
                        # Consume quota for successful retry
                        await self.quota_service.consume_quota(
                            entry.user_id, entry.url, entry.priority, True
                        )
                    else:
                        entry.status = IndexingStatus.FAILED
                        entry.completed_at = datetime.now(timezone.utc)
                    
                    await self._update_entry(entry)
                    retried_count += 1
                    
                    # Rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"Error retrying entry {doc.id}: {e}")
                    continue
            
            return retried_count
            
        except Exception as e:
            print(f"Error retrying failed entries: {e}")
            return 0
    
    async def get_indexing_history(
        self, 
        user_id: str, 
        page: int = 1, 
        page_size: int = 50,
        status_filter: Optional[IndexingStatus] = None,
        domain_filter: Optional[str] = None
    ) -> Tuple[List[IndexingEntry], int]:
        """Get indexing history for a user"""
        try:
            # Build query
            query = self.db.collection(self.indexing_collection) \
                       .where('user_id', '==', user_id) \
                       .order_by('created_at', direction='DESCENDING')
            
            if status_filter:
                query = query.where('status', '==', status_filter.value)
            
            if domain_filter:
                query = query.where('domain', '==', domain_filter)
            
            # Get total count (simplified approach)
            all_docs = query.stream()
            total_count = sum(1 for _ in all_docs)
            
            # Get paginated results
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
            
            docs = query.stream()
            entries = []
            
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                entries.append(IndexingEntry(**data))
            
            return entries, total_count
            
        except Exception as e:
            print(f"Error getting indexing history: {e}")
            return [], 0
    
    async def get_indexing_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get indexing statistics for a user"""
        try:
            # Calculate date range
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Query entries within date range
            query = self.db.collection(self.indexing_collection) \
                       .where('user_id', '==', user_id) \
                       .where('created_at', '>=', start_date)
            
            docs = query.stream()
            
            # Calculate statistics
            stats = {
                'total_submitted': 0,
                'pending': 0,
                'success': 0,
                'failed': 0,
                'quota_used': 0,
                'by_domain': {},
                'by_priority': {},
                'by_status': {}
            }
            
            for doc in docs:
                data = doc.to_dict()
                status = data.get('status')
                domain = data.get('domain')
                priority = data.get('priority')
                quota_used = data.get('quota_used', False)
                
                stats['total_submitted'] += 1
                
                if status == IndexingStatus.PENDING.value:
                    stats['pending'] += 1
                elif status == IndexingStatus.SUCCESS.value:
                    stats['success'] += 1
                elif status in [IndexingStatus.FAILED.value, IndexingStatus.QUOTA_EXCEEDED.value]:
                    stats['failed'] += 1
                
                if quota_used:
                    stats['quota_used'] += 1
                
                # Domain breakdown
                if domain:
                    stats['by_domain'][domain] = stats['by_domain'].get(domain, 0) + 1
                
                # Priority breakdown
                if priority:
                    stats['by_priority'][priority] = stats['by_priority'].get(priority, 0) + 1
                
                # Status breakdown
                if status:
                    stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
            
            # Calculate success rate
            if stats['total_submitted'] > 0:
                stats['success_rate'] = (stats['success'] / stats['total_submitted']) * 100
            else:
                stats['success_rate'] = 0.0
            
            return stats
            
        except Exception as e:
            print(f"Error getting indexing stats: {e}")
            return {}
    
    async def _store_entry(self, entry: IndexingEntry) -> bool:
        """Store indexing entry in database"""
        try:
            doc_ref = self.db.collection(self.indexing_collection).document(entry.id)
            doc_ref.set(entry.dict(exclude={'id'}))
            return True
        except Exception as e:
            print(f"Error storing entry: {e}")
            return False
    
    async def _update_entry(self, entry: IndexingEntry) -> bool:
        """Update indexing entry in database"""
        try:
            doc_ref = self.db.collection(self.indexing_collection).document(entry.id)
            doc_ref.update(entry.dict(exclude={'id'}))
            return True
        except Exception as e:
            print(f"Error updating entry: {e}")
            return False
    
    async def submit_url_simple(self, url: str, user_id: str = "test_user") -> Dict[str, Any]:
        """Simple URL submission method for testing - returns dict instead of IndexingEntry"""
        try:
            entry = await self.submit_url(
                user_id=user_id,
                url=url,
                priority=IndexingPriority.MEDIUM,
                action=IndexingAction.URL_UPDATED
            )
            
            return {
                "success": entry.status == IndexingStatus.SUCCESS,
                "entry_id": entry.id,
                "status": entry.status.value,
                "error": entry.error_message,
                "message": f"URL submission {'successful' if entry.status == IndexingStatus.SUCCESS else 'failed'}",
                "url": entry.url,
                "google_response": entry.google_response
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to submit URL for indexing"
            }

    async def delete_url(
        self, 
        url: str,
        user_id: str = "test_user", 
        priority: IndexingPriority = IndexingPriority.MEDIUM
    ) -> Dict[str, Any]:
        """Submit a URL for deletion from Google index"""
        try:
            # Submit URL for deletion using URL_DELETED action
            entry = await self.submit_url(
                user_id=user_id,
                url=url,
                priority=priority,
                action=IndexingAction.URL_DELETED
            )
            
            return {
                "success": entry.status == IndexingStatus.SUCCESS,
                "entry_id": entry.id,
                "status": entry.status.value,
                "error": entry.error_message,
                "message": f"URL deletion {'successful' if entry.status == IndexingStatus.SUCCESS else 'failed'}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to submit URL for deletion"
            }

    async def delete_indexing_entry(self, user_id: str, entry_id: str) -> bool:
        """Delete an indexing entry"""
        try:
            # Verify ownership
            doc_ref = self.db.collection(self.indexing_collection).document(entry_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
            
            data = doc.to_dict()
            if data.get('user_id') != user_id:
                return False
            
            # Delete the entry
            doc_ref.delete()
            return True
            
        except Exception as e:
            print(f"Error deleting entry: {e}")
            return False
