# services/ai_summary.py

import os
from dotenv import load_dotenv
from typing import List
import google.generativeai as genai
from models.page_data import PageData

load_dotenv()

class AISummaryService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("⚠️ Warning: No GEMINI_API_KEY found. AI summary disabled.")
            self.model = None
        else:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")

    async def summarize_crawl(self, pages: List[PageData]) -> str:
        if not self.model:
            return "AI summary is not available (missing API key)."

        try:
            site_url = pages[0].url.split("/")[2] if pages else "the site"
            prompt = f"""
You are an expert SEO analyst. Summarize the key SEO findings from a site audit for {site_url}.
Use the following data from individual pages:

{[
    f"URL: {p.url}, Status: {p.status_code}, Title: {p.title}, Word Count: {p.word_count}, Issues: {p.issues}"
    for p in pages
][:20]}  # Send only 20 representative entries for now.

Focus on patterns and actionable issues. Keep it concise, like an executive report.
Only return the final summary paragraph, no preface or JSON formatting.
"""

            response = await self.model.generate_content_async(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"❌ Error generating AI summary: {e}")
            return "AI summary could not be generated due to an internal error."

ai_summary_service = AISummaryService()
