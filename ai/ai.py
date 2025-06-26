# backend/ai/ai.py

import asyncio
import google.generativeai as genai
import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional, List, Dict, Set
from collections import Counter
from models.page_data import AISuggestions, PageData, KeywordAnalysis, ContentSuggestions, TechnicalSEO, KeywordComparison

load_dotenv()

class AIService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("Warning: GEMINI_API_KEY not found in .env. AI suggestions will be disabled.")
            self.model = None
        else:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
    
    def _extract_keywords_from_text(self, text: str, min_length: int = 3) -> List[str]:
        """Extract potential keywords from text content."""
        if not text:
            return []
        
        # Remove HTML tags and special characters
        clean_text = re.sub(r'<[^>]+>', '', text.lower())
        clean_text = re.sub(r'[^\w\s]', ' ', clean_text)
        
        # Extract words
        words = [word.strip() for word in clean_text.split() if len(word.strip()) >= min_length]
        
        # Count frequency and return top keywords
        word_freq = Counter(words)
        return [word for word, _ in word_freq.most_common(20)]
    
    def _calculate_keyword_density(self, text: str, keywords: List[str]) -> Dict[str, float]:
        """Calculate keyword density for given keywords in text."""
        if not text or not keywords:
            return {}
        
        clean_text = re.sub(r'<[^>]+>', '', text.lower())
        word_count = len(clean_text.split())
        
        densities = {}
        for keyword in keywords:
            keyword_count = clean_text.count(keyword.lower())
            densities[keyword] = round((keyword_count / word_count) * 100, 2) if word_count > 0 else 0.0
        
        return densities
    
    def _generate_long_tail_keywords(self, primary_keywords: List[str], url: str) -> List[str]:
        """Generate long-tail keyword suggestions based on primary keywords and URL context."""
        long_tail = []
        
        # Extract page type from URL
        url_parts = url.split('/')
        page_context = []
        
        for part in url_parts:
            if part and not part.startswith(('http', 'www')):
                page_context.extend(part.replace('-', ' ').replace('_', ' ').split())
        
        # Combine primary keywords with context
        for keyword in primary_keywords[:5]:  # Top 5 primary keywords
            for context in page_context[:3]:  # Top 3 context words
                if context != keyword and len(context) > 2:
                    long_tail.append(f"{keyword} {context}")
                    long_tail.append(f"{context} {keyword}")
                    long_tail.append(f"best {keyword} {context}")
                    long_tail.append(f"how to {keyword} {context}")
        
        return list(set(long_tail))[:10]  # Return unique top 10

    async def _generate_keyword_analysis(self, page_data: PageData) -> Optional[KeywordAnalysis]:
        """Generate comprehensive keyword analysis with fallback for when AI is unavailable."""
        # Extract existing keywords from available content
        primary_keywords = self._extract_keywords_from_text(page_data.body_text or "")
        title_keywords = self._extract_keywords_from_text(page_data.title or "")
        meta_keywords = self._extract_keywords_from_text(page_data.meta_description or "")
        
        # If we have no content at all, try to extract from URL
        if not primary_keywords and not title_keywords and not meta_keywords:
            url_keywords = self._extract_keywords_from_url(page_data.url)
            primary_keywords = url_keywords
        
        # Calculate keyword density
        all_keywords = list(set(primary_keywords + title_keywords + meta_keywords))
        keyword_density = self._calculate_keyword_density(page_data.body_text or "", all_keywords)
        
        # Generate long-tail suggestions
        long_tail_suggestions = self._generate_long_tail_keywords(primary_keywords, page_data.url)
        
        # Try AI analysis if model is available
        ai_keywords = {}
        if self.model:
            try:
                ai_keywords = await self._get_ai_keyword_suggestions(page_data, primary_keywords)
            except Exception as e:
                print(f"[AI ERROR] Keyword analysis failed for {page_data.url}: {e}")
                # Continue with fallback analysis
        
        # Prepare fallback suggestions if AI failed
        if not ai_keywords:
            ai_keywords = self._generate_fallback_keywords(primary_keywords, page_data)
        
        return KeywordAnalysis(
            primary_keywords=primary_keywords[:15],
            suggested_keywords=ai_keywords.get("suggested_keywords", []),
            keyword_density=keyword_density,
            missing_keywords=ai_keywords.get("missing_keywords", []),
            competitor_keywords=ai_keywords.get("competitor_keywords", []),
            long_tail_suggestions=long_tail_suggestions
        )

    def _extract_keywords_from_url(self, url: str) -> List[str]:
        """Extract potential keywords from URL structure."""
        if not url:
            return []
        
        # Remove protocol and www
        clean_url = url.replace('https://', '').replace('http://', '').replace('www.', '')
        
        # Extract domain and path parts
        parts = clean_url.replace('-', ' ').replace('_', ' ').replace('/', ' ').split()
        
        # Filter out common web terms and short words
        excluded = {'com', 'org', 'net', 'html', 'php', 'asp', 'htm', 'index', 'www'}
        keywords = [part.lower() for part in parts if len(part) > 2 and part.lower() not in excluded]
        
        return keywords[:10]

    async def _get_ai_keyword_suggestions(self, page_data: PageData, primary_keywords: List[str]) -> Dict:
        """Get AI-powered keyword suggestions with improved error handling."""
        keyword_prompt = f"""
        Analyze this webpage content and suggest SEO keywords:
        
        URL: {page_data.url}
        Title: {page_data.title or "No title"}
        Meta Description: {page_data.meta_description or "No meta description"}
        Content Sample: {(page_data.body_text or "")[:1500]}
        Current Keywords: {primary_keywords[:10]}
        
        Please suggest:
        1. 5-10 high-value keywords this page should target
        2. 5-10 keywords that are missing but should be included
        3. 5 competitor-style keywords for this topic
        
        Return as JSON:
        {{
            "suggested_keywords": ["keyword1", "keyword2", ...],
            "missing_keywords": ["missing1", "missing2", ...],
            "competitor_keywords": ["comp1", "comp2", ...]
        }}
        """
        
        response = await self.model.generate_content_async(keyword_prompt)
        cleaned = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)

    def _generate_fallback_keywords(self, primary_keywords: List[str], page_data: PageData) -> Dict:
        """Generate fallback keyword suggestions when AI is unavailable."""
        suggested_keywords = []
        missing_keywords = []
        competitor_keywords = []
        
        # Generate suggestions based on URL and content
        url_parts = page_data.url.split('/')
        domain_keywords = []
        
        for part in url_parts:
            if part and not part.startswith(('http', 'www')):
                domain_keywords.extend(part.replace('-', ' ').replace('_', ' ').split())
        
        # Suggest variations of primary keywords
        for keyword in primary_keywords[:5]:
            suggested_keywords.extend([
                f"best {keyword}",
                f"{keyword} services",
                f"professional {keyword}",
                f"{keyword} solutions"
            ])
        
        # Missing keywords based on common SEO patterns
        if 'services' not in ' '.join(primary_keywords).lower():
            missing_keywords.append('services')
        if 'professional' not in ' '.join(primary_keywords).lower():
            missing_keywords.append('professional')
        if 'quality' not in ' '.join(primary_keywords).lower():
            missing_keywords.append('quality')
        
        # Competitor-style keywords
        competitor_keywords = [
            'industry leading',
            'top rated',
            'expert',
            'trusted',
            'reliable'
        ]
        
        return {
            "suggested_keywords": suggested_keywords[:10],
            "missing_keywords": missing_keywords[:10],
            "competitor_keywords": competitor_keywords[:5]
        }

    async def _generate_content_suggestions(self, page_data: PageData) -> Optional[ContentSuggestions]:
        """Generate detailed content improvement suggestions."""
        if not self.model:
            return None
        
        content_prompt = f"""
        Analyze this webpage for content improvements:
        
        URL: {page_data.url}
        Title: {page_data.title or "No title"}
        Word Count: {page_data.word_count}
        Content Sample: {(page_data.body_text or "")[:2000]}
        Current Issues: {page_data.issues}
        
        Provide specific suggestions for:
        1. Content structure improvements (3-5 specific recommendations)
        2. Readability score (0-100, where 100 is perfect)
        3. Content gaps (topics/sections missing)
        4. Optimization tips (actionable improvements)
        
        Return as JSON:
        {{
            "structure_improvements": ["improvement1", "improvement2", ...],
            "readability_score": 75,
            "content_gaps": ["gap1", "gap2", ...],
            "optimization_tips": ["tip1", "tip2", ...]
        }}
        """
        
        try:
            response = await self.model.generate_content_async(content_prompt)
            cleaned = response.text.strip().replace("```json", "").replace("```", "").strip()
            content_data = json.loads(cleaned)
            
            return ContentSuggestions(**content_data)
        except Exception as e:
            print(f"[AI ERROR] Content suggestions failed for {page_data.url}: {e}")
            return ContentSuggestions(
                readability_score=60,
                optimization_tips=["Improve content structure", "Add more relevant keywords"]
            )

    async def _generate_technical_seo(self, page_data: PageData) -> Optional[TechnicalSEO]:
        """Generate technical SEO recommendations."""
        if not self.model:
            return None
        
        technical_prompt = f"""
        Analyze technical SEO aspects for this page:
        
        URL: {page_data.url}
        Load Time: {page_data.load_time}s
        Page Size: {page_data.page_size_bytes} bytes
        Has Viewport: {page_data.has_viewport}
        Issues: {page_data.issues}
        Console Errors: {page_data.console_errors}
        
        Provide specific recommendations for:
        1. Schema markup suggestions
        2. Performance improvements
        3. Accessibility enhancements
        4. Mobile optimizations
        
        Return as JSON:
        {{
            "schema_markup_suggestions": ["suggestion1", "suggestion2", ...],
            "performance_suggestions": ["perf1", "perf2", ...],
            "accessibility_improvements": ["acc1", "acc2", ...],
            "mobile_optimizations": ["mobile1", "mobile2", ...]
        }}
        """
        
        try:
            response = await self.model.generate_content_async(technical_prompt)
            cleaned = response.text.strip().replace("```json", "").replace("```", "").strip()
            technical_data = json.loads(cleaned)
            
            return TechnicalSEO(**technical_data)
        except Exception as e:
            print(f"[AI ERROR] Technical SEO analysis failed for {page_data.url}: {e}")
            return TechnicalSEO(
                performance_suggestions=["Optimize images", "Minify CSS/JS"],
                accessibility_improvements=["Add alt text to images", "Improve heading structure"]
            )

    def _format_issues_for_prompt(self, issues: List[str]) -> str:
        """
        Translates a list of technical issues into human-readable guidance for AI prompting.
        """
        if not issues:
            return ""

        issue_map = {
            "missingTitle": "The page is missing a title. Please create a compelling, SEO-friendly title from scratch.",
            "duplicateTitle": "The current title is a duplicate. Please suggest a unique and descriptive title.",
            "missingMeta": "The meta description is missing. Write a strong one based on the content.",
            "duplicateDescription": "The description is duplicated. Provide a unique, informative description.",
            "lowWordCount": "The content is too short. Recommend additional sections or topics to expand it.",
            "imagesMissingAlt": "Some images are missing alt text. Suggest improving accessibility and SEO.",
            "notMobileFriendly": "The page is not mobile-friendly. Recommend layout or content fixes.",
        }

        formatted = []
        for issue in issues:
            if issue in issue_map:
                formatted.append(f"- {issue_map[issue]}")
            elif "h1CountMismatch" in issue:
                count = issue.split(":")[1]
                formatted.append(f"- The page has {count} H1 tags, but should only have one.")
            elif "brokenLink" in issue:
                status = issue.split(":")[1]
                formatted.append(f"- This is a broken link (HTTP {status}). Skip content suggestions.")
            elif "slowLoad" in issue:
                formatted.append("- Page loads slowly. Suggest content-related optimizations.")

        return (
            "\n\nThis page has the following issues that need addressing:\n"
            + "\n".join(formatted)
        )

    async def get_seo_suggestions(self, page_data: PageData) -> Optional[AISuggestions]:
        """
        Generate comprehensive, well-structured SEO suggestions.
        """
        if not self.model or page_data.status_code >= 400:
            return None

        issue_context = self._format_issues_for_prompt(page_data.issues)
        body_snippet = (page_data.body_text or "")[:2000]

        # Enhanced prompt for better structured responses
        main_prompt = f"""
        You are an expert SEO consultant. Analyze this webpage and provide comprehensive, actionable SEO recommendations.

        **Page Analysis:**
        - URL: {page_data.url}
        - Current Title: "{page_data.title or 'NO TITLE'}"
        - Current Meta Description: "{page_data.meta_description or 'NO META DESCRIPTION'}"
        - H1 Count: {page_data.h1_count}
        - Word Count: {page_data.word_count}
        - Load Time: {page_data.load_time}s
        - Page Size: {page_data.page_size_bytes} bytes
        - Content Preview: "{body_snippet}..."
        {issue_context}

        **Provide Detailed Recommendations:**
        1. **Main Title Suggestion** (1 optimized title)
        2. **Alternative Titles** (3 different approaches)
        3. **Meta Description** (compelling, 150-160 characters)
        4. **Alternative Descriptions** (2 variations)
        5. **Content Strategy** (specific improvements)
        6. **Priority Score** (1-10, where 10 is most urgent)
        7. **Potential Impact** (low/medium/high)
        8. **Confidence Score** (0.0-1.0 based on available data)

        Return your analysis in this exact JSON format:
        {{
            "title": "Main optimized title suggestion",
            "title_alternatives": ["Alternative title 1", "Alternative title 2", "Alternative title 3"],
            "description": "Optimized meta description (150-160 chars)",
            "description_alternatives": ["Alt description 1", "Alt description 2"],
            "content": "Specific content improvement strategy and recommendations",
            "priority_score": 8,
            "potential_impact": "high",
            "confidence_score": 0.85
        }}
        """

        try:
            # Generate all components concurrently
            main_task = self.model.generate_content_async(main_prompt)
            keyword_task = self._generate_keyword_analysis(page_data)
            content_task = self._generate_content_suggestions(page_data)
            technical_task = self._generate_technical_seo(page_data)
            
            # Wait for all tasks to complete
            main_response, keyword_analysis, content_suggestions, technical_seo = await asyncio.gather(
                main_task, keyword_task, content_task, technical_task
            )
            
            # Process main response
            cleaned = main_response.text.strip().replace("```json", "").replace("```", "").strip()
            main_data = json.loads(cleaned)
            
            # Create comprehensive suggestions object
            return AISuggestions(
                title=main_data.get("title"),
                description=main_data.get("description"),
                content=main_data.get("content"),
                title_alternatives=main_data.get("title_alternatives", []),
                description_alternatives=main_data.get("description_alternatives", []),
                keyword_analysis=keyword_analysis,
                content_suggestions=content_suggestions,
                technical_seo=technical_seo,
                priority_score=main_data.get("priority_score", 5),
                potential_impact=main_data.get("potential_impact", "medium"),
                confidence_score=main_data.get("confidence_score", 0.7),
                generated_at=datetime.utcnow()
            )
            
        except Exception as e:
            print(f"[AI ERROR] Failed for {page_data.url}: {e}")
            return None

    async def compare_keywords(self, target_page: PageData, competitor_pages: List[PageData]) -> Optional[KeywordComparison]:
        """
        Compare keywords between target page and competitor pages.
        """
        if not self.model or not competitor_pages:
            return None
        
        # Extract keywords from all pages
        target_keywords = set(self._extract_keywords_from_text(target_page.body_text or ""))
        competitor_keywords_sets = []
        
        for comp_page in competitor_pages:
            comp_keywords = set(self._extract_keywords_from_text(comp_page.body_text or ""))
            competitor_keywords_sets.append(comp_keywords)
        
        # Find shared and unique keywords
        all_competitor_keywords = set()
        for comp_set in competitor_keywords_sets:
            all_competitor_keywords.update(comp_set)
        
        shared_keywords = list(target_keywords.intersection(all_competitor_keywords))
        keyword_gaps = list(all_competitor_keywords - target_keywords)
        unique_opportunities = list(target_keywords - all_competitor_keywords)
        
        # Calculate competitive strength (simplified)
        competitive_strength = {}
        for keyword in shared_keywords:
            competitors_using = sum(1 for comp_set in competitor_keywords_sets if keyword in comp_set)
            competitive_strength[keyword] = competitors_using / len(competitor_keywords_sets)
        
        return KeywordComparison(
            target_url=target_page.url,
            competitor_urls=[page.url for page in competitor_pages],
            shared_keywords=shared_keywords[:20],
            unique_opportunities=unique_opportunities[:15],
            keyword_gaps=keyword_gaps[:15],
            competitive_strength=competitive_strength
        )

    async def compare_two_keywords(self, current_keyword: str, proposed_keyword: str) -> Optional[Dict]:
        """Compares two keywords directly using an AI prompt."""
        if not self.model:
            return None

        prompt = f"""
        As an SEO expert, compare these two keywords and provide a recommendation.

        Current Keyword: "{current_keyword}"
        Proposed Keyword: "{proposed_keyword}"

        Analyze the following metrics based on general SEO knowledge, assuming the user wants to switch from the current to the proposed keyword:
        1.  **Volume Score (0-100):** Estimate the search volume potential of the proposed keyword compared to the current one.
        2.  **Difficulty Score (0-100):** Estimate the difficulty to rank for the proposed keyword.
        3.  **Content Relevance (0-100):** Estimate how relevant the proposed keyword might be for content currently ranking for the original keyword.
        4.  **Estimated Traffic Change (percentage):** Estimate the potential percentage change in traffic if the switch is successful.
        5.  **Overall Score (0-100):** Your final combined score for making the switch.
        6.  **Recommendation:** A one-word verdict: "SWITCH", "CONSIDER", or "KEEP".

        Return the analysis as a JSON object with the keys: "current_keyword", "proposed_keyword", "overall_score", "recommendation", "volume_score", "difficulty_score", "content_relevance", "estimated_traffic_change".
        """
        try:
            response = await self.model.generate_content_async(prompt)
            cleaned = response.text.strip().replace("```json", "").replace("```", "").strip()
            comparison_data = json.loads(cleaned)
            return comparison_data
        except Exception as e:
            print(f"[AI ERROR] Keyword-to-keyword comparison failed: {e}")
            return None

    async def analyze_batch(self, pages: List[PageData]) -> List[Optional[AISuggestions]]:
        """Analyzes a batch of pages concurrently for SEO suggestions."""
        if not self.model:
            return []

        tasks = [self.get_seo_suggestions(page) for page in pages]
        return await asyncio.gather(*tasks)

    async def get_relevance_scores(self, proposed_keyword: str, current_keyword: str, page_content: Optional[str]) -> Dict[str, int]:
        """Use AI to get relevance scores for a keyword change."""
        if not self.model:
            return {
                "content_relevance": 50,
                "user_intent_match": 50,
                "brand_alignment": 50,
            }

        prompt = f"""
        You are an SEO expert. Analyze a proposed keyword change for a webpage.
        
        **Webpage Context:**
        - Current Keyword: "{current_keyword}"
        - Proposed Keyword: "{proposed_keyword}"
        - Page Content Snippet: "{page_content[:2000] if page_content else 'No content provided.'}"
        
        **Your Task:**
        Provide three scores from 0 to 100 based on your expert analysis.
        
        1.  **Content Relevance (0-100):** How relevant is the **proposed keyword** to the provided page content? 
            (0=not relevant, 50=somewhat relevant, 100=perfectly relevant).
        2.  **User Intent Match (0-100):** Does the **proposed keyword** better match the likely user intent for this page's content compared to the current keyword?
            (0=worse match, 50=similar match, 100=much better match).
        3.  **Brand Alignment (0-100):** Is the **proposed keyword** well-aligned with a typical business or brand offering this content?
            (0=not aligned, 50=somewhat aligned, 100=perfectly aligned).
        
        Return your analysis in this exact JSON format:
        {{
            "content_relevance": 85,
            "user_intent_match": 70,
            "brand_alignment": 90
        }}
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            cleaned = response.text.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            return {
                "content_relevance": data.get("content_relevance", 50),
                "user_intent_match": data.get("user_intent_match", 50),
                "brand_alignment": data.get("brand_alignment", 50),
            }
        except Exception as e:
            print(f"[AI ERROR] Failed to get relevance scores for '{proposed_keyword}': {e}")
            return {
                "content_relevance": 50,
                "user_intent_match": 50,
                "brand_alignment": 50,
            }

# Instantiate once for reuse across API
ai_service = AIService()
