import ssl
import socket
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from urllib.parse import urlparse
import httpx
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from models.ssl_info import SSLInfo

class SSLChecker:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    async def check_ssl_certificate(self, url: str) -> Optional[SSLInfo]:
        """Check SSL certificate for a given URL"""
        try:
            parsed_url = urlparse(url)
            
            # Only check SSL for HTTPS URLs
            if parsed_url.scheme != 'https':
                return None
            
            hostname = parsed_url.hostname
            port = parsed_url.port or 443
            
            if not hostname:
                return SSLInfo(
                    is_valid=False,
                    error_message="Invalid hostname"
                )
            
            # Get certificate using socket connection
            cert_info = await self._get_certificate_info(hostname, port)
            return cert_info
            
        except Exception as e:
            return SSLInfo(
                is_valid=False,
                error_message=f"SSL check failed: {str(e)}"
            )

    async def _get_certificate_info(self, hostname: str, port: int) -> SSLInfo:
        """Get SSL certificate information from hostname and port"""
        try:
            # Create SSL context
            context = ssl.create_default_context()
            
            # Get certificate
            loop = asyncio.get_event_loop()
            cert_der = await loop.run_in_executor(
                None, 
                self._get_cert_der, 
                hostname, 
                port, 
                context
            )
            
            if not cert_der:
                return SSLInfo(
                    is_valid=False,
                    error_message="Could not retrieve certificate"
                )
            
            # Parse certificate
            cert = x509.load_der_x509_certificate(cert_der, default_backend())
            
            # Extract certificate information
            return self._parse_certificate(cert, hostname)
            
        except ssl.SSLError as e:
            return SSLInfo(
                is_valid=False,
                error_message=f"SSL Error: {str(e)}"
            )
        except Exception as e:
            return SSLInfo(
                is_valid=False,
                error_message=f"Certificate parsing error: {str(e)}"
            )

    def _get_cert_der(self, hostname: str, port: int, context: ssl.SSLContext) -> Optional[bytes]:
        """Get certificate DER data using socket connection"""
        try:
            with socket.create_connection((hostname, port), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert_der = ssock.getpeercert(binary_form=True)
                    return cert_der
        except Exception:
            return None

    def _parse_certificate(self, cert: x509.Certificate, hostname: str) -> SSLInfo:
        """Parse certificate and extract relevant information"""
        try:
            now = datetime.now(timezone.utc)
            
            # Basic certificate info
            not_valid_after = cert.not_valid_after.replace(tzinfo=timezone.utc)
            not_valid_before = cert.not_valid_before.replace(tzinfo=timezone.utc)
            
            days_until_expiry = (not_valid_after - now).days
            is_expired = now > not_valid_after
            is_expiring_soon = days_until_expiry <= 30 and days_until_expiry > 0
            
            # Extract issuer and subject
            issuer = self._get_name_attribute(cert.issuer, x509.NameOID.COMMON_NAME)
            subject = self._get_name_attribute(cert.subject, x509.NameOID.COMMON_NAME)
            
            # Get Subject Alternative Names (SAN)
            san_domains = self._get_san_domains(cert)
            
            # Check if certificate is self-signed
            is_self_signed = issuer == subject
            
            # Validate hostname against certificate
            hostname_valid = self._validate_hostname(cert, hostname)
            
            return SSLInfo(
                is_valid=hostname_valid and not is_expired,
                expires_at=not_valid_after,
                issued_at=not_valid_before,
                days_until_expiry=days_until_expiry,
                issuer=issuer,
                subject=subject,
                serial_number=str(cert.serial_number),
                signature_algorithm=cert.signature_algorithm_oid._name,
                version=cert.version.value,
                san_domains=san_domains,
                is_self_signed=is_self_signed,
                is_expired=is_expired,
                is_expiring_soon=is_expiring_soon,
                chain_valid=hostname_valid,  # Simplified for now
                error_message=None if hostname_valid and not is_expired else 
                             "Certificate expired" if is_expired else 
                             "Hostname mismatch" if not hostname_valid else None
            )
            
        except Exception as e:
            return SSLInfo(
                is_valid=False,
                error_message=f"Certificate parsing failed: {str(e)}"
            )

    def _get_name_attribute(self, name: x509.Name, oid: x509.ObjectIdentifier) -> Optional[str]:
        """Extract attribute from certificate name"""
        try:
            attributes = name.get_attributes_for_oid(oid)
            if attributes:
                return attributes[0].value
        except Exception:
            pass
        return None

    def _get_san_domains(self, cert: x509.Certificate) -> List[str]:
        """Extract Subject Alternative Names from certificate"""
        san_domains = []
        try:
            san_extension = cert.extensions.get_extension_for_oid(
                x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME
            )
            san_domains = [
                name.value for name in san_extension.value
                if isinstance(name, x509.DNSName)
            ]
        except x509.ExtensionNotFound:
            pass
        except Exception:
            pass
        return san_domains

    def _validate_hostname(self, cert: x509.Certificate, hostname: str) -> bool:
        """Validate if hostname matches certificate"""
        try:
            # Get common name
            subject_cn = self._get_name_attribute(cert.subject, x509.NameOID.COMMON_NAME)
            
            # Get SAN domains
            san_domains = self._get_san_domains(cert)
            
            # Check if hostname matches CN or any SAN domain
            valid_names = [subject_cn] + san_domains
            valid_names = [name for name in valid_names if name]
            
            for name in valid_names:
                if self._match_hostname(hostname, name):
                    return True
                    
            return False
            
        except Exception:
            return False

    def _match_hostname(self, hostname: str, cert_name: str) -> bool:
        """Check if hostname matches certificate name (including wildcards)"""
        if cert_name == hostname:
            return True
            
        # Handle wildcard certificates
        if cert_name.startswith('*.'):
            domain = cert_name[2:]
            if hostname.endswith('.' + domain):
                return True
                
        return False

# Singleton instance
ssl_checker = SSLChecker() 