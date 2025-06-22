# test_api.py

import requests
import json
import time

API_BASE_URL = "http://127.0.0.1:8000"
CRAWL_ENDPOINT = f"{API_BASE_URL}/api/crawl"
TARGET_URL = "https://portfolio-xi-dusky-67.vercel.app/"

def run_test():
    print(f"▶️  Starting API test...")
    print(f" Target: {CRAWL_ENDPOINT}")
    print(f" Crawling: {TARGET_URL}")

    payload = {
        "url": TARGET_URL,
        "depth": 1
    }

    try:
        start_time = time.time()
        response = requests.post(CRAWL_ENDPOINT, json=payload, timeout=300)
        duration = time.time() - start_time

        print(f"\n✅ Request completed in {duration:.2f} seconds.")
        print(f"   HTTP Status Code: {response.status_code}")

        if response.status_code == 200:
            crawl_data = response.json()

            summary = crawl_data.get("summary", {})
            pages = crawl_data.get("pages", [])
            sitemap_urls = crawl_data.get("sitemapUrls", [])

            print("\n📊 --- Crawl Summary ---")
            print(f"Crawl ID: {crawl_data.get('crawlId')}")
            print(f"Pages Crawled: {len(pages)}")
            print(f"URLs in Sitemap: {len(sitemap_urls)}")
            print("-" * 20)
            print(f"Total Pages: {summary.get('totalPages')}")
            print(f"Mobile Friendly: {summary.get('mobileFriendlyPages')}")
            print(f"Slow Pages (>2.5s): {summary.get('pagesWithSlowLoad')}")
            print(f"Orphan Pages: {summary.get('orphanPages')}")
            print(f"Redirect Chains: {summary.get('redirectChains')}")
            print(f"Broken Links: {summary.get('brokenLinks')}")
            print("-" * 20)
            print(f"Missing Titles: {summary.get('missingTitles')}")
            print(f"Duplicate Titles: {summary.get('duplicateTitles')}")
            print(f"Duplicate Descriptions: {summary.get('duplicateDescriptions')}")
            print(f"Low Word Count Pages: {summary.get('lowWordCountPages')}")
            print("-" * 20)

            # Print preview of up to 3 pages
            for idx, page in enumerate(pages[:3]):
                print(f"\n🔍 --- Page #{idx + 1} ---")
                print(f"URL: {page.get('url')}")
                print(f"Status: {page.get('statusCode')}")
                print(f"Load Time: {page.get('loadTime', 0):.2f}s")
                print(f"Page Size: {page.get('pageSizeBytes', 0)} bytes")
                print(f"Mobile Friendly: {page.get('hasViewport')}")
                print(f"Redirect Chain: {page.get('redirectChain')}")
                print(f"Issues: {page.get('issues') or 'None'}")

                suggestions = page.get('suggestions')
                if suggestions:
                    print("\n🤖 AI Suggestions:")
                    print(f"  • Title: {suggestions.get('title')}")
                    print(f"  • Description: {suggestions.get('description')}")
                    print(f"  • Content: {suggestions.get('content')}")
                else:
                    print("🤖 AI Suggestions: None")

            # Optional: Uncomment to print full JSON
            # print("\n📦 --- Full JSON Response ---")
            # print(json.dumps(crawl_data, indent=2))

        else:
            print(f"\n❌ Error: API returned {response.status_code}")
            try:
                error_details = response.json()
                print(json.dumps(error_details, indent=2))
            except json.JSONDecodeError:
                print("   Raw response:")
                print(response.text)

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Could not connect to {API_BASE_URL}")
        print(f"   Error: {e}")

if __name__ == "__main__":
    run_test()
