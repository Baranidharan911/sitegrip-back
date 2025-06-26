"""
Keyword Comparison Service

Handles the detailed comparison and scoring between a current keyword and a proposed one.
"""

import random
from typing import Optional
from models.page_data import KeywordComparisonScore
from services.ranking_service import ranking_service
from ai.ai import ai_service

class KeywordComparisonService:
    def __init__(self):
        self.ranking_service = ranking_service
        self.ai_service = ai_service

    async def compare_and_score(
        self,
        current_keyword: str,
        proposed_keyword: str,
        page_content: Optional[str] = None
    ) -> KeywordComparisonScore:
        """
        Compares two keywords and generates a detailed scoring report.
        """
        # 1. Get volume and difficulty data for both keywords
        current_volume_data = self.ranking_service.get_keyword_volume_data(current_keyword)
        proposed_volume_data = self.ranking_service.get_keyword_volume_data(proposed_keyword)

        # 2. Calculate volume score
        volume_improvement = 0
        if current_volume_data.monthly_volume > 0:
            volume_improvement = ((proposed_volume_data.monthly_volume - current_volume_data.monthly_volume) / current_volume_data.monthly_volume) * 100
        elif proposed_volume_data.monthly_volume > 0:
            volume_improvement = 100.0 # From 0 to something is a big improvement

        # Normalize score (0-100). Cap improvement at 200% for scoring.
        volume_score = min(100, max(0, 50 + (volume_improvement / 4))) # 50 is baseline, 200% improvement = 100 score

        # 3. Calculate competition score
        competition_improvement = current_volume_data.competition_score - proposed_volume_data.competition_score # Higher is better
        # Normalize score (0-100).
        competition_score = min(100, max(0, 50 + (competition_improvement * 100))) # 50 is baseline, 0.5 improvement = 100 score

        # 4. Calculate difficulty score
        difficulty_improvement = current_volume_data.difficulty_score - proposed_volume_data.difficulty_score # Higher is better
        # Normalize score (0-100).
        difficulty_score = min(100, max(0, 50 + difficulty_improvement)) # 50 is baseline, 50 pts improvement = 100 score

        # 5. Use AI for relevance scoring
        relevance_scores = await self.ai_service.get_relevance_scores(
            proposed_keyword,
            current_keyword,
            page_content
        )

        content_relevance = relevance_scores.get('content_relevance', 50)
        user_intent_match = relevance_scores.get('user_intent_match', 50)
        brand_alignment = relevance_scores.get('brand_alignment', 50)

        # 6. Calculate overall score (weighted average)
        weights = {
            'volume': 0.30,
            'competition': 0.20,
            'difficulty': 0.20,
            'relevance': 0.15,
            'intent': 0.10,
            'brand': 0.05
        }
        overall_score = (
            volume_score * weights['volume'] +
            competition_score * weights['competition'] +
            difficulty_score * weights['difficulty'] +
            content_relevance * weights['relevance'] +
            user_intent_match * weights['intent'] +
            brand_alignment * weights['brand']
        )
        overall_score = int(min(100, max(0, overall_score)))

        # 7. Generate recommendation
        if overall_score >= 85:
            recommendation = "strong_yes"
        elif overall_score >= 70:
            recommendation = "yes"
        elif overall_score >= 40:
            recommendation = "neutral"
        elif overall_score >= 20:
            recommendation = "no"
        else:
            recommendation = "strong_no"
            
        # Simplified estimated traffic change
        estimated_traffic_change = volume_improvement / 2 # Very rough estimate

        return KeywordComparisonScore(
            current_keyword=current_keyword,
            proposed_keyword=proposed_keyword,
            current_volume=current_volume_data.monthly_volume,
            proposed_volume=proposed_volume_data.monthly_volume,
            volume_improvement=round(volume_improvement, 2),
            volume_score=int(volume_score),
            current_competition=current_volume_data.competition_score,
            proposed_competition=proposed_volume_data.competition_score,
            competition_improvement=round(competition_improvement, 2),
            competition_score=int(competition_score),
            current_difficulty=current_volume_data.difficulty_score,
            proposed_difficulty=proposed_volume_data.difficulty_score,
            difficulty_improvement=difficulty_improvement,
            difficulty_score=int(difficulty_score),
            content_relevance=content_relevance,
            user_intent_match=user_intent_match,
            brand_alignment=brand_alignment,
            overall_score=overall_score,
            recommendation=recommendation,
            confidence_level=0.85, # Mock confidence
            estimated_traffic_change=round(estimated_traffic_change, 2),
            implementation_effort="medium",
            expected_timeframe="3-6 months"
        )

# Global instance
keyword_comparison_service = KeywordComparisonService() 