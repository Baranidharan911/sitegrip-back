# test_api.py - Comprehensive API Testing Suite

import requests
import json
import time
import uuid
from datetime import datetime

# --- CONFIGURATION ---
API_BASE_URL = "http://127.0.0.1:8000"
TARGET_URL = "https://www.elbrit.org/"
TARGET_DOMAIN = "www.elbrit.org"

# Test settings
SHOW_FULL_JSON = True
SHOW_DETAILED_ANALYSIS = True
MAX_PAGES_DETAILED = 1
TIMEOUT = 300  # 5 minutes

# --- HELPER FUNCTIONS ---

def print_section_header(title, level=1):
    if level == 1:
        print("\n" + "=" * 80)
        print(f"🚀 {title.upper()} 🚀")
        print("=" * 80)
    else:
        print("\n" + "-" * 60)
        print(f"📊 {title}")
        print("-" * 60)

def print_json_response(data, title="RESPONSE"):
    if SHOW_FULL_JSON:
        print(f"\n📦 {title}:")
        print(json.dumps(data, indent=2, default=str))

def make_request(method, url, payload=None, params=None, expected_status=200):
    """Helper function to make API requests with error handling"""
    try:
        if method.upper() == "GET":
            response = requests.get(url, params=params, timeout=TIMEOUT)
        elif method.upper() == "POST":
            response = requests.post(url, json=payload, timeout=TIMEOUT)
        elif method.upper() == "DELETE":
            response = requests.delete(url, params=params, timeout=TIMEOUT)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == expected_status:
            print("✅ Request successful")
            return response.json() if response.content else {}
        else:
            print(f"❌ Request failed with status {response.status_code}")
            return {"error": f"HTTP {response.status_code}", "detail": response.text}
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return {"error": "Request Exception", "detail": str(e)}

# --- ROOT & HEALTH ENDPOINTS ---

def test_root_endpoints():
    """Test root and health check endpoints"""
    print_section_header("Root & Health Check Endpoints")
    
    # Test root endpoint
    print_section_header("1. Root Endpoint", level=2)
    data = make_request("GET", f"{API_BASE_URL}/")
    print_json_response(data, "ROOT ENDPOINT RESPONSE")
    
    # Test health check
    print_section_header("2. Health Check", level=2)
    data = make_request("GET", f"{API_BASE_URL}/health")
    print_json_response(data, "HEALTH CHECK RESPONSE")

# --- AUTHENTICATION ENDPOINTS ---

def test_auth_endpoints():
    """Test authentication endpoints"""
    print_section_header("Authentication Endpoints")
    
    print_section_header("1. Verify Token (Mock)", level=2)
    # Note: This requires a valid Firebase token, so we'll show expected response format
    expected_response = {
        "uid": "sample_user_id",
        "email": "user@example.com", 
        "display_name": "Test User",
        "photo_url": "https://example.com/photo.jpg"
    }
    print("Expected Response Format:")
    print_json_response(expected_response, "AUTH VERIFY TOKEN RESPONSE FORMAT")

# --- CRAWL ENDPOINTS ---

def test_crawl_endpoints():
    """Test crawl-related endpoints"""
    print_section_header("Crawl Endpoints")
    
    print_section_header("1. Full Website Crawl", level=2)
    payload = {
        "url": TARGET_URL,
        "depth": 1,
        "selectedUrls": None
    }
    data = make_request("POST", f"{API_BASE_URL}/api/crawl", payload)
    print_json_response(data, "CRAWL RESPONSE")
    
    # Test with selected URLs
    print_section_header("2. Selective URL Crawl", level=2)
    payload_selective = {
        "url": TARGET_URL,
        "depth": 1,
        "selectedUrls": [TARGET_URL]
    }
    data = make_request("POST", f"{API_BASE_URL}/api/crawl", payload_selective)
    print_json_response(data, "SELECTIVE CRAWL RESPONSE")

# --- DISCOVERY ENDPOINTS ---

def test_discovery_endpoints():
    """Test page discovery endpoints"""
    print_section_header("Discovery Endpoints")
    
    print_section_header("1. Page Discovery", level=2)
    payload = {
        "url": TARGET_URL,
        "depth": 2
    }
    data = make_request("POST", f"{API_BASE_URL}/api/discover", payload)
    print_json_response(data, "DISCOVERY RESPONSE")

# --- HISTORY ENDPOINTS ---

