from urllib.parse import urljoin, urlparse
from lxml import etree
import requests
from typing import Set, Optional
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; SiteGripBot/1.0; +https://sitegrip.com/bot)'
}

def normalize_url(base_url: str, link: str) -> str:
    absolute_link = urljoin(base_url, link)
    parsed_link = urlparse(absolute_link)
    return parsed_link._replace(fragment="").geturl()

def is_same_origin(base_url: str, target_url: str) -> bool:
    return urlparse(base_url).netloc == urlparse(target_url).netloc

def get_root_domain(url: str) -> str:
    parsed = urlparse(str(url))
    return f"{parsed.scheme}://{parsed.netloc}"

def parse_sitemap(sitemap_url: str) -> Set[str]:
    urls: Set[str] = set()
    if not sitemap_url:
        return urls

    try:
        response = requests.get(sitemap_url, headers=HEADERS, timeout=15)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', '').lower()

        if 'xml' in content_type:
            root = etree.fromstring(response.content)
            namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            locs = root.xpath('//ns:loc', namespaces=namespace)
            for loc in locs:
                if loc.text:
                    loc_text = loc.text.strip()
                    if loc_text.endswith('.xml'):
                        urls.update(parse_sitemap(loc_text))  # Recursive parse
                    else:
                        urls.add(loc_text)

        elif 'html' in content_type:
            print(f"[sitemap] ⚠️ Received HTML at {sitemap_url}. Looking for .xml links.")
            soup = BeautifulSoup(response.content, 'html.parser')
            sitemap_links = soup.find_all('a', href=lambda href: href and href.endswith('.xml'))
            for link in sitemap_links:
                absolute_link = urljoin(sitemap_url, link['href'])
                print(f"[sitemap] ➕ Found nested sitemap: {absolute_link}")
                urls.update(parse_sitemap(absolute_link))

        else:
            print(f"[sitemap] ⚠️ Unsupported content type at {sitemap_url}: {content_type}")

    except requests.RequestException as e:
        if hasattr(e, 'response') and e.response and e.response.status_code == 404:
            print(f"[sitemap] ℹ️ No sitemap found at {sitemap_url} (404).")
        else:
            print(f"[sitemap] ❌ Could not fetch {sitemap_url}: {e}")
    except etree.XMLSyntaxError as e:
        print(f"[sitemap] ❌ XML parse error at {sitemap_url}: {e}")

    return urls

def get_sitemap_urls_from_robots(robots_url: str) -> list[str]:
    try:
        response = requests.get(robots_url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"[robots.txt] ⚠️ Non-200 status: {response.status_code}")
            return []

        sitemap_urls = []
        lines = response.text.splitlines()
        for line in lines:
            if line.strip().lower().startswith("sitemap:"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    raw_url = parts[1].strip()
                    full_url = urljoin(robots_url, raw_url)
                    sitemap_urls.append(full_url)

        return list(set(sitemap_urls))

    except Exception as e:
        print(f"[robots.txt] ❌ Failed to fetch or parse: {e}")
        return []
