import asyncio
import json
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin
import requests
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build

from db.firestore import get_or_create_firestore_client
from models.sitemap import (
    SitemapEntry, SitemapStatus, IndexingHistory, IndexingResponse
)
from services.gsc_service import GSCService

class SitemapService:
    """Service for sitemap management and Google Search Console integration"""
    
    def __init__(self):
        self.db = get_or_create_firestore_client()
        self.gsc_service = GSCService()
        self.sitemap_collection = "sitemaps"
        
        # Google Search Console API configuration
        self.api_name = "searchconsole"
        self.api_version = "v1"
        self.scopes = [
            "https://www.googleapis.com/auth/webmasters",
            "https://www.googleapis.com/auth/webmasters.readonly"
        ]
        
        # Initialize Google service
        self.service = self._initialize_google_service()
        
    def _initialize_google_service(self):
        """Initialize Google Search Console API service"""
        try:
            # Load service account credentials from environment or file
            service_account_info = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            
            if service_account_info:
                # Parse JSON from environment variable
                service_account_dict = json.loads(service_account_info)
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_dict, scopes=self.scopes
                )
            else:
                # Load from file
                service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'serviceAccountKey.json')
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_file, scopes=self.scopes
                )
            
            return build(self.api_name, self.api_version, credentials=credentials)
            
        except Exception as e:
            print(f"Error initializing Google Search Console service: {e}")
            return None
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return url.lower()
    
    async def submit_sitemap(
        self, 
        user_id: str, 
        property_url: str, 
        sitemap_url: str
    ) -> SitemapEntry:
        """Submit a sitemap to Google Search Console"""
        try:
            domain = self._extract_domain(property_url)
            
            # Create sitemap entry
            entry = SitemapEntry(
                id=str(uuid.uuid4()),
                sitemap_url=sitemap_url,
                property_url=property_url,
                domain=domain,
                user_id=user_id,
                status=SitemapStatus.PENDING
            )
            
            # Store entry in database
            await self._store_sitemap_entry(entry)
            
            # Submit to Google Search Console
            success = await self._submit_sitemap_to_gsc(entry)
            
            if success:
                entry.status = SitemapStatus.SUBMITTED
                entry.submitted_at = datetime.utcnow()
                
                # Analyze sitemap content
                await self._analyze_sitemap_content(entry)
            else:
                entry.status = SitemapStatus.FAILED
                entry.completed_at = datetime.utcnow()
            
            # Update entry in database
            await self._update_sitemap_entry(entry)
            
            return entry
            
        except Exception as e:
            print(f"Error submitting sitemap: {e}")
            entry = SitemapEntry(
                id=str(uuid.uuid4()),
                sitemap_url=sitemap_url,
                property_url=property_url,
                domain=self._extract_domain(property_url),
                user_id=user_id,
                status=SitemapStatus.FAILED,
                error_message=str(e)
            )
            await self._store_sitemap_entry(entry)
            return entry
    
    async def _submit_sitemap_to_gsc(self, entry: SitemapEntry) -> bool:
        """Submit sitemap to Google Search Console API"""
        try:
            if not self.service:
                entry.error_message = "Google Search Console service not initialized"
                return False
            
            # Submit sitemap to GSC
            request = self.service.sitemaps().submit(
                siteUrl=entry.property_url,
                feedpath=entry.sitemap_url
            )
            
            response = request.execute()
            
            # Store Google's response
            entry.google_response = response if response else {"submitted": True}
            
            return True
                
        except Exception as e:
            print(f"Error calling Google Search Console API: {e}")
            entry.error_message = str(e)
            return False
    
    async def delete_sitemap(
        self, 
        user_id: str, 
        property_url: str, 
        sitemap_url: str
    ) -> Dict[str, any]:
        """Delete a sitemap from Google Search Console"""
        try:
            if not self.service:
                return {"success": False, "error": "Google Search Console service not initialized"}
            
            # Delete sitemap from GSC
            request = self.service.sitemaps().delete(
                siteUrl=property_url,
                feedpath=sitemap_url
            )
            
            response = request.execute()
            
            # Update entry in database if exists
            await self._update_sitemap_status_by_url(
                user_id, sitemap_url, SitemapStatus.DELETED
            )
            
            return {
                "success": True,
                "message": "Sitemap deleted successfully",
                "sitemap_url": sitemap_url,
                "property_url": property_url
            }
                
        except Exception as e:
            print(f"Error deleting sitemap: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_sitemaps_list(
        self, 
        user_id: str, 
        property_url: str
    ) -> List[Dict[str, any]]:
        """Get list of sitemaps from Google Search Console"""
        try:
            if not self.service:
                return []
            
            # Get sitemaps from GSC
            request = self.service.sitemaps().list(siteUrl=property_url)
            response = request.execute()
            
            sitemaps = response.get('sitemap', [])
            
            # Enhance with local database info
            enhanced_sitemaps = []
            for sitemap in sitemaps:
                sitemap_url = sitemap.get('feedpath')
                
                # Get additional info from local database
                local_entry = await self._get_sitemap_by_url(user_id, sitemap_url)
                
                enhanced_sitemap = {
                    "sitemap_url": sitemap_url,
                    "path": sitemap.get('path'),
                    "type": sitemap.get('type'),
                    "lastSubmitted": sitemap.get('lastSubmitted'),
                    "isPending": sitemap.get('isPending', False),
                    "isSitemapsIndex": sitemap.get('isSitemapsIndex', False),
                    "contents": sitemap.get('contents', []),
                    "errors": sitemap.get('errors', 0),
                    "warnings": sitemap.get('warnings', 0),
                    "local_info": local_entry.dict() if local_entry else None
                }
                
                enhanced_sitemaps.append(enhanced_sitemap)
            
            return enhanced_sitemaps
                
        except Exception as e:
            print(f"Error getting sitemaps list: {e}")
            return []
    
    async def _analyze_sitemap_content(self, entry: SitemapEntry) -> bool:
        """Analyze sitemap content and extract URLs"""
        try:
            # Fetch sitemap XML
            response = requests.get(entry.sitemap_url, timeout=30)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Handle namespace
            namespaces = {
                'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'
            }
            
            urls = []
            url_count = 0
            
            # Check if it's a sitemap index
            if root.tag.endswith('sitemapindex'):
                entry.is_sitemap_index = True
                # Extract child sitemaps
                for sitemap in root.findall('sitemap:sitemap', namespaces):
                    loc = sitemap.find('sitemap:loc', namespaces)
                    if loc is not None:
                        urls.append(loc.text)
                        url_count += 1
            else:
                # Regular sitemap with URLs
                for url in root.findall('sitemap:url', namespaces):
                    loc = url.find('sitemap:loc', namespaces)
                    if loc is not None:
                        urls.append(loc.text)
                        url_count += 1
            
            # Update entry with analysis results
            entry.url_count = url_count
            entry.urls_sample = urls[:100]  # Store first 100 URLs as sample
            entry.last_analyzed = datetime.utcnow()
            entry.content_analyzed = True
            
            return True
            
        except Exception as e:
            print(f"Error analyzing sitemap content: {e}")
            entry.error_message = f"Content analysis failed: {str(e)}"
            return False
    
    async def auto_discover_sitemaps(
        self, 
        user_id: str, 
        property_url: str
    ) -> List[str]:
        """Auto-discover sitemaps from robots.txt"""
        try:
            sitemap_urls = []
            
            # Check robots.txt
            robots_url = urljoin(property_url, '/robots.txt')
            
            try:
                response = requests.get(robots_url, timeout=10)
                response.raise_for_status()
                
                # Parse robots.txt for sitemap entries
                for line in response.text.splitlines():
                    line = line.strip()
                    if line.lower().startswith('sitemap:'):
                        sitemap_url = line[8:].strip()
                        if sitemap_url.startswith(('http://', 'https://')):
                            sitemap_urls.append(sitemap_url)
                
            except Exception as e:
                print(f"Error fetching robots.txt: {e}")
            
            # Common sitemap locations if none found in robots.txt
            if not sitemap_urls:
                common_paths = [
                    '/sitemap.xml',
                    '/sitemap_index.xml',
                    '/sitemaps.xml',
                    '/sitemap/sitemap.xml'
                ]
                
                for path in common_paths:
                    sitemap_url = urljoin(property_url, path)
                    
                    # Check if sitemap exists
                    try:
                        response = requests.head(sitemap_url, timeout=5)
                        if response.status_code == 200:
                            sitemap_urls.append(sitemap_url)
                    except Exception:
                        continue
            
            return sitemap_urls
            
        except Exception as e:
            print(f"Error auto-discovering sitemaps: {e}")
            return []
    
    async def sync_sitemaps_daily(self, user_id: Optional[str] = None) -> int:
        """Daily sync of sitemaps - used by background job"""
        try:
            synced_count = 0
            
            # Get all submitted sitemaps that need sync
            query = self.db.collection(self.sitemap_collection) \
                       .where('status', '==', SitemapStatus.SUBMITTED.value) \
                       .where('auto_sync', '==', True)
            
            if user_id:
                query = query.where('user_id', '==', user_id)
            
            docs = query.stream()
            
            for doc in docs:
                try:
                    data = doc.to_dict()
                    data['id'] = doc.id
                    entry = SitemapEntry(**data)
                    
                    # Re-analyze sitemap content
                    success = await self._analyze_sitemap_content(entry)
                    
                    if success:
                        entry.last_synced = datetime.utcnow()
                        await self._update_sitemap_entry(entry)
                        synced_count += 1
                    
                    # Rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"Error syncing sitemap {doc.id}: {e}")
                    continue
            
            return synced_count
            
        except Exception as e:
            print(f"Error during daily sitemap sync: {e}")
            return 0
    
    async def get_sitemap_history(
        self, 
        user_id: str, 
        page: int = 1, 
        page_size: int = 50
    ) -> Tuple[List[SitemapEntry], int]:
        """Get sitemap submission history"""
        try:
            # Build query
            query = self.db.collection(self.sitemap_collection) \
                       .where('user_id', '==', user_id) \
                       .order_by('created_at', direction='DESCENDING')
            
            # Get total count
            all_docs = query.stream()
            total_count = sum(1 for _ in all_docs)
            
            # Get paginated results
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
            
            docs = query.stream()
            entries = []
            
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                entries.append(SitemapEntry(**data))
            
            return entries, total_count
            
        except Exception as e:
            print(f"Error getting sitemap history: {e}")
            return [], 0
    
    async def _store_sitemap_entry(self, entry: SitemapEntry) -> bool:
        """Store sitemap entry in database"""
        try:
            doc_ref = self.db.collection(self.sitemap_collection).document(entry.id)
            doc_ref.set(entry.dict(exclude={'id'}))
            return True
        except Exception as e:
            print(f"Error storing sitemap entry: {e}")
            return False
    
    async def _update_sitemap_entry(self, entry: SitemapEntry) -> bool:
        """Update sitemap entry in database"""
        try:
            doc_ref = self.db.collection(self.sitemap_collection).document(entry.id)
            doc_ref.update(entry.dict(exclude={'id'}))
            return True
        except Exception as e:
            print(f"Error updating sitemap entry: {e}")
            return False
    
    async def _get_sitemap_by_url(self, user_id: str, sitemap_url: str) -> Optional[SitemapEntry]:
        """Get sitemap entry by URL"""
        try:
            query = self.db.collection(self.sitemap_collection) \
                       .where('user_id', '==', user_id) \
                       .where('sitemap_url', '==', sitemap_url) \
                       .limit(1)
            
            docs = list(query.stream())
            
            if docs:
                data = docs[0].to_dict()
                data['id'] = docs[0].id
                return SitemapEntry(**data)
            
            return None
            
        except Exception as e:
            print(f"Error getting sitemap by URL: {e}")
            return None
    
    async def _update_sitemap_status_by_url(
        self, 
        user_id: str, 
        sitemap_url: str, 
        status: SitemapStatus
    ) -> bool:
        """Update sitemap status by URL"""
        try:
            query = self.db.collection(self.sitemap_collection) \
                       .where('user_id', '==', user_id) \
                       .where('sitemap_url', '==', sitemap_url)
            
            docs = query.stream()
            
            for doc in docs:
                doc.reference.update({
                    'status': status.value,
                    'updated_at': datetime.utcnow()
                })
            
            return True
            
        except Exception as e:
            print(f"Error updating sitemap status: {e}")
            return False

# Global service instance
sitemap_service = SitemapService() 