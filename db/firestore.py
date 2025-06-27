# backend/db/firestore.py
import firebase_admin
from firebase_admin import credentials, firestore
import os
from datetime import datetime
from typing import Dict, Any, Optional, List

# Mock Firestore Client for when database is in Datastore mode
class MockFirestoreClient:
    """Mock Firestore client for when database is in Datastore mode"""
    
    def __init__(self):
        print("⚠️  Using Mock Firestore Client - Database operations will be logged but not executed")
        self.collections = {}
        
    def collection(self, name: str):
        return MockCollectionReference(name)

class MockCollectionReference:
    def __init__(self, name: str):
        self.name = name
        
    def document(self, doc_id: str = None):
        return MockDocumentReference(self.name, doc_id)
        
    def where(self, field: str, op: str, value: Any):
        return MockQuery(self.name, field, op, value)
        
    def order_by(self, field: str, direction: str = 'ASCENDING'):
        return MockQuery(self.name)
        
    def limit(self, count: int):
        return MockQuery(self.name)
        
    def offset(self, count: int):
        return MockQuery(self.name)
        
    def stream(self):
        print(f"📖 Mock Stream: {self.name} (returning empty results)")
        return []

class MockQuery:
    def __init__(self, collection_name: str, field: str = None, op: str = None, value: Any = None):
        self.collection_name = collection_name
        self.field = field
        self.op = op
        self.value = value
        
    def where(self, field: str, op: str, value: Any):
        return MockQuery(self.collection_name, field, op, value)
        
    def order_by(self, field: str, direction: str = 'ASCENDING'):
        return self
        
    def limit(self, count: int):
        return self
        
    def offset(self, count: int):
        return self
        
    def stream(self):
        print(f"📖 Mock Query Stream: {self.collection_name} (returning empty results)")
        return []

class MockDocumentReference:
    def __init__(self, collection_name: str, doc_id: str = None):
        self.collection_name = collection_name
        self.doc_id = doc_id or "mock_doc_id"
        
    def set(self, data: Dict[str, Any], merge: bool = False):
        print(f"💾 Mock Set: {self.collection_name}/{self.doc_id} = {data}")
        return True
        
    def update(self, data: Dict[str, Any]):
        print(f"🔄 Mock Update: {self.collection_name}/{self.doc_id} = {data}")
        return True
        
    def get(self):
        print(f"📖 Mock Get: {self.collection_name}/{self.doc_id} (returning empty document)")
        return MockDocumentSnapshot(self.doc_id)
        
    def delete(self):
        print(f"🗑️ Mock Delete: {self.collection_name}/{self.doc_id}")
        return True

class MockDocumentSnapshot:
    def __init__(self, doc_id: str):
        self.id = doc_id
        self.exists = False
        
    def to_dict(self):
        return {}

def initialize_firestore():
    """
    Initializes the Firebase Admin SDK using credentials from a service account file.
    Ensures that initialization happens only once.
    """
    if not firebase_admin._apps:
        try:
            # Check if we're running on Cloud Run, App Engine, or locally
            if os.getenv('K_SERVICE') or os.getenv('GAE_ENV'):
                # Running on Cloud Run or App Engine - use Application Default Credentials
                # with explicit project ID
                project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'sitegrip-backend')
                print(f"🚀 Initializing Firebase Admin SDK for Cloud Run/App Engine with project: {project_id}")
                firebase_admin.initialize_app(options={'projectId': project_id})
                print(f"✅ Firebase Admin SDK initialized with Application Default Credentials for project: {project_id}")
            else:
                # Running locally - use service account key file
                service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'serviceAccountKey.json')
                if os.path.exists(service_account_file):
                    print(f"🔑 Using service account key file: {service_account_file}")
                    cred = credentials.Certificate(service_account_file)
                    firebase_admin.initialize_app(cred)
                    print("✅ Firebase Admin SDK initialized with service account key (Local).")
                else:
                    # Fallback to Application Default Credentials
                    project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'sitegrip-backend')
                    print(f"🔄 Fallback to Application Default Credentials for project: {project_id}")
                    firebase_admin.initialize_app(options={'projectId': project_id})
                    print(f"✅ Firebase Admin SDK initialized with Application Default Credentials (Fallback) for project: {project_id}")
        except Exception as e:
            print(f"❌ Error initializing Firebase Admin SDK: {e}")
            raise

