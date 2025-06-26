from fastapi import APIRouter, Body, Response
from typing import List
from models.page_data import PageData
import csv
import io

router = APIRouter()

@router.post("/export/csv")
async def export_csv(pages: List[PageData] = Body(...)):
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "URL",
        "Status Code",
        "Title",
        "Word Count",
        "Issues",
        "Load Time (s)",
        "Page Size (KB)",
        "Redirect Chain",
        "Has Viewport",
        "AI Title",
        "AI Description",
        "AI Content Suggestions",
        "Priority Score",
        "Potential Impact",
        "Confidence Score",
        "Primary Keywords",
        "Suggested Keywords",
        "Missing Keywords",
        "Long-tail Suggestions",
        "Readability Score",
        "Content Gaps"
    ])

    for page in pages:
        writer.writerow([
            page.url,
            page.status_code,
            page.title or "",
            page.word_count,
            "; ".join(page.issues),
            f"{page.load_time:.2f}",
            f"{page.page_size_bytes / 1024:.1f}",
            " → ".join(page.redirect_chain),
            "Yes" if page.has_viewport else "No",
            page.suggestions.title if page.suggestions else "",
            page.suggestions.description if page.suggestions else "",
            page.suggestions.content if page.suggestions else "",
            page.suggestions.priority_score if page.suggestions else "",
            page.suggestions.potential_impact if page.suggestions else "",
            page.suggestions.confidence_score if page.suggestions else "",
            "; ".join(page.suggestions.keyword_analysis.primary_keywords) if page.suggestions and page.suggestions.keyword_analysis else "",
            "; ".join(page.suggestions.keyword_analysis.suggested_keywords) if page.suggestions and page.suggestions.keyword_analysis else "",
            "; ".join(page.suggestions.keyword_analysis.missing_keywords) if page.suggestions and page.suggestions.keyword_analysis else "",
            "; ".join(page.suggestions.keyword_analysis.long_tail_suggestions) if page.suggestions and page.suggestions.keyword_analysis else "",
            page.suggestions.content_suggestions.readability_score if page.suggestions and page.suggestions.content_suggestions else "",
            "; ".join(page.suggestions.content_suggestions.content_gaps) if page.suggestions and page.suggestions.content_suggestions else "",
        ])

    csv_data = output.getvalue()
    output.close()

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=crawl_results.csv"}
    )
