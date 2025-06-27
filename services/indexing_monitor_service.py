"""
Service for monitoring and tracking indexing operations
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse

from db.firestore import get_or_create_firestore_client
from models.indexing_monitor import (
    IndexingMetrics, IndexingProgress, IndexingError,
    IndexingBatchStatus, IndexingMonitor
)

class IndexingMonitorService:
    """Service for monitoring indexing operations"""
    
    def __init__(self):
        self.db = get_or_create_firestore_client()
        self.monitor_collection = "indexing_monitors"
        self.batch_collection = "indexing_batches"
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return url.lower()
    
    async def create_batch(
        self,
        user_id: str,
        urls: List[str],
        priority: str,
        action: str
    ) -> IndexingBatchStatus:
        """Create a new batch indexing operation"""
        try:
            # Create batch ID
            batch_id = str(uuid.uuid4())
            
            # Get domain from first URL
            domain = self._extract_domain(urls[0]) if urls else "unknown"
            
            # Create progress tracking
            progress = IndexingProgress(
                total_urls=len(urls),
                pending_urls=len(urls)
            )
            
            # Create metrics
            metrics = IndexingMetrics(
                batch_size=len(urls)
            )
            
            # Create batch status
            batch = IndexingBatchStatus(
                batch_id=batch_id,
                user_id=user_id,
                domain=domain,
                total_urls=len(urls),
                priority=priority,
                action=action,
                status="QUEUED",
                progress=progress,
                metrics=metrics
            )
            
            # Store in database
            doc_ref = self.db.collection(self.batch_collection).document(batch_id)
            doc_ref.set(batch.dict())
            
            # Update monitor
            await self._update_monitor_for_new_batch(user_id, domain, batch_id)
            
            return batch
            
        except Exception as e:
            print(f"Error creating batch: {e}")
            raise
    
    async def update_batch_progress(
        self,
        batch_id: str,
        processed: int,
        successful: int,
        failed: int,
        quota_exceeded: int,
        errors: List[IndexingError] = None
    ) -> IndexingBatchStatus:
        """Update progress for a batch operation"""
        try:
            # Get current batch
            doc_ref = self.db.collection(self.batch_collection).document(batch_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                raise ValueError(f"Batch {batch_id} not found")
            
            batch_data = doc.to_dict()
            batch = IndexingBatchStatus(**batch_data)
            
            # Update progress
            batch.progress.processed_urls = processed
            batch.progress.successful_urls = successful
            batch.progress.failed_urls = failed
            batch.progress.quota_exceeded_urls = quota_exceeded
            batch.progress.pending_urls = batch.total_urls - processed
            batch.progress.last_update = datetime.utcnow()
            
            # Calculate progress metrics
            elapsed = (batch.progress.last_update - batch.progress.start_time).total_seconds()
            if elapsed > 0:
                batch.progress.urls_per_second = processed / elapsed
                if batch.progress.urls_per_second > 0:
                    remaining_urls = batch.total_urls - processed
                    batch.progress.remaining_time_seconds = int(remaining_urls / batch.progress.urls_per_second)
                    batch.progress.estimated_completion = batch.progress.last_update + timedelta(
                        seconds=batch.progress.remaining_time_seconds
                    )
            
            # Update metrics
            batch.metrics.success_count = successful
            batch.metrics.failed_count = failed
            batch.metrics.quota_exceeded_count = quota_exceeded
            
            # Add errors if provided
            if errors:
                batch.errors.extend(errors)
            
            # Check if batch is complete
            if processed >= batch.total_urls:
                batch.status = "COMPLETED"
                batch.completed_at = datetime.utcnow()
            
            # Update in database
            doc_ref.update(batch.dict())
            
            # Update monitor statistics
            await self._update_monitor_stats(batch)
            
            return batch
            
        except Exception as e:
            print(f"Error updating batch progress: {e}")
            raise
    
    async def get_batch_status(self, batch_id: str) -> Optional[IndexingBatchStatus]:
        """Get status of a batch operation"""
        try:
            doc = self.db.collection(self.batch_collection).document(batch_id).get()
            if doc.exists:
                return IndexingBatchStatus(**doc.to_dict())
            return None
        except Exception as e:
            print(f"Error getting batch status: {e}")
            return None
    
    async def get_user_monitor(self, user_id: str, domain: str) -> Optional[IndexingMonitor]:
        """Get monitoring data for a user and domain"""
        try:
            # Create monitor ID
            monitor_id = f"{user_id}_{domain}"
            
            doc = self.db.collection(self.monitor_collection).document(monitor_id).get()
            if doc.exists:
                return IndexingMonitor(**doc.to_dict())
            
            # Create new monitor if it doesn't exist
            monitor = IndexingMonitor(
                user_id=user_id,
                domain=domain
            )
            self.db.collection(self.monitor_collection).document(monitor_id).set(monitor.dict())
            return monitor
            
        except Exception as e:
            print(f"Error getting user monitor: {e}")
            return None
    
    async def get_active_batches(self, user_id: str) -> List[IndexingBatchStatus]:
        """Get all active batches for a user"""
        try:
            query = self.db.collection(self.batch_collection)\
                .where('user_id', '==', user_id)\
                .where('status', 'in', ['QUEUED', 'PROCESSING'])
            
            docs = query.stream()
            return [IndexingBatchStatus(**doc.to_dict()) for doc in docs]
            
        except Exception as e:
            print(f"Error getting active batches: {e}")
            return []
    
    async def get_batch_history(
        self,
        user_id: str,
        domain: Optional[str] = None,
        limit: int = 50
    ) -> List[IndexingBatchStatus]:
        """Get batch history for a user"""
        try:
            query = self.db.collection(self.batch_collection)\
                .where('user_id', '==', user_id)\
                .order_by('created_at', direction='DESCENDING')\
                .limit(limit)
            
            if domain:
                query = query.where('domain', '==', domain)
            
            docs = query.stream()
            return [IndexingBatchStatus(**doc.to_dict()) for doc in docs]
            
        except Exception as e:
            print(f"Error getting batch history: {e}")
            return []
    
    async def _update_monitor_for_new_batch(
        self,
        user_id: str,
        domain: str,
        batch_id: str
    ) -> None:
        """Update monitor when a new batch is created"""
        try:
            monitor_id = f"{user_id}_{domain}"
            doc_ref = self.db.collection(self.monitor_collection).document(monitor_id)
            
            doc = doc_ref.get()
            if doc.exists:
                monitor = IndexingMonitor(**doc.to_dict())
                monitor.active_batches.append(batch_id)
            else:
                monitor = IndexingMonitor(
                    user_id=user_id,
                    domain=domain,
                    active_batches=[batch_id]
                )
            
            doc_ref.set(monitor.dict())
            
        except Exception as e:
            print(f"Error updating monitor for new batch: {e}")
    
    async def _update_monitor_stats(self, batch: IndexingBatchStatus) -> None:
        """Update monitor statistics when a batch is updated"""
        try:
            monitor_id = f"{batch.user_id}_{batch.domain}"
            doc_ref = self.db.collection(self.monitor_collection).document(monitor_id)
            
            doc = doc_ref.get()
            if not doc.exists:
                return
            
            monitor = IndexingMonitor(**doc.to_dict())
            
            # Update batch lists
            if batch.status == "COMPLETED":
                if batch.batch_id in monitor.active_batches:
                    monitor.active_batches.remove(batch.batch_id)
                if batch.batch_id not in monitor.completed_batches:
                    monitor.completed_batches.append(batch.batch_id)
            elif batch.status == "FAILED":
                if batch.batch_id in monitor.active_batches:
                    monitor.active_batches.remove(batch.batch_id)
                if batch.batch_id not in monitor.failed_batches:
                    monitor.failed_batches.append(batch.batch_id)
            
            # Update statistics
            monitor.total_urls_submitted += batch.total_urls
            monitor.total_urls_indexed += batch.metrics.success_count
            monitor.total_urls_failed += batch.metrics.failed_count
            monitor.total_quota_exceeded += batch.metrics.quota_exceeded_count
            
            if batch.metrics.success_count > 0:
                monitor.last_successful_index = datetime.utcnow()
            if batch.metrics.failed_count > 0:
                monitor.last_failed_index = datetime.utcnow()
            
            # Calculate averages
            if monitor.total_urls_submitted > 0:
                monitor.average_success_rate = (
                    monitor.total_urls_indexed / monitor.total_urls_submitted
                ) * 100
            
            if batch.metrics.processing_time_ms:
                if monitor.average_processing_time_ms == 0:
                    monitor.average_processing_time_ms = batch.metrics.processing_time_ms
                else:
                    monitor.average_processing_time_ms = (
                        monitor.average_processing_time_ms + batch.metrics.processing_time_ms
                    ) / 2
            
            # Update quota
            monitor.daily_quota_used += batch.metrics.success_count
            
            # Check alert thresholds
            if monitor.alerts_enabled:
                await self._check_alert_thresholds(monitor, batch)
            
            # Save updates
            doc_ref.update(monitor.dict())
            
        except Exception as e:
            print(f"Error updating monitor stats: {e}")
    
    async def _check_alert_thresholds(
        self,
        monitor: IndexingMonitor,
        batch: IndexingBatchStatus
    ) -> None:
        """Check if any alert thresholds have been exceeded"""
        alerts = []
        
        # Check success rate
        if monitor.average_success_rate < monitor.alert_thresholds["success_rate"]:
            alerts.append({
                "type": "success_rate",
                "message": f"Success rate ({monitor.average_success_rate:.1f}%) below threshold "
                          f"({monitor.alert_thresholds['success_rate']}%)"
            })
        
        # Check error rate
        error_rate = (monitor.total_urls_failed / monitor.total_urls_submitted * 100) \
            if monitor.total_urls_submitted > 0 else 0
        if error_rate > monitor.alert_thresholds["error_rate"]:
            alerts.append({
                "type": "error_rate",
                "message": f"Error rate ({error_rate:.1f}%) above threshold "
                          f"({monitor.alert_thresholds['error_rate']}%)"
            })
        
        # Check quota usage
        quota_usage = (monitor.daily_quota_used / monitor.daily_quota_limit * 100)
        if quota_usage > monitor.alert_thresholds["quota_usage"]:
            alerts.append({
                "type": "quota_usage",
                "message": f"Daily quota usage ({quota_usage:.1f}%) above threshold "
                          f"({monitor.alert_thresholds['quota_usage']}%)"
            })
        
        # Check processing time
        if batch.metrics.processing_time_ms and \
           batch.metrics.processing_time_ms > monitor.alert_thresholds["processing_time"]:
            alerts.append({
                "type": "processing_time",
                "message": f"Processing time ({batch.metrics.processing_time_ms}ms) above threshold "
                          f"({monitor.alert_thresholds['processing_time']}ms)"
            })
        
        # Send alerts (implement your alert mechanism here)
        if alerts:
            await self._send_alerts(monitor, alerts)
    
    async def _send_alerts(self, monitor: IndexingMonitor, alerts: List[Dict]) -> None:
        """Send alerts when thresholds are exceeded"""
        # TODO: Implement your alert mechanism (email, webhook, etc.)
        for alert in alerts:
            print(f"⚠️ ALERT for {monitor.domain}: {alert['message']}")

# Global service instance
indexing_monitor_service = IndexingMonitorService() 