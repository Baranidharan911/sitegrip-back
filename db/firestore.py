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
            # The path to your service account key file
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
            print("Firebase Admin SDK initialized successfully.")
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