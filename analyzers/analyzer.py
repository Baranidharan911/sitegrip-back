# backend/analyzers/analyzer.py
from typing import List, Dict
from models.page_data import PageData

# Constants for analysis thresholds
LOW_WORD_COUNT_THRESHOLD = 100
SLOW_LOAD_TIME_THRESHOLD = 2.5  # seconds

class SEOAnalyzer:
    def __init__(self, all_pages_data: List[PageData]):
        self.all_pages_data = all_pages_data
        self.title_map: Dict[str, int] = {}
        self.description_map: Dict[str, int] = {}
        self._build_global_maps()

    def _build_global_maps(self):
        """
        Builds maps of titles and descriptions to detect duplicates across the site.
        """
        for page in self.all_pages_data:
            if page.title:
                self.title_map[page.title] = self.title_map.get(page.title, 0) + 1
            if page.meta_description:
                self.description_map[page.meta_description] = self.description_map.get(page.meta_description, 0) + 1

    def analyze_page(self, page_data: PageData) -> PageData:
        """
        Analyzes a single page for SEO issues and updates its 'issues' field and 'seo_score'.
        """
        issues = []
        total_deduction = 0

        # Define severity weights
        severity_weights = {
            "missingTitle": 30,
            "duplicateTitle": 20,
            "missingMeta": 20,
            "duplicateDescription": 10,
            "lowWordCount": 10,
            "h1CountMismatch": 10,
            "imagesMissingAlt": 5,
            "brokenLink": 30,
            "redirectChain": 10,
            "notMobileFriendly": 15,
            "slowLoad": 10
        }

        if not page_data.title:
            issues.append("missingTitle")
            total_deduction += severity_weights["missingTitle"]
        elif self.title_map.get(page_data.title, 0) > 1:
            issues.append("duplicateTitle")
            total_deduction += severity_weights["duplicateTitle"]

        if not page_data.meta_description:
            issues.append("missingMeta")
            total_deduction += severity_weights["missingMeta"]
        elif self.description_map.get(page_data.meta_description, 0) > 1:
            issues.append("duplicateDescription")
            total_deduction += severity_weights["duplicateDescription"]

        if page_data.word_count < LOW_WORD_COUNT_THRESHOLD:
            issues.append("lowWordCount")
            total_deduction += severity_weights["lowWordCount"]

        if page_data.h1_count != 1:
            issues.append(f"h1CountMismatch:{page_data.h1_count}")
            total_deduction += severity_weights["h1CountMismatch"]

        if page_data.images_without_alt_count > 0:
            issues.append("imagesMissingAlt")
            total_deduction += severity_weights["imagesMissingAlt"]

        if page_data.status_code >= 400:
            issues.append(f"brokenLink:{page_data.status_code}")
            total_deduction += severity_weights["brokenLink"]

        if len(page_data.redirect_chain) > 1:
            issues.append(f"redirectChain:{len(page_data.redirect_chain)}")
            total_deduction += severity_weights["redirectChain"]

        if not page_data.has_viewport:
            issues.append("notMobileFriendly")
            total_deduction += severity_weights["notMobileFriendly"]

        if page_data.load_time > SLOW_LOAD_TIME_THRESHOLD:
            issues.append(f"slowLoad:{page_data.load_time:.2f}s")
            total_deduction += severity_weights["slowLoad"]

        # Clamp the SEO score to a minimum of 0
        seo_score = max(0, 100 - total_deduction)

        page_data.issues = issues
        page_data.seo_score = seo_score
        return page_data

    def run_analysis(self) -> List[PageData]:
        """
        Runs the analysis for all pages and computes their SEO score.
        """
        analyzed_pages = [self.analyze_page(page) for page in self.all_pages_data]
        return analyzed_pages
