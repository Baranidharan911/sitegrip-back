# backend/db/firestore.py
import firebase_admin
from firebase_admin import credentials, firestore
import os

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
                project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'sitegrip-firestore')
                firebase_admin.initialize_app(options={'projectId': project_id})
                print(f"Firebase Admin SDK initialized with Application Default Credentials (Cloud Run/App Engine) for project: {project_id}")
            else:
                # Running locally - use service account key file
                if os.path.exists("serviceAccountKey.json"):
                    cred = credentials.Certificate("serviceAccountKey.json")
                    firebase_admin.initialize_app(cred)
                    print("Firebase Admin SDK initialized with service account key (Local).")
                else:
                    # Fallback to Application Default Credentials
                    project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'sitegrip-firestore')
                    firebase_admin.initialize_app(options={'projectId': project_id})
                    print(f"Firebase Admin SDK initialized with Application Default Credentials (Fallback) for project: {project_id}")
        except Exception as e:
            print(f"Error initializing Firebase Admin SDK: {e}")
            # You might want to raise the exception or handle it as needed
            raise

def get_firestore_client():
    """
    Returns a Firestore client instance.
    Initializes the app if it hasn't been initialized yet.
    """
    initialize_firestore()
    return firestore.client()

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