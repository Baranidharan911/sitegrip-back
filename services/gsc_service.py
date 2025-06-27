import asyncio
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union, Any
import json
import requests
import os

from db.firestore import get_or_create_firestore_client
from models.gsc import (
    GSCData, GSCProperty, GSCCoverageStatus, GSCAuthResponse
)
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from models.gsc_data import IndexStatus
from services.google_auth_service import google_auth_service

class GSCService:
    """Service for Google Search Console integration"""
    
    def __init__(self):
        self.db = get_or_create_firestore_client()
        self.gsc_api_base = "https://searchconsole.googleapis.com/webmasters/v3"
        self.scopes = [
            'https://www.googleapis.com/auth/webmasters.readonly',
            'https://www.googleapis.com/auth/webmasters'
        ]
        
        # OAuth credentials - in production, these would be environment variables
        self.client_id = os.getenv('GOOGLE_CLIENT_ID', 'your-client-id')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET', 'your-client-secret')
        self.redirect_uri = os.getenv('GSC_REDIRECT_URI', 'http://localhost:3000/auth/gsc/callback')
        self.api_name = "searchconsole"
        self.api_version = "v1"
        self.index_status_collection = "index_status"
    
    def get_oauth_authorization_url(self, state: str) -> str:
        """Generate OAuth authorization URL for Google Search Console"""
        try:
            # Mock OAuth URL for development
            base_url = "https://accounts.google.com/o/oauth2/v2/auth"
            params = {
                'client_id': self.client_id,
                'redirect_uri': self.redirect_uri,
                'scope': ' '.join(self.scopes),
                'response_type': 'code',
                'access_type': 'offline',
                'include_granted_scopes': 'true',
                'state': state
            }
            
            param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            return f"{base_url}?{param_string}"
            
        except Exception as e:
            print(f"Error generating OAuth URL: {e}")
            return ""
    
    async def handle_oauth_callback(
        self, 
        authorization_code: str, 
        user_id: str
    ) -> GSCAuthResponse:
        """Handle OAuth callback and store credentials"""
        try:
            # Mock credentials for development
            mock_credentials = {
                'token': f'mock_access_token_{user_id}',
                'refresh_token': f'mock_refresh_token_{user_id}',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scopes': self.scopes,
                'expiry': (datetime.utcnow() + timedelta(hours=1)).isoformat()
            }
            
            # Store credentials in database
            await self._store_user_credentials(user_id, mock_credentials)
            
            # Fetch user's GSC properties
            properties = await self._fetch_user_properties(user_id)
            
            return GSCAuthResponse(
                success=True,
                properties=properties,
                access_token=mock_credentials['token'],
                expires_in=3600
            )
            
        except Exception as e:
            print(f"Error handling OAuth callback: {e}")
            return GSCAuthResponse(
                success=False,
                properties=[],
                access_token=None
            )
    
    async def get_user_properties(self, user_id: str) -> List[GSCProperty]:
        """Get GSC properties for a user"""
        try:
            # Check if user has valid credentials
            credentials = await self._get_user_credentials(user_id)
            if not credentials:
                return []
            
            # Fetch properties from GSC API (mock for now)
            properties = await self._fetch_user_properties_from_api(credentials)
            
            return properties
            
        except Exception as e:
            print(f"Error getting user properties: {e}")
            return []
    
    async def fetch_url_data(
        self, 
        user_id: str, 
        property_url: str, 
        url: str
    ) -> Optional[GSCData]:
        """Fetch URL data from Google Search Console"""
        try:
            # Get user credentials
            credentials = await self._get_user_credentials(user_id)
            if not credentials:
                return None
            
            # Fetch URL inspection data (mock for now)
            url_data = await self._fetch_url_inspection_data(
                credentials, property_url, url
            )
            
            if url_data:
                return GSCData(
                    url=url,
                    coverage_status=url_data.get('coverage_status', GSCCoverageStatus.DISCOVERED),
                    last_crawled=url_data.get('last_crawled'),
                    discovered_date=url_data.get('discovered_date'),
                    indexing_state=url_data.get('indexing_state'),
                    crawl_errors=url_data.get('crawl_errors', []),
                    mobile_usability_issues=url_data.get('mobile_usability_issues', []),
                    page_experience_signals=url_data.get('page_experience_signals', {}),
                    referring_urls=url_data.get('referring_urls', [])
                )
            
            return None
            
        except Exception as e:
            print(f"Error fetching URL data: {e}")
            return None
    
    async def fetch_bulk_url_data(
        self, 
        user_id: str, 
        property_url: str, 
        urls: List[str]
    ) -> List[GSCData]:
        """Fetch data for multiple URLs from GSC"""
        try:
            # Get user credentials
            credentials = await self._get_user_credentials(user_id)
            if not credentials:
                return []
            
            # Batch fetch URL data
            results = []
            
            # Process in batches to avoid rate limits
            batch_size = 10
            for i in range(0, len(urls), batch_size):
                batch_urls = urls[i:i + batch_size]
                
                # Fetch data for each URL in the batch
                batch_tasks = [
                    self.fetch_url_data(user_id, property_url, url)
                    for url in batch_urls
                ]
                
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, GSCData):
                        results.append(result)
                
                # Rate limiting delay
                await asyncio.sleep(0.1)
            
            return results
            
        except Exception as e:
            print(f"Error fetching bulk URL data: {e}")
            return []
    
    async def fetch_coverage_report(
        self, 
        user_id: str, 
        property_url: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, any]:
        """Fetch coverage report from GSC"""
        try:
            # Get user credentials
            credentials = await self._get_user_credentials(user_id)
            if not credentials:
                return {"error": "No valid credentials found"}
            
            # Set default date range if not provided
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Fetch coverage data (mock for now)
            coverage_data = await self._fetch_coverage_data_from_api(
                credentials, property_url, start_date, end_date
            )
            
            return coverage_data
            
        except Exception as e:
            print(f"Error fetching coverage report: {e}")
            return {"error": str(e)}
    
    async def revoke_user_access(self, user_id: str) -> bool:
        """Revoke GSC access for a user"""
        try:
            # Remove stored credentials
            user_creds_ref = self.db.collection('gsc_credentials').where('user_id', '==', user_id)
            docs = user_creds_ref.stream()
            
            for doc in docs:
                doc.reference.delete()
            
            return True
            
        except Exception as e:
            print(f"Error revoking user access: {e}")
            return False
    
    async def _get_service(self, user_id: str):
        """Get GSC service with user credentials"""
        try:
            creds = await google_auth_service.get_refreshed_credentials(user_id)
            if not creds:
                return None
            return build(self.api_name, self.api_version, credentials=creds, cache_discovery=False)
        except Exception as e:
            print(f"Error getting GSC service: {e}")
            return None
    
    async def get_index_status(self, user_id: str, site_url: str) -> Optional[IndexStatus]:
        """Get indexing status for a site"""
        try:
            service = await self._get_service(user_id)
            if not service:
                return None
            
            # Get URL inspection data
            inspection_data = await self._get_url_inspection_data(service, site_url)
            
            # Get coverage data
            coverage_data = await self._get_coverage_data(service, site_url)
            
            # Get mobile usability data
            mobile_data = await self._get_mobile_usability_data(service, site_url)
            
            # Combine all data
            status = IndexStatus(
                site_url=site_url,
                total_urls=coverage_data.get("total_urls", 0),
                indexed_urls=coverage_data.get("indexed_urls", 0),
                not_indexed_urls=coverage_data.get("not_indexed_urls", 0),
                crawled_urls=coverage_data.get("crawled_urls", 0),
                last_updated=datetime.utcnow(),
                coverage_state=coverage_data.get("states", {}),
                mobile_usability=mobile_data,
                errors=coverage_data.get("errors", []),
                warnings=coverage_data.get("warnings", [])
            )
            
            # Store in database
            await self._store_index_status(user_id, status)
            
            return status
            
        except Exception as e:
            print(f"Error getting index status: {e}")
            return None
    
    async def _get_url_inspection_data(self, service, site_url: str) -> Dict[str, Any]:
        """Get URL inspection data from GSC"""
        try:
            # Use the URL Inspection API to get site-wide data
            body = {
                "inspectionUrl": site_url,
                "siteUrl": site_url
            }
            response = service.urlInspection().index().list(body=body).execute()
            return response
        except Exception as e:
            print(f"Error getting URL inspection data: {e}")
            return {}
    
    async def _get_coverage_data(self, service, site_url: str) -> Dict[str, Any]:
        """Get coverage data from GSC"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)  # Last 7 days
            
            body = {
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d"),
                "dimensions": ["page"],
                "rowLimit": 25000  # Maximum allowed
            }
            
            response = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
            
            # Process coverage data
            coverage_data = {
                "total_urls": 0,
                "indexed_urls": 0,
                "not_indexed_urls": 0,
                "crawled_urls": 0,
                "states": {},
                "errors": [],
                "warnings": []
            }
            
            if "rows" in response:
                for row in response["rows"]:
                    coverage_data["total_urls"] += 1
                    if row.get("keys"):
                        url = row["keys"][0]
                        # Get detailed status for this URL
                        try:
                            inspection = service.urlInspection().index().inspect(
                                body={"siteUrl": site_url, "inspectionUrl": url}
                            ).execute()
                            
                            status = inspection.get("inspectionResult", {}).get("indexStatusResult", {})
                            coverage_state = status.get("coverageState", "")
                            
                            # Update counts
                            if coverage_state in ["Indexed", "Submitted and indexed"]:
                                coverage_data["indexed_urls"] += 1
                            else:
                                coverage_data["not_indexed_urls"] += 1
                            
                            if status.get("lastCrawlTime"):
                                coverage_data["crawled_urls"] += 1
                            
                            # Update state counts
                            coverage_data["states"][coverage_state] = coverage_data["states"].get(coverage_state, 0) + 1
                            
                            # Check for errors and warnings
                            if status.get("robotsTxtState") == "BLOCKED":
                                coverage_data["errors"].append(f"Blocked by robots.txt: {url}")
                            if status.get("indexingState") == "BLOCKED_ROBOTS_TXT":
                                coverage_data["errors"].append(f"Indexing blocked by robots.txt: {url}")
                            if status.get("mobileFriendlyIssues"):
                                coverage_data["warnings"].append(f"Mobile usability issues: {url}")
                            
                        except Exception as e:
                            print(f"Error inspecting URL {url}: {e}")
                            continue
            
            return coverage_data
            
        except Exception as e:
            print(f"Error getting coverage data: {e}")
            return {}
    
    async def _get_mobile_usability_data(self, service, site_url: str) -> Dict[str, int]:
        """Get mobile usability data from GSC"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
            
            body = {
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d"),
                "dimensions": ["device"],
                "rowLimit": 10
            }
            
            response = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
            
            mobile_data = {
                "MOBILE_FRIENDLY": 0,
                "MOBILE_ISSUES": 0,
                "NOT_MOBILE_FRIENDLY": 0
            }
            
            if "rows" in response:
                for row in response["rows"]:
                    if row.get("keys") and row["keys"][0] == "MOBILE":
                        # Get detailed mobile usability data
                        try:
                            usability = service.urlInspection().index().inspect(
                                body={
                                    "siteUrl": site_url,
                                    "inspectionUrl": site_url,
                                    "categoryParams": {"category": "MOBILE_USABILITY"}
                                }
                            ).execute()
                            
                            result = usability.get("inspectionResult", {}).get("mobileFriendliness", "")
                            mobile_data[result] = mobile_data.get(result, 0) + 1
                            
                        except Exception as e:
                            print(f"Error getting mobile usability: {e}")
                            continue
            
            return mobile_data
            
        except Exception as e:
            print(f"Error getting mobile usability data: {e}")
            return {}
    
    async def _store_index_status(self, user_id: str, status: IndexStatus):
        """Store index status in database"""
        try:
            doc_id = f"{user_id}_{status.site_url}"
            doc_ref = self.db.collection(self.index_status_collection).document(doc_id)
            doc_ref.set(status.dict())
        except Exception as e:
            print(f"Error storing index status: {e}")
    
    async def get_stored_index_status(self, user_id: str, site_url: str) -> Optional[IndexStatus]:
        """Get stored index status from database"""
        try:
            doc_id = f"{user_id}_{site_url}"
            doc = self.db.collection(self.index_status_collection).document(doc_id).get()
            if doc.exists:
                return IndexStatus(**doc.to_dict())
            return None
        except Exception as e:
            print(f"Error getting stored index status: {e}")
            return None
    
    # Private helper methods
    
    async def _store_user_credentials(self, user_id: str, credentials: Dict) -> None:
        """Store user's GSC credentials"""
        try:
            credential_data = {
                'user_id': user_id,
                'credentials': credentials,
                'created_at': datetime.utcnow(),
                'last_used': datetime.utcnow()
            }
            
            # Check if credentials already exist
            existing_creds = self.db.collection('gsc_credentials')\
                .where('user_id', '==', user_id)\
                .limit(1)\
                .stream()
            
            existing_doc = None
            for doc in existing_creds:
                existing_doc = doc
                break
            
            if existing_doc:
                # Update existing credentials
                existing_doc.reference.update({
                    'credentials': credentials,
                    'last_used': datetime.utcnow()
                })
            else:
                # Create new credentials document
                self.db.collection('gsc_credentials').add(credential_data)
                
        except Exception as e:
            print(f"Error storing user credentials: {e}")
    
    async def _get_user_credentials(self, user_id: str) -> Optional[Dict]:
        """Get user's GSC credentials"""
        try:
            docs = self.db.collection('gsc_credentials')\
                .where('user_id', '==', user_id)\
                .limit(1)\
                .stream()
            
            for doc in docs:
                data = doc.to_dict()
                credentials = data.get('credentials')
                return credentials
            
            return None
            
        except Exception as e:
            print(f"Error getting user credentials: {e}")
            return None
    
    async def _fetch_user_properties(self, user_id: str) -> List[GSCProperty]:
        """Fetch user's GSC properties"""
        try:
            credentials = await self._get_user_credentials(user_id)
            if not credentials:
                return []
            
            return await self._fetch_user_properties_from_api(credentials)
            
        except Exception as e:
            print(f"Error fetching user properties: {e}")
            return []
    
    async def _fetch_user_properties_from_api(self, credentials: Dict) -> List[GSCProperty]:
        """Fetch properties from GSC API (mock implementation)"""
        try:
            # Mock API call - simulate delay
            await asyncio.sleep(0.1)
            
            # Mock properties data
            mock_properties = [
                GSCProperty(
                    property_url="https://example.com/",
                    property_type="URL_PREFIX",
                    permission_level="FULL",
                    verified=True
                ),
                GSCProperty(
                    property_url="sc-domain:example.com",
                    property_type="DOMAIN",
                    permission_level="FULL",
                    verified=True
                )
            ]
            
            return mock_properties
            
        except Exception as e:
            print(f"Error fetching properties from API: {e}")
            return []
    
    async def _fetch_url_inspection_data(
        self, 
        credentials: Dict, 
        property_url: str, 
        url: str
    ) -> Optional[Dict]:
        """Fetch URL inspection data from GSC API (mock implementation)"""
        try:
            # Mock API call
            await asyncio.sleep(0.1)
            
            # Mock URL inspection data
            import random
            
            coverage_statuses = list(GSCCoverageStatus)
            mock_data = {
                'coverage_status': random.choice(coverage_statuses),
                'last_crawled': datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                'discovered_date': datetime.utcnow() - timedelta(days=random.randint(30, 90)),
                'indexing_state': 'URL is on Google',
                'crawl_errors': [],
                'mobile_usability_issues': [],
                'page_experience_signals': {
                    'core_web_vitals': 'GOOD',
                    'mobile_friendly': True
                },
                'referring_urls': []
            }
            
            return mock_data
            
        except Exception as e:
            print(f"Error fetching URL inspection data: {e}")
            return None
    
    async def _fetch_coverage_data_from_api(
        self, 
        credentials: Dict, 
        property_url: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> Dict[str, any]:
        """Fetch coverage data from GSC API"""
        try:
            # Mock API call - in production, this would use the Search Analytics API
            await asyncio.sleep(0.2)  # Simulate API delay
            
            # Mock coverage report data
            mock_coverage_data = {
                'total_indexed_pages': 1250,
                'total_discovered_pages': 1500,
                'total_excluded_pages': 350,
                'total_error_pages': 25,
                'coverage_breakdown': {
                    'indexed': 1250,
                    'discovered_not_indexed': 250,
                    'excluded': 350,
                    'error': 25
                },
                'indexing_trends': [
                    {
                        'date': (start_date + timedelta(days=i)).isoformat(),
                        'indexed': 1200 + i * 2,
                        'discovered': 1400 + i * 3,
                        'excluded': 340 + i,
                        'error': 30 - i // 5
                    }
                    for i in range((end_date - start_date).days + 1)
                ],
                'top_issues': [
                    {
                        'issue_type': 'Crawled - currently not indexed',
                        'affected_urls': 180,
                        'examples': ['https://example.com/page1', 'https://example.com/page2']
                    },
                    {
                        'issue_type': 'Discovered - currently not indexed',
                        'affected_urls': 70,
                        'examples': ['https://example.com/page3', 'https://example.com/page4']
                    }
                ]
            }
            
            return mock_coverage_data
            
        except Exception as e:
            print(f"Error fetching coverage data: {e}")
            return {"error": str(e)}

# Global service instance
gsc_service = GSCService() 