def test_history_endpoints():
    """Test crawl history endpoints"""
    print_section_header("History Endpoints")
    
    print_section_header("1. Get All Crawl History", level=2)
    data = make_request("GET", f"{API_BASE_URL}/api/history")
    print_json_response(data, "CRAWL HISTORY RESPONSE")
    
    print_section_header("2. Get Latest Crawl for URL", level=2)
    params = {"url": TARGET_URL}
    data = make_request("GET", f"{API_BASE_URL}/api/history/latest", params=params)
    print_json_response(data, "LATEST CRAWL RESPONSE")

# --- EXPORT ENDPOINTS ---

def test_export_endpoints():
    """Test export endpoints"""
    print_section_header("Export Endpoints")
    
    print_section_header("1. Export to CSV", level=2)
    # Mock page data for export
    mock_pages = [{
        "url": TARGET_URL,
        "status_code": 200,
        "title": "Sample Page",
        "word_count": 500,
        "issues": ["Missing meta description"],
        "load_time": 1.2,
        "page_size_bytes": 50000,
        "redirect_chain": [],
        "has_viewport": True,
        "suggestions": {
            "title": "Improved Title",
            "description": "Better description",
            "content": "Enhanced content",
            "priority_score": 8,
            "potential_impact": "High",
            "confidence_score": 85,
            "keyword_analysis": {
                "primary_keywords": ["web development", "portfolio"],
                "suggested_keywords": ["responsive design"],
                "missing_keywords": ["SEO"],
                "long_tail_suggestions": ["professional web development portfolio"]
            },
            "content_suggestions": {
                "readability_score": 75,
                "content_gaps": ["More project descriptions needed"]
            }
        }
    }]
    
    try:
        response = requests.post(f"{API_BASE_URL}/api/export/csv", json=mock_pages, timeout=TIMEOUT)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("✅ CSV export successful")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Content-Disposition: {response.headers.get('content-disposition')}")
            print("📄 CSV content preview (first 200 chars):")
            print(response.text[:200] + "..." if len(response.text) > 200 else response.text)
        else:
            print(f"❌ CSV export failed")
    except Exception as e:
        print(f"❌ CSV export error: {e}")

# --- SITEMAP ENDPOINTS ---

def test_sitemap_endpoints():
    """Test sitemap endpoints"""
    print_section_header("Sitemap Endpoints")
    
    print_section_header("1. Visual Sitemap Generation", level=2)
    payload = {"url": TARGET_URL}
    data = make_request("POST", f"{API_BASE_URL}/api/sitemap", payload)
    print_json_response(data, "VISUAL SITEMAP RESPONSE")

# --- KEYWORD ENDPOINTS ---

def test_keyword_endpoints():
    """Test keyword analysis endpoints"""
    print_section_header("Keyword Analysis Endpoints")
    
    # Test keyword analysis
    print_section_header("1. Keyword Analysis", level=2)
    payload = {
        "url": TARGET_URL,
        "body_text": "This is a professional web development portfolio showcasing modern responsive designs and full-stack development skills.",
        "title": "Professional Web Developer Portfolio",
        "meta_description": "Showcasing modern web development projects and skills"
    }
    data = make_request("POST", f"{API_BASE_URL}/api/keywords/analyze", payload)
    print_json_response(data, "KEYWORD ANALYSIS RESPONSE")
    
    # Test keyword comparison
    print_section_header("2. Keyword Comparison", level=2)
    payload = {
        "target_url": TARGET_URL,
        "target_body_text": "Professional web development services for modern businesses",
        "competitor_urls": ["https://competitor1.com", "https://competitor2.com"],
        "competitor_body_texts": ["Competitor 1 web services", "Competitor 2 development"]
    }
    data = make_request("POST", f"{API_BASE_URL}/api/keywords/compare", payload)
    print_json_response(data, "KEYWORD COMPARISON RESPONSE")
    
    # Test keyword recommendations
    print_section_header("3. Keyword Recommendations", level=2)
    payload = {
        "url": TARGET_URL,
        "body_text": "Professional web development portfolio with modern responsive designs"
    }
    data = make_request("POST", f"{API_BASE_URL}/api/keywords/recommend", payload)
    print_json_response(data, "KEYWORD RECOMMENDATIONS RESPONSE")
    
    # Test keyword history
    print_section_header("4. Keyword History", level=2)
    data = make_request("GET", f"{API_BASE_URL}/api/keywords/history/{TARGET_URL}", params={"days": 30})
    print_json_response(data, "KEYWORD HISTORY RESPONSE")
    
    # Test trending keywords
    print_section_header("5. Trending Keywords", level=2)
    data = make_request("GET", f"{API_BASE_URL}/api/keywords/trending", params={"days": 7})
    print_json_response(data, "TRENDING KEYWORDS RESPONSE")
    
    # Test keyword gaps
    print_section_header("6. Keyword Gaps", level=2)
    data = make_request("GET", f"{API_BASE_URL}/api/keywords/gaps/{TARGET_URL}")
    print_json_response(data, "KEYWORD GAPS RESPONSE")
    
    # Test keyword tracking
    print_section_header("7. Start Keyword Tracking", level=2)
    payload = {
        "keywords": ["web development", "portfolio design"],
        "url": TARGET_URL
    }
    data = make_request("POST", f"{API_BASE_URL}/api/keywords/track", payload)
    print_json_response(data, "KEYWORD TRACKING RESPONSE")
    
    # Test keyword performance
    print_section_header("8. Keyword Performance", level=2)
    params = {
        "keywords": ["web development", "portfolio"],
        "days": 90
    }
    data = make_request("GET", f"{API_BASE_URL}/api/keywords/performance/{TARGET_URL}", params=params)
    print_json_response(data, "KEYWORD PERFORMANCE RESPONSE")
    
    # Test domain summary
    print_section_header("9. Domain Keyword Summary", level=2)
    data = make_request("GET", f"{API_BASE_URL}/api/keywords/domain-summary/{TARGET_DOMAIN}")
    print_json_response(data, "DOMAIN KEYWORD SUMMARY RESPONSE")
    
    # Test keyword stats
    print_section_header("10. Keyword Statistics", level=2)
    data = make_request("GET", f"{API_BASE_URL}/api/keywords/stats")
    print_json_response(data, "KEYWORD STATS RESPONSE")

