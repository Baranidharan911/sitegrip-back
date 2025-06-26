from playwright.async_api import async_playwright, Page, Browser, Response
from typing import Set, List
from .utils import normalize_url, is_same_origin, parse_sitemap, get_sitemap_urls_from_robots
from models.page_data import PageData
import asyncio
import time
from urllib.parse import urljoin
from urllib.parse import urljoin
from collections import defaultdict



def is_html_url(url: str) -> bool:
    skip_extensions = (
        ".pdf", ".zip", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mp3", ".avi", ".exe"
    )
    return not any(url.lower().endswith(ext) for ext in skip_extensions)

MOBILE_VIEWPORT = {"width": 375, "height": 667}

class SiteCrawler:
    def __init__(self, base_url: str, depth: int):
        self.base_url = base_url
        self.depth = depth
        self.crawled_urls: Set[str] = set()
        self.results: List[PageData] = []
        self.sitemap_urls: Set[str] = set()
        self.pending_urls: List[tuple[str, int]] = []
        self.linked_from_map = defaultdict(set)
        

    async def crawl_site(self):
        robots_url = urljoin(self.base_url, "/robots.txt")
        sitemap_urls = get_sitemap_urls_from_robots(robots_url)

        if not sitemap_urls:
            print("⚠️ No Sitemap found in robots.txt, falling back to default /sitemap.xml")
            sitemap_urls = [urljoin(self.base_url, "/sitemap.xml")]

        self.sitemap_urls = set()

        for sitemap in sitemap_urls:
            parsed_urls = parse_sitemap(sitemap)
            if parsed_urls:
                self.sitemap_urls.update(parsed_urls)

        print(f"✅ Found {len(self.sitemap_urls)} URLs in sitemap(s).")

        self.pending_urls.append((self.base_url, 0))

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            while self.pending_urls:
                url, current_depth = self.pending_urls.pop(0)
                await self._crawl_page(url, current_depth, browser)
            await browser.close()

        if len(self.results) < 2 and self.sitemap_urls:
            print("⚠️ Not enough pages crawled. Falling back to sitemap URLs...")
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                for url in self.sitemap_urls:
                    if url not in self.crawled_urls:
                        await self._crawl_page(url, 1, browser)
                await browser.close()

        return self.results, self.sitemap_urls

    async def _crawl_page(self, url: str, current_depth: int, browser: Browser):
        if not is_html_url(url):
            print(f"⏩ Skipping non-HTML resource: {url}")
            return

        normalized_url = normalize_url(self.base_url, url)
        if current_depth > self.depth or normalized_url in self.crawled_urls or not is_same_origin(self.base_url, normalized_url):
            return

        self.crawled_urls.add(normalized_url)
        page_data = await self._extract_page_data(normalized_url, browser, current_depth)
        if not page_data:
            return

        # Track backlinks (who links to whom)
        for link in page_data.internal_links:
            normalized_link = normalize_url(self.base_url, link)
            self.linked_from_map[normalized_link].add(page_data.url)

        # Append this page to results
        self.results.append(page_data)

        # Inject `linked_from` data into already-crawled pages
        for result in self.results:
            if result.url in self.linked_from_map:
                result.linked_from = list(self.linked_from_map[result.url])

        # Queue next-level internal links
        if current_depth < self.depth:
            for link in page_data.internal_links:
                normalized_link = normalize_url(self.base_url, link)
                if normalized_link not in self.crawled_urls:
                    self.pending_urls.append((normalized_link, current_depth + 1))


    async def _extract_page_data(self, url: str, browser: Browser, depth: int) -> PageData | None:

        context = await browser.new_context(
            viewport=MOBILE_VIEWPORT,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Mobile/15E148 Safari/604.1"
        )
        page = await context.new_page()
        page.set_default_timeout(10000)
        page.set_default_navigation_timeout(60000)

        page_size_bytes = 0
        ttfb = 0.0
        lcp = 0.0
        cls = 0.0
        console_errors: List[str] = []

        # 🐞 JS Console Error Listener
        def handle_console(msg):
            try:
                if msg.type == "error":
                    console_errors.append(msg.text)
            except Exception:
                pass
        
        page.on("console", handle_console)

        def handle_response(response: Response):
            nonlocal page_size_bytes, ttfb
            if response.ok:
                try:
                    page_size_bytes += response.body_size()
                    if response.url == url and response.timing():
                        timing = response.timing()
                        if "responseStart" in timing and "startTime" in timing:
                            ttfb = max(0.0, (timing["responseStart"] - timing["startTime"]) / 1000)
                except Exception:
                    pass

        page.on("response", handle_response)

        status_code = 500
        redirect_chain = []
        response = None
        start_time = time.time()

        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=120000)
        except Exception as e:
            print(f"Could not load page {url}: {e}")
            await context.close()
            return None

        load_time = time.time() - start_time

        try:
            await page.evaluate("""
                window.lcp = 0;
                window.cls = 0;
                new PerformanceObserver((entryList) => {
                for (const entry of entryList.getEntries()) {
                    if (entry.entryType === 'largest-contentful-paint') {
                    window.lcp = entry.renderTime || entry.loadTime;
                    }
                    if (entry.entryType === 'layout-shift' && !entry.hadRecentInput) {
                    window.cls += entry.value;
                    }
                }
                }).observe({ type: 'largest-contentful-paint', buffered: true });
                new PerformanceObserver((entryList) => {
                for (const entry of entryList.getEntries()) {
                    if (entry.entryType === 'layout-shift' && !entry.hadRecentInput) {
                    window.cls += entry.value;
                    }
                }
                }).observe({ type: 'layout-shift', buffered: true });
            """)
        except Exception as e:
            print(f"[warn] Could not inject LCP/CLS observer: {e}")

        if response:
            status_code = response.status
            if response.request and hasattr(response.request, 'redirect_chain'):
                redirect_chain = [r.url for r in response.request.redirect_chain]

            if status_code < 400:
                title = await page.title()
                try:
                    meta_description = await page.locator('meta[name="description"]').get_attribute("content")
                except:
                    meta_description = None

                h1_count = await page.locator('h1').count()
                try:
                    body_text = await page.locator('body').inner_text()
                except:
                    body_text = ""
                word_count = len(body_text.split())
                images_without_alt = await page.locator('img:not([alt]), img[alt=""]').count()
                layout_width = await page.evaluate("document.body.scrollWidth")
                has_viewport = layout_width <= (MOBILE_VIEWPORT["width"] + 5)

                links = await page.locator('a[href]').evaluate_all('(elements) => elements.map(el => el.href)')
                internal_links = {
                    normalize_url(self.base_url, link)
                    for link in links if is_same_origin(self.base_url, link)
                }

                try:
                    lcp = await page.evaluate("window.lcp / 1000")
                    cls = await page.evaluate("window.cls")
                except:
                    pass
            else:
                title, meta_description, body_text = None, None, ""
                h1_count, word_count, images_without_alt, internal_links, has_viewport = 0, 0, 0, set(), False
        else:
            title, meta_description, body_text = None, None, ""
            h1_count, word_count, images_without_alt, internal_links, has_viewport = 0, 0, 0, set(), False

        # 📱 Take mobile screenshot
        # 📱 Take mobile screenshot
        # try:
        #     mobile_bytes = await page.screenshot(full_page=True, type="png")
        #     import base64
        #     mobile_screenshot = base64.b64encode(mobile_bytes).decode("utf-8")
        # except Exception as e:
        #     print(f"[warn] Failed to capture mobile screenshot for {url}: {e}")
        #     mobile_screenshot = None

        # await context.close()

        # # 🖥️ Take desktop screenshot in a new context
        # try:
        #     desktop_context = await browser.new_context(
        #         viewport={"width": 1280, "height": 800},
        #         user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        #     )
        #     desktop_page = await desktop_context.new_page()
        #     await desktop_page.goto(url, wait_until="domcontentloaded", timeout=60000)
        #     desktop_bytes = await desktop_page.screenshot(full_page=True, type="png")
        #     desktop_screenshot = base64.b64encode(desktop_bytes).decode("utf-8")
        #     await desktop_context.close()
        # except Exception as e:
        #     print(f"[warn] Failed to capture desktop screenshot for {url}: {e}")
        #     desktop_screenshot = None


        await context.close()

        return PageData(
            url=url,
            statusCode=status_code,
            title=title,
            metaDescription=meta_description,
            wordCount=word_count,
            h1Count=h1_count,
            imageWithoutAltCount=images_without_alt,
            internalLinks=list(internal_links),
            redirectChain=redirect_chain,
            loadTime=load_time,
            pageSizeBytes=page_size_bytes,
            hasViewport=has_viewport,
            body_text=body_text,
            ttfb=ttfb,
            lcp=lcp,
            cls=cls,
            console_errors=console_errors,  # ✅ Added
            depth=depth,
            # mobile_screenshot=mobile_screenshot,
            # desktop_screenshot=desktop_screenshot
        )