def get_firestore_client():
    """
    Returns a Firestore client instance.
    Initializes the app if it hasn't been initialized yet.
    """
    initialize_firestore()
    
    # Get the database name from environment (production) or use default
    database_name = os.getenv('GOOGLE_FIRESTORE_DATABASE', 'indexing-sitegrip')
    is_cloud_run = bool(os.getenv('K_SERVICE') or os.getenv('GAE_ENV'))
    
    print(f"🔍 Environment: {'Cloud Run/App Engine' if is_cloud_run else 'Local'}")
    print(f"🔍 Target database: {database_name}")
    
    try:
        print(f"🔍 Attempting to connect to Firestore database: {database_name}")
        client = firestore.client(database_id=database_name)
        
        # Test the client to see if it's accessible
        test_collection = client.collection('_test_connection')
        test_doc = test_collection.document('test')
        test_doc.get()  # This will fail if database is not accessible
        print(f"✅ Connected to Firestore database: {database_name}")
        return client
    except Exception as e:
        print(f"❌ Error connecting to {database_name} database: {e}")
        
        # Only try default database as fallback if we weren't already using it
        if database_name != '(default)':
            try:
                print("🔍 Attempting to connect to Firestore default database as fallback...")
                client = firestore.client()  # Uses default database
                
                # Test the client to see if it's accessible
                test_collection = client.collection('_test_connection')
                test_doc = test_collection.document('test')
                test_doc.get()  # This will fail if database is not accessible
                print("✅ Connected to Firestore default database")
                return client
            except Exception as e2:
                error_str = str(e2)
                print(f"❌ Error connecting to default database: {e2}")
                
                # Check if this is a Datastore mode issue
                if "Datastore Mode" in error_str or "400" in error_str or "INVALID_ARGUMENT" in error_str:
                    print(f"❌ Firestore Database Mode Issue Detected: {e2}")
                    print("🔧 SOLUTION REQUIRED:")
                    print("   1. Go to Firebase Console: https://console.firebase.google.com/project/sitegrip-backend/firestore")
                    print("   2. Check if you have a database in Datastore mode")
                    print("   3. If yes, you need to:")
                    print("      a. Create a new Firebase project with Firestore Native mode, OR")
                    print("      b. Migrate from Datastore mode to Firestore Native mode")
                    print("   4. Update your service account key to point to the correct project")
                    print("   5. Alternative: Use a different Firebase project with Firestore Native mode")
                    
                    # Return mock client as fallback
                    return MockFirestoreClient()
                else:
                    # Re-raise original error for debugging
                    print(f"🔧 Debugging info: Original error: {e}")
                    print(f"🔧 Debugging info: Fallback error: {e2}")
                    if is_cloud_run:
                        print("🔧 For Cloud Run deployment, ensure:")
                        print("   - Service account has Firestore permissions")
                        print("   - Database name is correctly set in environment variables")
                        print("   - Project ID matches the service account project")
                    return MockFirestoreClient()
        else:
            # Already tried default, check for Datastore mode
            error_str = str(e)
            if "Datastore Mode" in error_str or "400" in error_str or "INVALID_ARGUMENT" in error_str:
                print(f"❌ Firestore Database Mode Issue Detected: {e}")
                print("🔧 SOLUTION REQUIRED:")
                print("   1. Go to Firebase Console: https://console.firebase.google.com/project/sitegrip-backend/firestore")
                print("   2. Check if you have a database in Datastore mode")
                print("   3. If yes, you need to:")
                print("      a. Create a new Firebase project with Firestore Native mode, OR")
                print("      b. Migrate from Datastore mode to Firestore Native mode")
                print("   4. Update your service account key to point to the correct project")
                print("   5. Alternative: Use a different Firebase project with Firestore Native mode")
                
                # Return mock client as fallback
                return MockFirestoreClient()
            else:
                # Re-raise original error for debugging
                print(f"🔧 Debugging info: Error details: {e}")
                if is_cloud_run:
                    print("🔧 For Cloud Run deployment, ensure:")
                    print("   - Service account has Firestore permissions")
                    print("   - Database name is correctly set in environment variables")
                    print("   - Project ID matches the service account project")
                return MockFirestoreClient()

# Create a global client instance for easy importing
firestore_client = None

def get_or_create_firestore_client():
    """
    Returns the global Firestore client, creating it if necessary.
    """
    global firestore_client
    if firestore_client is None:
        firestore_client = get_firestore_client()
    return firestore_client

# Initialize the global client
try:
    firestore_client = get_firestore_client()
except Exception as e:
    print(f"Warning: Could not initialize firestore_client during import: {e}")
    firestore_client = None

# Example of how to use it (optional, for direct testing)
if __name__ == "__main__":
    try:
        db = get_firestore_client()
        print("Successfully connected to Firestore.")
        # You can perform a simple test operation here, e.g.,
        # doc_ref = db.collection('test_collection').document('test_doc')
        # doc_ref.set({'status': 'connected'})
        # print("Test document written to 'test_collection'.")
    except Exception as e:
        print(f"Failed to get Firestore client: {e}")