# backend/services/storage.py
from db.firestore import get_firestore_client
from models.crawl_result import CrawlResult
from typing import Optional, List
import os
from dotenv import load_dotenv
from pydantic import ValidationError # <-- Import the validation error

load_dotenv()

COLLECTION_NAME = os.getenv("FIRESTORE_COLLECTION_NAME", "crawls")

class StorageService:
    def __init__(self):
        try:
            print(f"Initializing StorageService with collection: {COLLECTION_NAME}")
            self.db = get_firestore_client()
            self.collection = self.db.collection(COLLECTION_NAME)
            self.firestore_available = True
            print("StorageService initialized successfully")
        except Exception as e:
            print(f"Warning: Firestore initialization failed: {e}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            self.firestore_available = False
            self.db = None
            self.collection = None

    def save_crawl_result(self, crawl_result: CrawlResult) -> str:
        """
        Saves a CrawlResult object to Firestore.
        """
        if not self.firestore_available:
            print("Warning: Firestore not available, skipping save")
            return crawl_result.crawl_id
            
        try:
            print(f"Attempting to save crawl result with ID: {crawl_result.crawl_id}")
            doc_ref = self.collection.document(crawl_result.crawl_id)
            data_dict = crawl_result.dict(by_alias=True)
            print(f"Saving to Firestore collection: {COLLECTION_NAME}")
            doc_ref.set(data_dict)
            print(f"Successfully saved crawl result to Firestore: {crawl_result.crawl_id}")
            return crawl_result.crawl_id
        except Exception as e:
            print(f"Error saving to Firestore: {e}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            # Don't raise the exception, just log it
            return crawl_result.crawl_id

    def get_crawl_by_id(self, crawl_id: str) -> Optional[CrawlResult]:
        """
        Retrieves a crawl result by its ID.
        """
        if not self.firestore_available:
            print("Warning: Firestore not available")
            return None
            
        try:
            doc_ref = self.collection.document(crawl_id)
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                data['crawlId'] = doc.id
                try:
                    return CrawlResult(**data)
                except ValidationError as e:
                    print(f"Validation error for document {doc.id}: {e}")
                    return None # Return None if data is malformed
            return None
        except Exception as e:
            print(f"Error retrieving from Firestore: {e}")
            return None

    def get_all_crawls(self) -> List[CrawlResult]:
        """
        Retrieves all crawl results, ordered by date.
        This version gracefully handles malformed documents and Firestore unavailability.
        """
        if not self.firestore_available:
            print("Warning: Firestore not available, returning empty list")
            return []
            
        try:
            print(f"Querying Firestore collection: {COLLECTION_NAME}")
            query = self.collection.order_by('crawledAt', direction='DESCENDING').stream()
            results = []
            doc_count = 0
            for doc in query:
                doc_count += 1
                try:
                    # 1. Get the data dictionary from the document.
                    data = doc.to_dict()
                    # 2. Manually add the document's ID to the dictionary.
                    data['crawlId'] = doc.id
                    # 3. Attempt to validate and create the CrawlResult object.
                    results.append(CrawlResult(**data))
                    print(f"Successfully loaded document: {doc.id}")
                except ValidationError as e:
                    # 4. If validation fails, print a warning and skip this document.
                    #    This prevents the entire API call from crashing.
                    print(f"Skipping malformed document with ID {doc.id} in history. Reason: {e}")
                    continue # Move to the next document
            print(f"Retrieved {len(results)} valid crawl results out of {doc_count} documents")
            return results
        except Exception as e:
            print(f"Error retrieving crawl history: {e}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            return []  # Return empty list instead of raising exception

    def get_latest_crawl_by_url(self, url: str) -> Optional[CrawlResult]:
        """
        Retrieves the most recent completed crawl for a given URL.
        """
        if not self.firestore_available:
            print("Warning: Firestore not available")
            return None
        try:
            query = self.collection.where('url', '==', url).where('status', '==', 'completed').order_by('end_time', direction='DESCENDING').limit(1)
            docs = list(query.stream())
            if not docs:
                return None
            
            doc = docs[0]
            data = doc.to_dict()
            data['crawlId'] = doc.id
            return CrawlResult(**data)
        except Exception as e:
            print(f"Error fetching latest crawl for {url}: {e}")
            return None

    def get_crawls_by_user(self, user_id: str) -> List[CrawlResult]:
        """
        Retrieves all crawl results for a specific user, ordered by date.
        """
        if not self.firestore_available:
            print("Warning: Firestore not available, returning empty list")
            return []
            
        try:
            print(f"Querying Firestore collection: {COLLECTION_NAME} for user: {user_id}")
            query = self.collection.where('userId', '==', user_id).order_by('crawledAt', direction='DESCENDING').stream()
            results = []
            doc_count = 0
            for doc in query:
                doc_count += 1
                try:
                    # 1. Get the data dictionary from the document.
                    data = doc.to_dict()
                    # 2. Manually add the document's ID to the dictionary.
                    data['crawlId'] = doc.id
                    # 3. Attempt to validate and create the CrawlResult object.
                    results.append(CrawlResult(**data))
                    print(f"Successfully loaded document: {doc.id} for user: {user_id}")
                except ValidationError as e:
                    # 4. If validation fails, print a warning and skip this document.
                    print(f"Skipping malformed document with ID {doc.id} for user {user_id}. Reason: {e}")
                    continue # Move to the next document
            print(f"Retrieved {len(results)} valid crawl results out of {doc_count} documents for user: {user_id}")
            return results
        except Exception as e:
            print(f"Error retrieving crawl history for user {user_id}: {e}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            return []  # Return empty list instead of raising exception

# Instantiate the service for easy import
storage_service = StorageService()