# backend/ai/ai.py

import asyncio
import google.generativeai as genai
import os
import json
from dotenv import load_dotenv
from typing import Optional, List
from models.page_data import AISuggestions, PageData

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
        Sends page data to Gemini AI for title/meta/content suggestions.
        Returns an AISuggestions object or None if errors or inapplicable.
        """
        if not self.model or page_data.status_code >= 400:
            return None

        issue_context = self._format_issues_for_prompt(page_data.issues)
        body_snippet = (page_data.body_text or "")[:2000]

        prompt = f"""
        Analyze the following SEO data for the URL {page_data.url} and provide expert suggestions.

        **Page Data:**
        - Title: "{page_data.title}"
        - Meta Description: "{page_data.meta_description}"
        - H1 Count: {page_data.h1_count}
        - Word Count: {page_data.word_count}
        - Content Snippet: "{body_snippet}..."
        {issue_context}

        **Your Task:**
        Give clear, concise SEO improvements for:
        1. Page Title
        2. Meta Description
        3. Page Content (structure, topics, or section ideas)

        Return your suggestions in this exact JSON format:
        {{
            "title": "Suggested new page title.",
            "description": "Suggested meta description.",
            "content": "Content structure or keyword-based improvements."
        }}
        """

        try:
            response = await self.model.generate_content_async(prompt)
            cleaned = response.text.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(cleaned)
            return AISuggestions(**data)
        except Exception as e:
            print(f"[AI ERROR] Failed for {page_data.url}: {e}")
            return None

    async def analyze_batch(self, pages: List[PageData]) -> List[Optional[AISuggestions]]:
        """
        Analyzes a list of PageData objects concurrently.
        Returns a list of AISuggestions (one per input page, may include None).
        """
        tasks = [self.get_seo_suggestions(page) for page in pages]
        return await asyncio.gather(*tasks)

# Instantiate once for reuse across API
ai_service = AIService()
