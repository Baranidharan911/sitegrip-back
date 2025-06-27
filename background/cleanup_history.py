#!/usr/bin/env python3
"""
Background job to cleanup old indexing and sitemap history
Run this script as a cron job weekly
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import from the project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.firestore import get_or_create_firestore_client, initialize_firestore

async def cleanup_indexing_history(days_to_keep: int = 90) -> int:
    """Cleanup indexing entries older than specified days"""
    try:
        db = get_or_create_firestore_client()
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Query old indexing entries
        query = db.collection('indexing_entries') \
                  .where('created_at', '<', cutoff_date) \
                  .limit(500)  # Process in batches
        
        docs = query.stream()
        deleted_count = 0
        
        # Delete old entries
        batch = db.batch()
        batch_count = 0
        
        for doc in docs:
            batch.delete(doc.reference)
            batch_count += 1
            deleted_count += 1
            
            # Commit batch every 100 deletes
            if batch_count >= 100:
                batch.commit()
                batch = db.batch()
                batch_count = 0
        
        # Commit remaining deletes
        if batch_count > 0:
            batch.commit()
        
        return deleted_count
        
    except Exception as e:
        print(f"Error cleaning up indexing history: {e}")
        return 0

async def cleanup_sitemap_history(days_to_keep: int = 90) -> int:
    """Cleanup sitemap entries older than specified days"""
    try:
        db = get_or_create_firestore_client()
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Query old sitemap entries (keep active ones)
        query = db.collection('sitemaps') \
                  .where('created_at', '<', cutoff_date) \
                  .where('status', 'in', ['failed', 'deleted']) \
                  .limit(500)  # Process in batches
        
        docs = query.stream()
        deleted_count = 0
        
        # Delete old entries
        batch = db.batch()
        batch_count = 0
        
        for doc in docs:
            batch.delete(doc.reference)
            batch_count += 1
            deleted_count += 1
            
            # Commit batch every 100 deletes
            if batch_count >= 100:
                batch.commit()
                batch = db.batch()
                batch_count = 0
        
        # Commit remaining deletes
        if batch_count > 0:
            batch.commit()
        
        return deleted_count
        
    except Exception as e:
        print(f"Error cleaning up sitemap history: {e}")
        return 0

async def cleanup_quota_history(days_to_keep: int = 30) -> int:
    """Cleanup quota entries older than specified days"""
    try:
        db = get_or_create_firestore_client()
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Query old quota entries
        query = db.collection('quota_info') \
                  .where('created_at', '<', cutoff_date) \
                  .limit(500)  # Process in batches
        
        docs = query.stream()
        deleted_count = 0
        
        # Delete old entries
        batch = db.batch()
        batch_count = 0
        
        for doc in docs:
            batch.delete(doc.reference)
            batch_count += 1
            deleted_count += 1
            
            # Commit batch every 100 deletes
            if batch_count >= 100:
                batch.commit()
                batch = db.batch()
                batch_count = 0
        
        # Commit remaining deletes
        if batch_count > 0:
            batch.commit()
        
        return deleted_count
        
    except Exception as e:
        print(f"Error cleaning up quota history: {e}")
        return 0

async def main():
    """Main function to cleanup old history"""
    try:
        print(f"[{datetime.utcnow()}] Starting history cleanup job...")
        
        # For testing, just return 0 immediately if no real data
        if os.getenv('TESTING_MODE'):
            print(f"[{datetime.utcnow()}] Running in test mode - skipping actual cleanup")
            return 0
        
        # Initialize Firestore
        initialize_firestore()
        
        # Cleanup different types of history
        indexing_deleted = await cleanup_indexing_history(days_to_keep=90)
        sitemap_deleted = await cleanup_sitemap_history(days_to_keep=90)
        quota_deleted = await cleanup_quota_history(days_to_keep=30)
        
        total_deleted = indexing_deleted + sitemap_deleted + quota_deleted
        
        print(f"[{datetime.utcnow()}] Cleanup completed:")
        print(f"  - Indexing entries deleted: {indexing_deleted}")
        print(f"  - Sitemap entries deleted: {sitemap_deleted}")
        print(f"  - Quota entries deleted: {quota_deleted}")
        print(f"  - Total deleted: {total_deleted}")
        
        return total_deleted
        
    except Exception as e:
        print(f"[{datetime.utcnow()}] Error in cleanup job: {e}")
        return 0

if __name__ == "__main__":
    # Run the cleanup job
    result = asyncio.run(main())
    
    # Exit with appropriate code
    sys.exit(0 if result >= 0 else 1)
