"""
Keyword Storage Service

Handles storage and retrieval of keyword data for SEO analysis,
including keyword comparisons, tracking, and historical data.
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from db.firestore import firestore_client, get_or_create_firestore_client
from models.page_data import KeywordAnalysis, KeywordComparison
import json

class KeywordStorageService:
    def __init__(self):
        try:
            self.db = get_or_create_firestore_client()
        except Exception as e:
            print(f"Warning: Could not initialize Firestore client in KeywordStorageService: {e}")
            self.db = None
        self.keywords_collection = "keywords"
        self.keyword_comparisons_collection = "keyword_comparisons"
        self.keyword_trends_collection = "keyword_trends"
    
    def store_keyword_analysis(self, url: str, keyword_analysis: KeywordAnalysis, crawl_id: str) -> bool:
        """
        Store keyword analysis data for a specific URL and crawl.
        """
        if not self.db:
            print("Warning: Firestore client not available, cannot store keyword analysis")
            return False
            
        try:
            doc_data = {
                "url": url,
                "crawl_id": crawl_id,
                "primary_keywords": keyword_analysis.primary_keywords,
                "suggested_keywords": keyword_analysis.suggested_keywords,
                "keyword_density": keyword_analysis.keyword_density,
                "missing_keywords": keyword_analysis.missing_keywords,
                "competitor_keywords": keyword_analysis.competitor_keywords,
                "long_tail_suggestions": keyword_analysis.long_tail_suggestions,
                "created_at": datetime.utcnow(),
                "url_hash": self._generate_url_hash(url)
            }
            
            # Use URL hash + timestamp as document ID to allow multiple analyses per URL
            doc_id = f"{self._generate_url_hash(url)}_{int(datetime.utcnow().timestamp())}"
            
            self.db.collection(self.keywords_collection).document(doc_id).set(doc_data)
            return True
            
        except Exception as e:
            print(f"Error storing keyword analysis for {url}: {e}")
            return False
    
    def store_keyword_comparison(self, comparison: KeywordComparison, crawl_id: str) -> bool:
        """
        Store keyword comparison data.
        """
        if not self.db:
            print("Warning: Firestore client not available, cannot store keyword comparison")
            return False
            
        try:
            doc_data = {
                "target_url": comparison.target_url,
                "competitor_urls": comparison.competitor_urls,
                "shared_keywords": comparison.shared_keywords,
                "unique_opportunities": comparison.unique_opportunities,
                "keyword_gaps": comparison.keyword_gaps,
                "competitive_strength": comparison.competitive_strength,
                "crawl_id": crawl_id,
                "created_at": datetime.utcnow(),
                "url_hash": self._generate_url_hash(comparison.target_url)
            }
            
            doc_id = f"comp_{self._generate_url_hash(comparison.target_url)}_{int(datetime.utcnow().timestamp())}"
            
            self.db.collection(self.keyword_comparisons_collection).document(doc_id).set(doc_data)
            return True
            
        except Exception as e:
            print(f"Error storing keyword comparison: {e}")
            return False
    
    def get_keyword_history(self, url: str, days: int = 30) -> List[Dict]:
        """
        Get keyword analysis history for a URL over the specified number of days.
        """
        if not self.db:
            print("Warning: Firestore client not available, cannot get keyword history")
            return []
            
        try:
            url_hash = self._generate_url_hash(url)
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            docs = (self.db.collection(self.keywords_collection)
                   .where("url_hash", "==", url_hash)
                   .where("created_at", ">=", cutoff_date)
                   .order_by("created_at", direction="DESCENDING")
                   .get())
            
            return [doc.to_dict() for doc in docs]
            
        except Exception as e:
            print(f"Error retrieving keyword history for {url}: {e}")
            return []
    
    def get_trending_keywords(self, domain: str = None, days: int = 7) -> Dict[str, int]:
        """
        Get trending keywords across all URLs or for a specific domain.
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = self.db.collection(self.keywords_collection).where("created_at", ">=", cutoff_date)
            
            if domain:
                # Filter by domain (simplified approach)
                docs = query.get()
                filtered_docs = [doc for doc in docs if domain in doc.to_dict().get("url", "")]
            else:
                docs = query.get()
                filtered_docs = docs
            
            # Aggregate keywords
            keyword_counts = {}
            for doc in filtered_docs:
                data = doc.to_dict()
                
                # Count primary keywords
                for keyword in data.get("primary_keywords", []):
                    keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
                
                # Count suggested keywords
                for keyword in data.get("suggested_keywords", []):
                    keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
            
            # Return top 20 trending keywords
            return dict(sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:20])
            
        except Exception as e:
            print(f"Error getting trending keywords: {e}")
            return {}
    
    def get_competitor_keyword_gaps(self, target_url: str, days: int = 30) -> List[str]:
        """
        Get keyword gaps identified in recent competitor analysis.
        """
        try:
            url_hash = self._generate_url_hash(target_url)
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            docs = (self.db.collection(self.keyword_comparisons_collection)
                   .where("url_hash", "==", url_hash)
                   .where("created_at", ">=", cutoff_date)
                   .order_by("created_at", direction="DESCENDING")
                   .limit(5)
                   .get())
            
            all_gaps = set()
            for doc in docs:
                data = doc.to_dict()
                gaps = data.get("keyword_gaps", [])
                all_gaps.update(gaps)
            
            return list(all_gaps)
            
        except Exception as e:
            print(f"Error getting competitor keyword gaps for {target_url}: {e}")
            return []
    
    def store_keyword_tracking(self, keywords: List[str], url: str, crawl_id: str) -> bool:
        """
        Store keywords for tracking over time.
        """
        try:
            doc_data = {
                "keywords": keywords,
                "url": url,
                "crawl_id": crawl_id,
                "created_at": datetime.utcnow(),
                "url_hash": self._generate_url_hash(url),
                "tracking_active": True
            }
            
            doc_id = f"track_{self._generate_url_hash(url)}_{int(datetime.utcnow().timestamp())}"
            
            self.db.collection(self.keyword_trends_collection).document(doc_id).set(doc_data)
            return True
            
        except Exception as e:
            print(f"Error storing keyword tracking data: {e}")
            return False
    
    def get_keyword_performance_trends(self, url: str, keywords: List[str], days: int = 90) -> Dict[str, List[Dict]]:
        """
        Get performance trends for specific keywords on a URL.
        """
        try:
            url_hash = self._generate_url_hash(url)
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            docs = (self.db.collection(self.keywords_collection)
                   .where("url_hash", "==", url_hash)
                   .where("created_at", ">=", cutoff_date)
                   .order_by("created_at")
                   .get())
            
            trends = {keyword: [] for keyword in keywords}
            
            for doc in docs:
                data = doc.to_dict()
                keyword_density = data.get("keyword_density", {})
                created_at = data.get("created_at")
                
                for keyword in keywords:
                    if keyword in keyword_density:
                        trends[keyword].append({
                            "date": created_at,
                            "density": keyword_density[keyword],
                            "crawl_id": data.get("crawl_id")
                        })
            
            return trends
            
        except Exception as e:
            print(f"Error getting keyword performance trends: {e}")
            return {}
    
    def get_domain_keyword_summary(self, domain: str) -> Dict:
        """
        Get a comprehensive keyword summary for a domain.
        """
        try:
            # Get all keyword data for the domain (last 30 days)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            docs = (self.db.collection(self.keywords_collection)
                   .where("created_at", ">=", cutoff_date)
                   .get())
            
            domain_docs = [doc for doc in docs if domain in doc.to_dict().get("url", "")]
            
            if not domain_docs:
                return {"message": "No keyword data found for this domain"}
            
            # Aggregate data
            all_primary_keywords = set()
            all_suggested_keywords = set()
            all_missing_keywords = set()
            total_pages_analyzed = len(domain_docs)
            avg_keyword_density = {}
            
            for doc in domain_docs:
                data = doc.to_dict()
                
                all_primary_keywords.update(data.get("primary_keywords", []))
                all_suggested_keywords.update(data.get("suggested_keywords", []))
                all_missing_keywords.update(data.get("missing_keywords", []))
                
                # Calculate average keyword density
                for keyword, density in data.get("keyword_density", {}).items():
                    if keyword not in avg_keyword_density:
                        avg_keyword_density[keyword] = []
                    avg_keyword_density[keyword].append(density)
            
            # Calculate averages
            for keyword in avg_keyword_density:
                densities = avg_keyword_density[keyword]
                avg_keyword_density[keyword] = round(sum(densities) / len(densities), 2)
            
            return {
                "domain": domain,
                "total_pages_analyzed": total_pages_analyzed,
                "total_unique_primary_keywords": len(all_primary_keywords),
                "total_unique_suggested_keywords": len(all_suggested_keywords),
                "total_missing_keywords": len(all_missing_keywords),
                "top_primary_keywords": list(all_primary_keywords)[:20],
                "top_suggested_keywords": list(all_suggested_keywords)[:20],
                "critical_missing_keywords": list(all_missing_keywords)[:15],
                "average_keyword_density": dict(sorted(avg_keyword_density.items(), 
                                                      key=lambda x: x[1], reverse=True)[:15]),
                "analysis_period": "Last 30 days",
                "last_updated": datetime.utcnow()
            }
            
        except Exception as e:
            print(f"Error getting domain keyword summary: {e}")
            return {"error": f"Failed to generate summary: {str(e)}"}
    
    def _generate_url_hash(self, url: str) -> str:
        """
        Generate a consistent hash for URL-based document IDs.
        """
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()[:16]
    
    def cleanup_old_data(self, days: int = 90) -> bool:
        """
        Clean up keyword data older than specified days.
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Clean up keywords collection
            old_docs = (self.db.collection(self.keywords_collection)
                       .where("created_at", "<", cutoff_date)
                       .get())
            
            for doc in old_docs:
                doc.reference.delete()
            
            # Clean up comparisons collection
            old_comp_docs = (self.db.collection(self.keyword_comparisons_collection)
                            .where("created_at", "<", cutoff_date)
                            .get())
            
            for doc in old_comp_docs:
                doc.reference.delete()
            
            print(f"Cleaned up {len(old_docs)} keyword documents and {len(old_comp_docs)} comparison documents")
            return True
            
        except Exception as e:
            print(f"Error cleaning up old keyword data: {e}")
            return False

# Global instance
keyword_storage_service = KeywordStorageService() 