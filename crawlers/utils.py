from urllib.parse import urljoin, urlparse
from lxml import etree
import requests
from typing import Set, Optional
from bs4 import BeautifulSoup

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
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
        }
        response = requests.get(sitemap_url, headers=headers, timeout=15)
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
                        urls.update(parse_sitemap(loc_text))
                    else:
                        urls.add(loc_text)
            return urls

        elif 'html' in content_type:
            print(f"Warning: Received HTML at {sitemap_url}. Searching for XML links.")
            soup = BeautifulSoup(response.content, 'html.parser')
            sitemap_links = soup.find_all('a', href=lambda href: href and href.endswith('.xml'))
            for link in sitemap_links:
                absolute_link = urljoin(sitemap_url, link['href'])
                print(f"Found potential sitemap link: {absolute_link}. Parsing it.")
                urls.update(parse_sitemap(absolute_link))
            return urls

        else:
            print(f"Warning: Unsupported content type at {sitemap_url}: {content_type}")
            return urls

    except requests.RequestException as e:
        if hasattr(e, 'response') and e.response and e.response.status_code == 404:
            print(f"Info: No sitemap found at {sitemap_url} (404 Not Found).")
        else:
            print(f"Could not fetch sitemap from {sitemap_url}: {e}")
    except etree.XMLSyntaxError as e:
        print(f"Error parsing XML from {sitemap_url}: {e}")

    return urls

def get_sitemap_urls_from_robots(robots_url: str) -> list[str]:
    try:
        res = requests.get(robots_url, timeout=5)
        if res.status_code != 200:
            return []

        lines = res.text.splitlines()
        sitemap_urls = []
        for line in lines:
            if line.strip().lower().startswith("sitemap:"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    raw_url = parts[1].strip()
                    full_url = urljoin(robots_url, raw_url)
                    sitemap_urls.append(full_url)

        return list(set(sitemap_urls))

    except Exception as e:
        print(f"[robots.txt] Failed to fetch or parse: {e}")
        return []
