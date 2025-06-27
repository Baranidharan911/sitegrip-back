from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class SSLInfo(BaseModel):
    """SSL Certificate information model"""
    is_valid: bool = True
    expires_at: Optional[datetime] = None
    issued_at: Optional[datetime] = None
    days_until_expiry: Optional[int] = None
    issuer: Optional[str] = None
    subject: Optional[str] = None
    serial_number: Optional[str] = None
    signature_algorithm: Optional[str] = None
    version: Optional[int] = None
    san_domains: Optional[List[str]] = None  # Subject Alternative Names
    is_self_signed: bool = False
    is_expired: bool = False
    is_expiring_soon: bool = False  # Within 30 days
    chain_valid: bool = True
    error_message: Optional[str] = None

class SSLAlert(BaseModel):
    """SSL-specific alert configuration"""
    days_before_expiry: int = 30  # Alert when cert expires within X days
    check_chain: bool = True      # Validate full certificate chain
    alert_on_self_signed: bool = True  # Alert if certificate is self-signed
    alert_on_invalid: bool = True      # Alert if certificate is invalid 