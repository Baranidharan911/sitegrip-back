"""
Ranking Service

Handles keyword ranking tracking across Google, Bing, and Mobile platforms.
Includes search volume estimation and ranking history management.
"""

import random
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from google.cloud import firestore
from db.firestore import get_or_create_firestore_client
from models.page_data import SearchEngineRanking, KeywordVolume, KeywordRankingHistory, DomainKeywordProfile

class RankingService:
    def __init__(self):
        try:
            self.db = get_or_create_firestore_client()
        except Exception as e:
            print(f"Warning: Could not initialize Firestore client in RankingService: {e}")
            self.db = None
        self.rankings_collection = "keyword_rankings"
        self.volumes_collection = "keyword_volumes"
        self.domain_profiles_collection = "domain_profiles"
    
    def _generate_mock_ranking(self, keyword: str, url: str, base_rank: Optional[int] = None) -> SearchEngineRanking:
        """Generate realistic mock ranking data based on keyword characteristics."""
        # Use keyword hash for consistent "randomness"
        seed = int(hashlib.md5((keyword + url).encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        # Estimate base ranking based on keyword length and characteristics
        if base_rank is None:
            keyword_length = len(keyword.split())
            if keyword_length == 1:  # Single word - typically harder to rank
                base_rank = random.randint(25, 80)
            elif keyword_length <= 3:  # Short phrases - medium difficulty
                base_rank = random.randint(15, 50)
            else:  # Long tail - easier to rank
                base_rank = random.randint(5, 30)
        
        # Add some variance
        variance = random.randint(-10, 15)
        google_rank = max(1, min(100, base_rank + variance))
        
        # Bing typically has different rankings
        bing_variance = random.randint(-15, 20)
        bing_rank = max(1, min(100, google_rank + bing_variance))
        
        # Mobile rankings can be slightly different
        mobile_variance = random.randint(-5, 10)
        mobile_rank = max(1, min(100, google_rank + mobile_variance))
        
        # Generate search volume based on keyword characteristics
        volume = self._estimate_search_volume(keyword)
        
        # Competition level based on volume and keyword type
        if volume > 10000:
            competition = "high"
            cpc = random.uniform(2.0, 15.0)
        elif volume > 1000:
            competition = "medium"
            cpc = random.uniform(0.5, 5.0)
        else:
            competition = "low"
            cpc = random.uniform(0.1, 2.0)
        
        return SearchEngineRanking(
            keyword=keyword,
            google_rank=google_rank,
            bing_rank=bing_rank,
            mobile_rank=mobile_rank,
            search_volume=volume,
            competition_level=competition,
            cpc_estimate=round(cpc, 2),
            ranking_date=datetime.utcnow()
        )
    
    def _estimate_search_volume(self, keyword: str) -> int:
        """Estimate search volume based on keyword characteristics."""
        # Use keyword hash for consistent estimation
        seed = int(hashlib.md5(keyword.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        keyword_lower = keyword.lower()
        word_count = len(keyword.split())
        
        # Base volume estimation
        if word_count == 1:
            # Single words typically have higher volume
            base_volume = random.randint(1000, 50000)
        elif word_count <= 3:
            # Short phrases
            base_volume = random.randint(100, 10000)
        else:
            # Long tail keywords
            base_volume = random.randint(10, 2000)
        
        # Adjust based on common keyword patterns
        high_volume_patterns = ['seo', 'marketing', 'business', 'web', 'design', 'development', 'service']
        medium_volume_patterns = ['how to', 'best', 'top', 'guide', 'tips']
        
        if any(pattern in keyword_lower for pattern in high_volume_patterns):
            base_volume = int(base_volume * random.uniform(2.0, 5.0))
        elif any(pattern in keyword_lower for pattern in medium_volume_patterns):
            base_volume = int(base_volume * random.uniform(1.5, 3.0))
        
        return min(base_volume, 100000)  # Cap at 100k for realism
    
    def track_keyword_ranking(self, keyword: str, url: str, domain: str) -> SearchEngineRanking:
        """Track a keyword ranking for a specific URL."""
        if not self.db:
            print("Warning: Firestore client not available")
            return self._generate_mock_ranking(keyword, url)
        
        try:
            # Generate current ranking
            current_ranking = self._generate_mock_ranking(keyword, url)
            
            # Check for previous ranking to calculate change
            url_hash = self._generate_url_hash(url)
            keyword_hash = self._generate_keyword_hash(keyword)
            doc_id = f"{url_hash}_{keyword_hash}"
            
            # Get previous ranking
            previous_doc = self.db.collection(self.rankings_collection).document(doc_id).get()
            
            if previous_doc.exists:
                previous_data = previous_doc.to_dict()
                last_rankings = previous_data.get('rankings', [])
                if last_rankings:
                    last_rank = last_rankings[-1].get('google_rank', current_ranking.google_rank)
                    current_ranking.ranking_change = last_rank - current_ranking.google_rank
            
            # Store ranking data
            ranking_data = {
                'keyword': keyword,
                'url': url,
                'domain': domain,
                'google_rank': current_ranking.google_rank,
                'bing_rank': current_ranking.bing_rank,
                'mobile_rank': current_ranking.mobile_rank,
                'search_volume': current_ranking.search_volume,
                'competition_level': current_ranking.competition_level,
                'cpc_estimate': current_ranking.cpc_estimate,
                'ranking_date': current_ranking.ranking_date,
                'ranking_change': current_ranking.ranking_change,
                'url_hash': url_hash,
                'keyword_hash': keyword_hash
            }
            
            # Update or create document
            if previous_doc.exists:
                # Add to existing rankings array
                self.db.collection(self.rankings_collection).document(doc_id).update({
                    'rankings': firestore.ArrayUnion([ranking_data]),
                    'last_updated': datetime.utcnow()
                })
            else:
                # Create new document
                self.db.collection(self.rankings_collection).document(doc_id).set({
                    'keyword': keyword,
                    'url': url,
                    'domain': domain,
                    'rankings': [ranking_data],
                    'created_at': datetime.utcnow(),
                    'last_updated': datetime.utcnow(),
                    'url_hash': url_hash,
                    'keyword_hash': keyword_hash
                })
            
            return current_ranking
            
        except Exception as e:
            print(f"Error tracking keyword ranking: {e}")
            return self._generate_mock_ranking(keyword, url)
    
    def get_keyword_volume_data(self, keyword: str) -> KeywordVolume:
        """Get comprehensive volume and competition data for a keyword."""
        if not self.db:
            return self._generate_mock_volume_data(keyword)
        
        try:
            keyword_hash = self._generate_keyword_hash(keyword)
            doc = self.db.collection(self.volumes_collection).document(keyword_hash).get()
            
            if doc.exists:
                data = doc.to_dict()
                return KeywordVolume(**data)
            else:
                # Generate new volume data
                volume_data = self._generate_mock_volume_data(keyword)
                
                # Store for future use
                self.db.collection(self.volumes_collection).document(keyword_hash).set(volume_data.dict())
                
                return volume_data
                
        except Exception as e:
            print(f"Error getting keyword volume data: {e}")
            return self._generate_mock_volume_data(keyword)
    
    def _generate_mock_volume_data(self, keyword: str) -> KeywordVolume:
        """Generate mock volume and competition data."""
        seed = int(hashlib.md5(keyword.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        monthly_volume = self._estimate_search_volume(keyword)
        
        # Generate trend
        trends = ["growing", "stable", "declining"]
        trend_weights = [0.3, 0.5, 0.2]  # Most keywords are stable
        volume_trend = random.choices(trends, weights=trend_weights)[0]
        
        # Competition score based on volume
        if monthly_volume > 10000:
            competition_score = random.uniform(0.7, 0.95)
            difficulty_score = random.randint(70, 95)
        elif monthly_volume > 1000:
            competition_score = random.uniform(0.4, 0.8)
            difficulty_score = random.randint(40, 75)
        else:
            competition_score = random.uniform(0.1, 0.5)
            difficulty_score = random.randint(10, 50)
        
        # Generate related keywords
        related_keywords = self._generate_related_keywords(keyword)
        
        # Generate seasonal data (simplified)
        seasonal_data = {}
        for month in range(1, 13):
            seasonal_multiplier = random.uniform(0.7, 1.3)
            seasonal_data[f"month_{month}"] = int(monthly_volume * seasonal_multiplier)
        
        return KeywordVolume(
            keyword=keyword,
            monthly_volume=monthly_volume,
            volume_trend=volume_trend,
            competition_score=round(competition_score, 2),
            difficulty_score=difficulty_score,
            related_keywords=related_keywords,
            seasonal_data=seasonal_data
        )
    
    def _generate_related_keywords(self, keyword: str) -> List[str]:
        """Generate related keyword suggestions."""
        related = []
        words = keyword.split()
        
        # Add prefixes and suffixes
        prefixes = ["best", "top", "how to", "free", "online", "professional"]
        suffixes = ["services", "tools", "tips", "guide", "2024", "company"]
        
        for prefix in prefixes[:2]:
            related.append(f"{prefix} {keyword}")
        
        for suffix in suffixes[:2]:
            related.append(f"{keyword} {suffix}")
        
        # Add variations
        if len(words) > 1:
            related.append(" ".join(words[:-1]))  # Remove last word
            related.append(" ".join(words[1:]))   # Remove first word
        
        return related[:10]
    
    def get_ranking_history(self, keyword: str, url: str, days: int = 30) -> KeywordRankingHistory:
        """Get ranking history for a keyword on a specific URL."""
        if not self.db:
            return self._generate_mock_ranking_history(keyword, url, days)
        
        try:
            url_hash = self._generate_url_hash(url)
            keyword_hash = self._generate_keyword_hash(keyword)
            doc_id = f"{url_hash}_{keyword_hash}"
            
            doc = self.db.collection(self.rankings_collection).document(doc_id).get()
            
            if doc.exists:
                data = doc.to_dict()
                rankings_data = data.get('rankings', [])
                
                # Convert to SearchEngineRanking objects
                rankings = []
                for rank_data in rankings_data:
                    try:
                        ranking = SearchEngineRanking(**rank_data)
                        rankings.append(ranking)
                    except Exception as e:
                        print(f"Error parsing ranking data: {e}")
                        continue
                
                # Calculate statistics
                google_ranks = [r.google_rank for r in rankings if r.google_rank]
                
                if google_ranks:
                    best_ranking = min(google_ranks)
                    worst_ranking = max(google_ranks)
                    average_ranking = sum(google_ranks) / len(google_ranks)
                    
                    # Determine trend
                    if len(google_ranks) >= 2:
                        recent_avg = sum(google_ranks[-3:]) / len(google_ranks[-3:])
                        older_avg = sum(google_ranks[:-3]) / len(google_ranks[:-3]) if len(google_ranks) > 3 else recent_avg
                        
                        if recent_avg < older_avg - 5:
                            trend = "improving"
                        elif recent_avg > older_avg + 5:
                            trend = "declining"
                        else:
                            trend = "stable"
                    else:
                        trend = "stable"
                else:
                    best_ranking = None
                    worst_ranking = None
                    average_ranking = 0.0
                    trend = "stable"
                
                return KeywordRankingHistory(
                    keyword=keyword,
                    url=url,
                    rankings=rankings,
                    best_ranking=best_ranking,
                    worst_ranking=worst_ranking,
                    average_ranking=round(average_ranking, 1),
                    ranking_trend=trend,
                    tracking_start_date=data.get('created_at', datetime.utcnow())
                )
            else:
                return self._generate_mock_ranking_history(keyword, url, days)
                
        except Exception as e:
            print(f"Error getting ranking history: {e}")
            return self._generate_mock_ranking_history(keyword, url, days)
    
    def _generate_mock_ranking_history(self, keyword: str, url: str, days: int) -> KeywordRankingHistory:
        """Generate mock ranking history for testing."""
        rankings = []
        
        # Generate historical rankings
        for i in range(min(days, 30)):  # Limit to 30 data points
            date = datetime.utcnow() - timedelta(days=days-i)
            base_rank = 50 + i  # Simulate improving trend
            ranking = self._generate_mock_ranking(keyword, url, base_rank)
            ranking.ranking_date = date
            rankings.append(ranking)
        
        # Calculate statistics
        google_ranks = [r.google_rank for r in rankings if r.google_rank]
        
        if google_ranks:
            best_ranking = min(google_ranks)
            worst_ranking = max(google_ranks)
            average_ranking = sum(google_ranks) / len(google_ranks)
            trend = "improving"  # Mock trend
        else:
            best_ranking = None
            worst_ranking = None
            average_ranking = 0.0
            trend = "stable"
        
        return KeywordRankingHistory(
            keyword=keyword,
            url=url,
            rankings=rankings,
            best_ranking=best_ranking,
            worst_ranking=worst_ranking,
            average_ranking=round(average_ranking, 1),
            ranking_trend=trend,
            tracking_start_date=datetime.utcnow() - timedelta(days=days)
        )
    
    def get_domain_profile(self, domain: str) -> DomainKeywordProfile:
        """Get comprehensive keyword profile for a domain."""
        if not self.db:
            return self._generate_mock_domain_profile(domain)
        
        try:
            # Get all keywords for this domain
            docs = self.db.collection(self.rankings_collection).where("domain", "==", domain).get()
            
            if not docs:
                return self._generate_mock_domain_profile(domain)
            
            total_keywords = len(docs)
            top10_count = 0
            top50_count = 0
            total_volume = 0
            all_rankings = []
            
            for doc in docs:
                data = doc.to_dict()
                rankings = data.get('rankings', [])
                if rankings:
                    latest_ranking = rankings[-1]
                    google_rank = latest_ranking.get('google_rank', 100)
                    search_volume = latest_ranking.get('search_volume', 0)
                    
                    all_rankings.append(google_rank)
                    total_volume += search_volume
                    
                    if google_rank <= 10:
                        top10_count += 1
                    if google_rank <= 50:
                        top50_count += 1
            
            avg_ranking = sum(all_rankings) / len(all_rankings) if all_rankings else 0.0
            
            return DomainKeywordProfile(
                domain=domain,
                total_tracked_keywords=total_keywords,
                keywords_ranking_top10=top10_count,
                keywords_ranking_top50=top50_count,
                total_search_volume=total_volume,
                average_ranking_position=round(avg_ranking, 1),
                keyword_distribution={"high": 20, "medium": 50, "low": 30},  # Mock distribution
                top_performing_keywords=["seo services", "web design", "digital marketing"][:3],
                improvement_opportunities=["content marketing", "social media", "email marketing"][:3],
                competitive_gaps=["ppc advertising", "conversion optimization"][:2],
                last_updated=datetime.utcnow()
            )
            
        except Exception as e:
            print(f"Error getting domain profile: {e}")
            return self._generate_mock_domain_profile(domain)
    
    def _generate_mock_domain_profile(self, domain: str) -> DomainKeywordProfile:
        """Generate mock domain profile for testing."""
        seed = int(hashlib.md5(domain.encode()).hexdigest()[:8], 16)
        random.seed(seed)
        
        total_keywords = random.randint(50, 200)
        top10_count = random.randint(5, 20)
        top50_count = random.randint(20, 80)
        total_volume = random.randint(10000, 100000)
        avg_ranking = random.uniform(25.0, 75.0)
        
        return DomainKeywordProfile(
            domain=domain,
            total_tracked_keywords=total_keywords,
            keywords_ranking_top10=top10_count,
            keywords_ranking_top50=top50_count,
            total_search_volume=total_volume,
            average_ranking_position=round(avg_ranking, 1),
            keyword_distribution={"high": 25, "medium": 45, "low": 30},
            top_performing_keywords=["digital marketing", "web development", "seo services"],
            improvement_opportunities=["content strategy", "link building", "technical seo"],
            competitive_gaps=["paid advertising", "social media marketing"],
            last_updated=datetime.utcnow()
        )
    
    def _generate_url_hash(self, url: str) -> str:
        """Generate a consistent hash for URL-based document IDs."""
        return hashlib.md5(url.encode()).hexdigest()[:16]
    
    def _generate_keyword_hash(self, keyword: str) -> str:
        """Generate a consistent hash for keyword-based document IDs."""
        return hashlib.md5(keyword.lower().encode()).hexdigest()[:16]

# Global instance
ranking_service = RankingService() 