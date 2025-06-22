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
        self.db = get_firestore_client()
        self.collection = self.db.collection(COLLECTION_NAME)

    def save_crawl_result(self, crawl_result: CrawlResult) -> str:
        """
        Saves a CrawlResult object to Firestore.
        """
        try:
            doc_ref = self.collection.document(crawl_result.crawl_id)
            doc_ref.set(crawl_result.dict(by_alias=True))
            return crawl_result.crawl_id
        except Exception as e:
            print(f"Error saving to Firestore: {e}")
            raise

    def get_crawl_by_id(self, crawl_id: str) -> Optional[CrawlResult]:
        """
        Retrieves a crawl result by its ID.
        """
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

    def get_all_crawls(self) -> List[CrawlResult]:
        """
        Retrieves all crawl results, ordered by date.
        This version gracefully handles malformed documents in the database.
        """
        query = self.collection.order_by('crawledAt', direction='DESCENDING').stream()
        results = []
        for doc in query:
            try:
                # 1. Get the data dictionary from the document.
                data = doc.to_dict()
                # 2. Manually add the document's ID to the dictionary.
                data['crawlId'] = doc.id
                # 3. Attempt to validate and create the CrawlResult object.
                results.append(CrawlResult(**data))
            except ValidationError as e:
                # 4. If validation fails, print a warning and skip this document.
                #    This prevents the entire API call from crashing.
                print(f"Skipping malformed document with ID {doc.id} in history. Reason: {e}")
                continue # Move to the next document
        return results

# Instantiate the service for easy import
storage_service = StorageService()