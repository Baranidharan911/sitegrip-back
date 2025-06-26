import asyncio
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

from db.firestore import get_or_create_firestore_client
from models.sitemap import (
    SitemapEntry, SitemapStatus, IndexingHistory, IndexingResponse
)

class SitemapService:
    """Service for managing sitemap operations"""
    
    def __init__(self):
        self.db = get_or_create_firestore_client()
        self.google_sitemap_api_url = "https://www.google.com/webmasters/tools/feeds/{property}/sitemaps/"
        
    async def submit_sitemap(
        self, 
        sitemap_url: str, 
        auto_sync: bool, 
        project_id: str, 
        user_id: str
    ) -> IndexingResponse:
        """Submit a sitemap to Google"""
        
        try:
            # Validate sitemap URL
            if not self._is_valid_url(sitemap_url):
                return IndexingResponse(
                    success=False,
                    message="Invalid sitemap URL",
                    errors=["URL must be a valid HTTP/HTTPS URL"]
                )
            
            # Extract domain
            domain = self._extract_domain(sitemap_url)
            
            # Check if sitemap already exists
            existing_sitemap = await self._get_existing_sitemap(sitemap_url, user_id, project_id)
            if existing_sitemap:
                return IndexingResponse(
                    success=False,
                    message="Sitemap already exists",
                    errors=["This sitemap has already been submitted"]
                )
            
            # Validate sitemap content
            validation_result = await self._validate_sitemap_content(sitemap_url)
            if not validation_result["valid"]:
                return IndexingResponse(
                    success=False,
                    message="Invalid sitemap content",
                    errors=validation_result["errors"]
                )
            
            # Create sitemap entry
            sitemap_entry = SitemapEntry(
                sitemap_url=sitemap_url,
                status=SitemapStatus.SUBMITTED,
                domain=domain,
                auto_sync=auto_sync,
                urls_count=validation_result.get("url_count", 0),
                project_id=project_id,
                user_id=user_id
            )
            
            # Save to database
            sitemap_id = await self._save_sitemap_entry(sitemap_entry)
            
            # Submit to Google (mock for now)
            submission_result = await self._submit_sitemap_to_google(sitemap_url, user_id)
            
            if submission_result["success"]:
                # Update status
                await self._update_sitemap_status(sitemap_id, SitemapStatus.SUCCESS)
                
                # Log action
                await self._log_sitemap_action(
                    action_type="submit_sitemap",
                    sitemap_url=sitemap_url,
                    status="success",
                    user_id=user_id,
                    project_id=project_id,
                    details={"url_count": validation_result.get("url_count", 0)}
                )
                
                return IndexingResponse(
                    success=True,
                    message="Sitemap submitted successfully",
                    data={
                        "sitemap_id": sitemap_id,
                        "url_count": validation_result.get("url_count", 0),
                        "auto_sync": auto_sync
                    }
                )
            else:
                # Update status to error
                await self._update_sitemap_status(
                    sitemap_id, 
                    SitemapStatus.ERROR, 
                    submission_result.get("error", "Unknown error")
                )
                
                return IndexingResponse(
                    success=False,
                    message="Failed to submit sitemap",
                    errors=[submission_result.get("error", "Unknown error")]
                )
                
        except Exception as e:
            return IndexingResponse(
                success=False,
                message="Internal error occurred",
                errors=[str(e)]
            )
    
    async def delete_sitemap(
        self, 
        sitemap_url: str, 
        user_id: str, 
        project_id: str
    ) -> IndexingResponse:
        """Delete a sitemap from Google"""
        
        try:
            # Find existing sitemap
            existing_sitemap = await self._get_existing_sitemap(sitemap_url, user_id, project_id)
            if not existing_sitemap:
                return IndexingResponse(
                    success=False,
                    message="Sitemap not found",
                    errors=["Sitemap does not exist in the system"]
                )
            
            # Submit deletion to Google (mock for now)
            deletion_result = await self._delete_sitemap_from_google(sitemap_url, user_id)
            
            if deletion_result["success"]:
                # Update status to deleted
                await self._update_sitemap_status(
                    existing_sitemap["id"], 
                    SitemapStatus.DELETED
                )
                
                # Log action
                await self._log_sitemap_action(
                    action_type="delete_sitemap",
                    sitemap_url=sitemap_url,
                    status="success",
                    user_id=user_id,
                    project_id=project_id
                )
                
                return IndexingResponse(
                    success=True,
                    message="Sitemap deleted successfully"
                )
            else:
                return IndexingResponse(
                    success=False,
                    message="Failed to delete sitemap",
                    errors=[deletion_result.get("error", "Unknown error")]
                )
                
        except Exception as e:
            return IndexingResponse(
                success=False,
                message="Internal error occurred",
                errors=[str(e)]
            )
    
    async def get_sitemaps(
        self, 
        user_id: str, 
        project_id: Optional[str] = None,
        limit: int = 100
    ) -> List[SitemapEntry]:
        """Get sitemaps for a user/project"""
        try:
            query = self.db.collection('sitemaps').where('user_id', '==', user_id)
            
            if project_id:
                query = query.where('project_id', '==', project_id)
            
            query = query.order_by('submitted_at', direction='DESCENDING').limit(limit)
            
            docs = query.stream()
            sitemaps = []
            
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                sitemaps.append(SitemapEntry(**data))
            
            return sitemaps
            
        except Exception as e:
            print(f"Error getting sitemaps: {e}")
            return []
    
    async def sync_sitemaps_daily(self, user_id: str, project_id: str) -> Dict[str, any]:
        """Perform daily auto-sync for sitemaps"""
        try:
            # Get sitemaps with auto-sync enabled
            auto_sync_sitemaps = await self._get_auto_sync_sitemaps(user_id, project_id)
            
            sync_results = {
                "total_sitemaps": len(auto_sync_sitemaps),
                "successful_syncs": 0,
                "failed_syncs": 0,
                "errors": []
            }
            
            for sitemap in auto_sync_sitemaps:
                try:
                    # Re-submit sitemap
                    sync_result = await self._submit_sitemap_to_google(
                        sitemap.sitemap_url, 
                        user_id
                    )
                    
                    if sync_result["success"]:
                        # Update last sync time
                        await self._update_sitemap_last_sync(sitemap)
                        sync_results["successful_syncs"] += 1
                        
                        # Log sync action
                        await self._log_sitemap_action(
                            action_type="auto_sync_sitemap",
                            sitemap_url=sitemap.sitemap_url,
                            status="success",
                            user_id=user_id,
                            project_id=project_id
                        )
                    else:
                        sync_results["failed_syncs"] += 1
                        sync_results["errors"].append(
                            f"{sitemap.sitemap_url}: {sync_result.get('error', 'Unknown error')}"
                        )
                        
                except Exception as e:
                    sync_results["failed_syncs"] += 1
                    sync_results["errors"].append(f"{sitemap.sitemap_url}: {str(e)}")
            
            return sync_results
            
        except Exception as e:
            return {
                "total_sitemaps": 0,
                "successful_syncs": 0,
                "failed_syncs": 0,
                "errors": [str(e)]
            }
    
    async def analyze_sitemap_content(self, sitemap_url: str) -> Dict[str, any]:
        """Analyze sitemap content and extract URLs"""
        try:
            # Download and parse sitemap
            response = requests.get(sitemap_url, timeout=30)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            
            if 'xml' in content_type:
                return await self._parse_xml_sitemap(response.content)
            elif 'text' in content_type:
                return await self._parse_text_sitemap(response.text)
            else:
                # Try to detect format by content
                try:
                    ET.fromstring(response.content)
                    return await self._parse_xml_sitemap(response.content)
                except ET.ParseError:
                    return await self._parse_text_sitemap(response.text)
                    
        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "urls": [],
                "url_count": 0
            }
    
    async def discover_sitemaps_from_robots(self, domain: str) -> List[str]:
        """Discover sitemaps from robots.txt"""
        try:
            robots_url = f"https://{domain}/robots.txt"
            
            try:
                response = requests.get(robots_url, timeout=10)
                response.raise_for_status()
            except:
                # Try with http if https fails
                robots_url = f"http://{domain}/robots.txt"
                response = requests.get(robots_url, timeout=10)
                response.raise_for_status()
            
            sitemap_urls = []
            lines = response.text.split('\n')
            
            for line in lines:
                line = line.strip()
                if line.lower().startswith('sitemap:'):
                    sitemap_url = line.split(':', 1)[1].strip()
                    if self._is_valid_url(sitemap_url):
                        sitemap_urls.append(sitemap_url)
            
            return sitemap_urls
            
        except Exception as e:
            print(f"Error discovering sitemaps from robots.txt: {e}")
            return []
    
    # Private helper methods
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc) and parsed.scheme in ['http', 'https']
        except Exception:
            return False
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return "unknown"
    
    async def _get_existing_sitemap(
        self, 
        sitemap_url: str, 
        user_id: str, 
        project_id: str
    ) -> Optional[Dict]:
        """Check if sitemap already exists"""
        try:
            docs = self.db.collection('sitemaps')\
                .where('sitemap_url', '==', sitemap_url)\
                .where('user_id', '==', user_id)\
                .where('project_id', '==', project_id)\
                .limit(1)\
                .stream()
            
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                return data
            
            return None
            
        except Exception as e:
            print(f"Error checking existing sitemap: {e}")
            return None
    
    async def _validate_sitemap_content(self, sitemap_url: str) -> Dict[str, any]:
        """Validate sitemap content"""
        try:
            analysis = await self.analyze_sitemap_content(sitemap_url)
            return analysis
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "url_count": 0
            }
    
    async def _save_sitemap_entry(self, sitemap: SitemapEntry) -> str:
        """Save sitemap entry to database"""
        try:
            doc_ref = self.db.collection('sitemaps').add(sitemap.dict())
            return doc_ref[1].id
        except Exception as e:
            print(f"Error saving sitemap entry: {e}")
            raise
    
    async def _update_sitemap_status(
        self, 
        sitemap_id: str, 
        status: SitemapStatus, 
        error_message: Optional[str] = None
    ) -> bool:
        """Update sitemap status"""
        try:
            update_data = {
                'status': status.value,
                'last_submitted': datetime.utcnow()
            }
            
            if error_message:
                update_data['error_message'] = error_message
            
            self.db.collection('sitemaps').document(sitemap_id).update(update_data)
            return True
            
        except Exception as e:
            print(f"Error updating sitemap status: {e}")
            return False
    
    async def _submit_sitemap_to_google(self, sitemap_url: str, user_id: str) -> Dict[str, any]:
        """Submit sitemap to Google (mock implementation)"""
        try:
            # Mock implementation - in production, this would:
            # 1. Get user's Google Search Console credentials
            # 2. Make authenticated request to GSC API
            # 3. Handle response and return appropriate status
            
            # Simulate API call
            await asyncio.sleep(0.2)  # Simulate network delay
            
            # Mock success rate of 95%
            import random
            if random.random() < 0.95:
                return {"success": True, "message": "Sitemap submitted successfully"}
            else:
                return {"success": False, "error": "Failed to submit sitemap to Google"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _delete_sitemap_from_google(self, sitemap_url: str, user_id: str) -> Dict[str, any]:
        """Delete sitemap from Google (mock implementation)"""
        try:
            # Mock implementation
            await asyncio.sleep(0.1)
            
            # Mock success rate of 98%
            import random
            if random.random() < 0.98:
                return {"success": True, "message": "Sitemap deleted successfully"}
            else:
                return {"success": False, "error": "Failed to delete sitemap from Google"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _get_auto_sync_sitemaps(self, user_id: str, project_id: str) -> List[SitemapEntry]:
        """Get sitemaps with auto-sync enabled"""
        try:
            docs = self.db.collection('sitemaps')\
                .where('user_id', '==', user_id)\
                .where('project_id', '==', project_id)\
                .where('auto_sync', '==', True)\
                .where('status', 'in', [SitemapStatus.SUBMITTED.value, SitemapStatus.SUCCESS.value])\
                .stream()
            
            sitemaps = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                sitemaps.append(SitemapEntry(**data))
            
            return sitemaps
            
        except Exception as e:
            print(f"Error getting auto-sync sitemaps: {e}")
            return []
    
    async def _update_sitemap_last_sync(self, sitemap: SitemapEntry) -> bool:
        """Update last sync time for sitemap"""
        try:
            if hasattr(sitemap, 'id'):
                self.db.collection('sitemaps').document(sitemap.id).update({
                    'last_sync_at': datetime.utcnow()
                })
                return True
            return False
            
        except Exception as e:
            print(f"Error updating sitemap last sync: {e}")
            return False
    
    async def _parse_xml_sitemap(self, content: bytes) -> Dict[str, any]:
        """Parse XML sitemap content"""
        try:
            root = ET.fromstring(content)
            
            # Handle different sitemap namespaces
            namespaces = {
                'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9',
                'image': 'http://www.google.com/schemas/sitemap-image/1.1',
                'news': 'http://www.google.com/schemas/sitemap-news/0.9'
            }
            
            urls = []
            
            # Check if it's a sitemap index
            sitemapindex_urls = root.findall('sitemap:sitemap/sitemap:loc', namespaces)
            if sitemapindex_urls:
                # It's a sitemap index
                for url_elem in sitemapindex_urls:
                    if url_elem.text:
                        urls.append(url_elem.text.strip())
            else:
                # It's a regular sitemap
                url_elements = root.findall('sitemap:url/sitemap:loc', namespaces)
                for url_elem in url_elements:
                    if url_elem.text:
                        urls.append(url_elem.text.strip())
            
            return {
                "valid": True,
                "urls": urls,
                "url_count": len(urls),
                "errors": [],
                "type": "xml_sitemap"
            }
            
        except ET.ParseError as e:
            return {
                "valid": False,
                "errors": [f"XML parsing error: {str(e)}"],
                "urls": [],
                "url_count": 0
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "urls": [],
                "url_count": 0
            }
    
    async def _parse_text_sitemap(self, content: str) -> Dict[str, any]:
        """Parse text sitemap content"""
        try:
            lines = content.strip().split('\n')
            urls = []
            
            for line in lines:
                line = line.strip()
                if line and self._is_valid_url(line):
                    urls.append(line)
            
            return {
                "valid": True,
                "urls": urls,
                "url_count": len(urls),
                "errors": [],
                "type": "text_sitemap"
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "urls": [],
                "url_count": 0
            }
    
    async def _log_sitemap_action(
        self,
        action_type: str,
        sitemap_url: str,
        status: str,
        user_id: str,
        project_id: str,
        details: Optional[Dict] = None
    ) -> None:
        """Log sitemap action to history"""
        try:
            history_entry = IndexingHistory(
                action_id=str(uuid.uuid4()),
                action_type=action_type,
                sitemap_url=sitemap_url,
                status=status,
                user_id=user_id,
                project_id=project_id,
                details=details or {}
            )
            
            self.db.collection('indexing_history').add(history_entry.dict())
            
        except Exception as e:
            print(f"Error logging sitemap action: {e}")

# Global service instance
sitemap_service = SitemapService() 