# --- RANKING ENDPOINTS ---

def test_ranking_endpoints():
    """Test ranking and advanced keyword features"""
    print_section_header("Ranking & Advanced Keyword Endpoints")
    
    # Test keyword tracking
    print_section_header("1. Track Keyword Ranking", level=2)
    payload = {
        "keyword": "web development portfolio",
        "url": TARGET_URL,
        "domain": TARGET_DOMAIN
    }
    data = make_request("POST", f"{API_BASE_URL}/api/ranking/track", payload)
    print_json_response(data, "KEYWORD RANKING TRACKING RESPONSE")
    
    # Test keyword volume
    print_section_header("2. Get Keyword Volume", level=2)
    keyword = "web development"
    data = make_request("GET", f"{API_BASE_URL}/api/ranking/volume/{keyword}")
    print_json_response(data, "KEYWORD VOLUME RESPONSE")
    
    # Test ranking history
    print_section_header("3. Get Ranking History", level=2)
    params = {
        "keyword": "web development portfolio",
        "url": TARGET_URL,
        "days": 30
    }
    data = make_request("GET", f"{API_BASE_URL}/api/ranking/history", params=params)
    print_json_response(data, "RANKING HISTORY RESPONSE")
    
    # Test domain profile
    print_section_header("4. Get Domain Keyword Profile", level=2)
    data = make_request("GET", f"{API_BASE_URL}/api/ranking/domain-profile/{TARGET_DOMAIN}")
    print_json_response(data, "DOMAIN KEYWORD PROFILE RESPONSE")
    
    # Test keyword comparison with scoring
    print_section_header("5. Compare Keywords with Scoring", level=2)
    payload = {
        "current_keyword": "web development",
        "proposed_keyword": "professional full-stack development",
        "page_content": "Professional web development services for modern businesses"
    }
    data = make_request("POST", f"{API_BASE_URL}/api/ranking/compare-score", payload)
    print_json_response(data, "KEYWORD COMPARISON SCORE RESPONSE")

# --- MAIN EXECUTION ---

def run_all_tests():
    """Run all API endpoint tests"""
    print("🧪 STARTING COMPREHENSIVE API TESTING SUITE")
    print(f"Target API: {API_BASE_URL}")
    print(f"Target URL: {TARGET_URL}")
    print(f"Target Domain: {TARGET_DOMAIN}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    try:
        # Test all endpoint categories
        test_root_endpoints()
        test_auth_endpoints()
        test_crawl_endpoints()
        test_discovery_endpoints() 
        test_history_endpoints()
        test_export_endpoints()
        test_sitemap_endpoints()
        test_keyword_endpoints()
        test_ranking_endpoints()
        
    except KeyboardInterrupt:
        print("\n⚠️ Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
    
    print("\n" + "="*80)
    print("🎉 COMPREHENSIVE API TESTING COMPLETED 🎉")
    print("="*80)
    print("\n💡 Notes:")
    print("- Some endpoints may require valid authentication tokens")
    print("- AI-powered endpoints may take longer to respond")
    print("- Error responses are expected for some test scenarios")
    print("- Check server logs for detailed error information")

if __name__ == "__main__":
    run_all_tests()
