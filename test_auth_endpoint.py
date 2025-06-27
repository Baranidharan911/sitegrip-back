#!/usr/bin/env python3
"""
Quick test script to verify the auth endpoint is accessible
"""
import requests
import json

def test_auth_endpoint():
    """Test if the auth endpoint responds"""
    try:
        # Test OPTIONS request (CORS preflight)
        print("Testing OPTIONS request...")
        options_response = requests.options("http://localhost:8000/api/auth/verify-token-with-google")
        print(f"OPTIONS Status: {options_response.status_code}")
        print(f"OPTIONS Headers: {dict(options_response.headers)}")
        
        # Test POST with invalid data (should return error but show endpoint exists)
        print("\nTesting POST request with invalid data...")
        test_data = {"idToken": "invalid_token"}
        post_response = requests.post(
            "http://localhost:8000/api/auth/verify-token-with-google",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"POST Status: {post_response.status_code}")
        print(f"POST Response: {post_response.text}")
        
        # Test if server root is accessible
        print("\nTesting server root...")
        root_response = requests.get("http://localhost:8000/")
        print(f"Root Status: {root_response.status_code}")
        print(f"Root Response: {root_response.text}")
        
        # Test health endpoint
        print("\nTesting health endpoint...")
        health_response = requests.get("http://localhost:8000/health")
        print(f"Health Status: {health_response.status_code}")
        print(f"Health Response: {health_response.text}")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure it's running on localhost:8000")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    test_auth_endpoint() 