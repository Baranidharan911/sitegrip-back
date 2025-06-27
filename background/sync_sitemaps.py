#!/usr/bin/env python3
"""
Background job to sync sitemaps daily
Run this script as a cron job once per day
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import from the project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.sitemap_service import SitemapService
from db.firestore import initialize_firestore

async def main():
    """Main function to sync sitemaps daily"""
    try:
        print(f"[{datetime.utcnow()}] Starting daily sitemap sync job...")
        
        # Initialize Firestore (if not running in test mode)
        if not os.getenv('TESTING_MODE'):
            initialize_firestore()
        
        # Initialize sitemap service
        sitemap_service = SitemapService()
        
        # For testing, just return 0 immediately if no real data
        if os.getenv('TESTING_MODE'):
            print(f"[{datetime.utcnow()}] Running in test mode - skipping actual sync")
            return 0
        
        # Sync all sitemaps that have auto_sync enabled
        synced_count = await sitemap_service.sync_sitemaps_daily()
        
        print(f"[{datetime.utcnow()}] Successfully synced {synced_count} sitemaps")
        
        return synced_count
        
    except Exception as e:
        print(f"[{datetime.utcnow()}] Error in sitemap sync job: {e}")
        return 0

if __name__ == "__main__":
    # Run the sitemap sync job
    result = asyncio.run(main())
    
    # Exit with appropriate code
    sys.exit(0 if result >= 0 else 1)
