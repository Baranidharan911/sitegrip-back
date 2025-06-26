"""
Test script for Enhanced AI Suggestions and Keyword Functionality

This script tests the new AI features including:
- Enhanced, well-structured AI suggestions
- Keyword analysis and suggestions
- Keyword comparisons
- Keyword storage functionality
"""

import asyncio
import requests
import json
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8080"  # Change to your server URL
TEST_URL = "https://www.sitegrip.com/"
TEST_CONTENT = """
Welcome to Example Company

Our company provides excellent web development services and digital marketing solutions. 
We specialize in SEO optimization, content marketing, and website design. Our team of 
experts has years of experience in helping businesses grow online.

Services:
- Web Development
- SEO Services  
- Digital Marketing
- Content Creation
- Social Media Management

Contact us today for a free consultation about your digital marketing needs.
"""

async def test_keyword_analysis():
    """Test keyword analysis functionality"""
    print("🔍 Testing Keyword Analysis...")
    
    payload = {
        "url": TEST_URL,
        "body_text": TEST_CONTENT,
        "title": "Digital Marketing Services | Example Company",
        "meta_description": "Professional digital marketing and SEO services to grow your business online."
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/api/keywords/analyze", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Keyword Analysis Success!")
            
            keyword_analysis = data.get('keyword_analysis', {})
            print(f"   Primary Keywords: {keyword_analysis.get('primary_keywords', [])[:5]}")
            print(f"   Suggested Keywords: {keyword_analysis.get('suggested_keywords', [])[:5]}")
            print(f"   Missing Keywords: {keyword_analysis.get('missing_keywords', [])[:3]}")
            print(f"   Long-tail Suggestions: {keyword_analysis.get('long_tail_suggestions', [])[:3]}")
            print(f"   Analysis ID: {data.get('analysis_id')}")
            
            return True
        else:
            print(f"❌ Keyword Analysis Failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Keyword Analysis Error: {e}")
        return False

def test_keyword_comparison():
    """Test keyword comparison functionality"""
    print("\n🆚 Testing Keyword Comparison...")
    
    payload = {
        "target_url": TEST_URL,
        "target_body_text": TEST_CONTENT,
        "competitor_urls": [
            "https://competitor1.com",
            "https://competitor2.com"
        ],
        "competitor_body_texts": [
            "Competitor 1 offers digital marketing, SEO services, web design, and online advertising solutions.",
            "Competitor 2 specializes in search engine optimization, pay-per-click advertising, and social media marketing."
        ]
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/api/keywords/compare", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Keyword Comparison Success!")
            
            comparison = data.get('comparison', {})
            print(f"   Shared Keywords: {comparison.get('shared_keywords', [])[:5]}")
            print(f"   Unique Opportunities: {comparison.get('unique_opportunities', [])[:3]}")
            print(f"   Keyword Gaps: {comparison.get('keyword_gaps', [])[:3]}")
            print(f"   Comparison ID: {data.get('comparison_id')}")
            
            return True
        else:
            print(f"❌ Keyword Comparison Failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Keyword Comparison Error: {e}")
        return False

