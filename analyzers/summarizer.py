# backend/analyzers/summarizer.py
from typing import List, Set
from models.page_data import PageData
from models.crawl_result import CrawlSummary

class SummarizerService:
    def generate_summary(self, pages: List[PageData], sitemap_urls: Set[str], crawled_urls: Set[str]) -> CrawlSummary:
        """
        Generates a summary report from a list of analyzed page data.
        """
        summary_data = {
            "totalPages": len(pages),
            "missingTitles": 0,
            "lowWordCountPages": 0,
            "brokenLinks": 0,
            "duplicateTitles": 0,
            "duplicateDescriptions": 0,
            "redirectChains": 0,
            "mobileFriendlyPages": 0,
            "nonMobilePages": 0,
            "pagesWithSlowLoad": 0,
            "orphanPages": 0,
            "averageSeoScore": 100  # 👈 default to 100 unless calculated below
        }

        pages_with_duplicate_titles = set()
        pages_with_duplicate_descriptions = set()

        total_score = 0

        for page in pages:
            total_score += getattr(page, "seo_score", 100)

            if "missingTitle" in page.issues:
                summary_data["missingTitles"] += 1
            if "lowWordCount" in page.issues:
                summary_data["lowWordCountPages"] += 1
            if any("brokenLink" in issue for issue in page.issues):
                summary_data["brokenLinks"] += 1
            if "duplicateTitle" in page.issues:
                pages_with_duplicate_titles.add(page.title)
            if "duplicateDescription" in page.issues:
                pages_with_duplicate_descriptions.add(page.meta_description)
            if any("redirectChain" in issue for issue in page.issues):
                summary_data["redirectChains"] += 1
            if page.has_viewport:
                summary_data["mobileFriendlyPages"] += 1
            else:
                summary_data["nonMobilePages"] += 1
            if any("slowLoad" in issue for issue in page.issues):
                summary_data["pagesWithSlowLoad"] += 1

        summary_data["duplicateTitles"] = len(pages_with_duplicate_titles)
        summary_data["duplicateDescriptions"] = len(pages_with_duplicate_descriptions)

        if sitemap_urls:
            orphan_urls = sitemap_urls - crawled_urls
            summary_data["orphanPages"] = len(orphan_urls)

        if pages:
            summary_data["averageSeoScore"] = round(total_score / len(pages))

        return CrawlSummary(**summary_data)

# Instantiate the service
summarizer_service = SummarizerService()
