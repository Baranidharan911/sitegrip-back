#!/usr/bin/env python3
"""
Background job to reset daily quotas
Run this script as a cron job at midnight every day
"""

import asyncio
import sys
import os
from datetime import datetime, date

# Add the parent directory to the path so we can import from the project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.quota_service import QuotaService
from db.firestore import initialize_firestore

async def main():
    """Main function to reset daily quotas"""
    try:
        print(f"[{datetime.utcnow()}] Starting daily quota reset job...")
        
        # Initialize Firestore
        initialize_firestore()
        
        # Initialize quota service
        quota_service = QuotaService()
        
        # Reset quotas for today (this will create new quota entries for today)
        # The quota service automatically creates new entries for each day,
        # so we don't need to explicitly reset anything
        today = date.today()
        
        print(f"[{datetime.utcnow()}] Quota reset job completed for {today}")
        
        # You could add cleanup of old quota entries here if needed
        # For example, delete quota entries older than 30 days
        
        return 0
        
    except Exception as e:
        print(f"[{datetime.utcnow()}] Error in quota reset job: {e}")
        return 1

if __name__ == "__main__":
    # Run the quota reset job
    result = asyncio.run(main())
    
    # Exit with appropriate code
    sys.exit(result)