def test_enhanced_crawl():
    """Test enhanced crawl with new AI suggestions"""
    print("\n🚀 Testing Enhanced Crawl with AI Suggestions...")
    
    payload = {
        "url": "https://example.com",
        "depth": 1
    }
    
    try:
        response = requests.post(f"{API_BASE_URL}/api/crawl", json=payload)
        
        if response.status_code == 200:
            print("✅ Enhanced Crawl Success!")
            data = response.json()
            
            pages = data.get('pages', [])
            if pages:
                page = pages[0]
                suggestions = page.get('suggestions', {})
                
                print(f"   📄 Page: {page.get('url')}")
                print(f"   📝 AI Title: {suggestions.get('title', 'N/A')}")
                print(f"   📈 Priority Score: {suggestions.get('priority_score', 'N/A')}")
                print(f"   💪 Potential Impact: {suggestions.get('potential_impact', 'N/A')}")
                print(f"   🎯 Confidence Score: {suggestions.get('confidence_score', 'N/A')}")
                
                # Enhanced keyword analysis
                keyword_analysis = suggestions.get('keyword_analysis', {})
                if keyword_analysis:
                    print(f"   🔑 Primary Keywords: {keyword_analysis.get('primary_keywords', [])[:3]}")
                    print(f"   💡 Suggested Keywords: {keyword_analysis.get('suggested_keywords', [])[:3]}")
                
                # Content suggestions
                content_suggestions = suggestions.get('content_suggestions', {})
                if content_suggestions:
                    print(f"   📊 Readability Score: {content_suggestions.get('readability_score', 'N/A')}")
                    print(f"   🔧 Structure Improvements: {len(content_suggestions.get('structure_improvements', []))}")
                
                # Technical SEO
                technical_seo = suggestions.get('technical_seo', {})
                if technical_seo:
                    print(f"   ⚡ Performance Suggestions: {len(technical_seo.get('performance_suggestions', []))}")
                    print(f"   ♿ Accessibility Improvements: {len(technical_seo.get('accessibility_improvements', []))}")
            
            return True
        else:
            print(f"❌ Enhanced Crawl Failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Enhanced Crawl Error: {e}")
        return False

def test_keyword_trending():
    """Test trending keywords functionality"""
    print("\n📈 Testing Trending Keywords...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/keywords/trending?days=7")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Trending Keywords Success!")
            
            trending = data.get('trending_keywords', {})
            print(f"   📊 Total Keywords: {data.get('total_keywords', 0)}")
            print(f"   🔥 Top Trending: {list(trending.keys())[:5] if trending else 'None'}")
            
            return True
        else:
            print(f"❌ Trending Keywords Failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Trending Keywords Error: {e}")
        return False

def test_keyword_stats():
    """Test keyword statistics"""
    print("\n📊 Testing Keyword Statistics...")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/keywords/stats")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Keyword Statistics Success!")
            
            stats = data.get('statistics', {})
            print(f"   📈 Total Analyses: {stats.get('total_keyword_analyses', 0)}")
            print(f"   🆚 Total Comparisons: {stats.get('total_keyword_comparisons', 0)}")
            print(f"   📊 Tracking Records: {stats.get('total_tracking_records', 0)}")
            
            return True
        else:
            print(f"❌ Keyword Statistics Failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Keyword Statistics Error: {e}")
        return False

async def run_all_tests():
    """Run all tests"""
    print("🧪 Starting Enhanced AI & Keyword Functionality Tests")
    print("=" * 60)
    
    test_results = []
    
    # Test keyword analysis
    result1 = await test_keyword_analysis()
    test_results.append(result1)
    
    # Test keyword comparison
    result2 = test_keyword_comparison()
    test_results.append(result2)
    
    # Test enhanced crawl
    result3 = test_enhanced_crawl()
    test_results.append(result3)
    
    # Test trending keywords
    result4 = test_keyword_trending()
    test_results.append(result4)
    
    # Test keyword stats
    result5 = test_keyword_stats()
    test_results.append(result5)
    
    # Summary
    print("\n" + "=" * 60)
    print("🏁 Test Results Summary")
    print("=" * 60)
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced AI functionality is working correctly.")
    else:
        print("⚠️ Some tests failed. Please check the error messages above.")
    
    print("\n📋 Test Coverage:")
    print("   ✓ Enhanced AI Suggestions Structure")
    print("   ✓ Keyword Analysis & Suggestions")
    print("   ✓ Keyword Comparison")
    print("   ✓ Keyword Storage & Retrieval")
    print("   ✓ Trending Keywords")
    print("   ✓ Keyword Statistics")

if __name__ == "__main__":
    print("🔧 Enhanced AI & Keyword Functionality Test Suite")
    print(f"🌐 Testing against: {API_BASE_URL}")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}") 