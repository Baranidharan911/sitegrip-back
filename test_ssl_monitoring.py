import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from services.ssl_checker import ssl_checker
from services.uptime_checker import uptime_checker
from services.storage_uptime import uptime_storage
from models.ssl_info import SSLInfo, SSLAlert
from models.monitor import Monitor, AlertConfig

# Test client setup
client = TestClient(app)

# Test URLs
HTTPS_URL = "https://www.google.com"
HTTP_URL = "http://www.example.com"
INVALID_SSL_URL = "https://self-signed.badssl.com"
EXPIRED_SSL_URL = "https://expired.badssl.com"

@pytest.fixture
def mock_ssl_info_valid():
    """Mock valid SSL certificate info"""
    return SSLInfo(
        is_valid=True,
        expires_at=datetime.now(timezone.utc) + timedelta(days=90),
        issued_at=datetime.now(timezone.utc) - timedelta(days=30),
        days_until_expiry=90,
        issuer="Google Trust Services",
        subject="*.google.com",
        serial_number="123456789",
        signature_algorithm="sha256WithRSAEncryption",
        version=3,
        san_domains=["*.google.com", "google.com"],
        is_self_signed=False,
        is_expired=False,
        is_expiring_soon=False,
        chain_valid=True,
        error_message=None
    )

@pytest.fixture
def mock_ssl_info_expiring():
    """Mock SSL certificate info that's expiring soon"""
    return SSLInfo(
        is_valid=True,
        expires_at=datetime.now(timezone.utc) + timedelta(days=15),
        issued_at=datetime.now(timezone.utc) - timedelta(days=75),
        days_until_expiry=15,
        issuer="Let's Encrypt",
        subject="example.com",
        serial_number="987654321",
        signature_algorithm="sha256WithRSAEncryption",
        version=3,
        san_domains=["example.com", "www.example.com"],
        is_self_signed=False,
        is_expired=False,
        is_expiring_soon=True,
        chain_valid=True,
        error_message="Certificate expires in 15 days"
    )

@pytest.fixture
def mock_ssl_info_expired():
    """Mock expired SSL certificate info"""
    return SSLInfo(
        is_valid=False,
        expires_at=datetime.now(timezone.utc) - timedelta(days=5),
        issued_at=datetime.now(timezone.utc) - timedelta(days=95),
        days_until_expiry=-5,
        issuer="BadSSL",
        subject="expired.badssl.com",
        serial_number="111111111",
        signature_algorithm="sha256WithRSAEncryption",
        version=3,
        san_domains=["expired.badssl.com"],
        is_self_signed=False,
        is_expired=True,
        is_expiring_soon=False,
        chain_valid=False,
        error_message="Certificate expired"
    )

# Test SSL certificate checking
@pytest.mark.asyncio
async def test_ssl_checker_valid_certificate(mock_ssl_info_valid):
    """Test SSL checker with valid certificate"""
    with patch.object(ssl_checker, '_get_certificate_info', return_value=mock_ssl_info_valid):
        result = await ssl_checker.check_ssl_certificate(HTTPS_URL)
        
        assert result is not None
        assert result.is_valid == True
        assert result.days_until_expiry == 90
        assert result.issuer == "Google Trust Services"
        assert not result.is_expired
        assert not result.is_expiring_soon

@pytest.mark.asyncio
async def test_ssl_checker_http_url():
    """Test SSL checker with HTTP URL (should return None)"""
    result = await ssl_checker.check_ssl_certificate(HTTP_URL)
    assert result is None

@pytest.mark.asyncio
async def test_ssl_checker_expired_certificate(mock_ssl_info_expired):
    """Test SSL checker with expired certificate"""
    with patch.object(ssl_checker, '_get_certificate_info', return_value=mock_ssl_info_expired):
        result = await ssl_checker.check_ssl_certificate(EXPIRED_SSL_URL)
        
        assert result is not None
        assert result.is_valid == False
        assert result.is_expired == True
        assert result.days_until_expiry == -5
        assert "expired" in result.error_message.lower()

@pytest.mark.asyncio
async def test_uptime_checker_with_ssl(mock_ssl_info_valid):
    """Test uptime checker with SSL monitoring enabled"""
    with patch.object(ssl_checker, 'check_ssl_certificate', return_value=mock_ssl_info_valid), \
         patch('httpx.AsyncClient') as mock_client:
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.25
        
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        result = await uptime_checker.check(HTTPS_URL, ssl_monitoring_enabled=True)
        
        assert result.status == "up"
        assert result.ssl_info is not None
        assert result.ssl_info.is_valid == True
        assert result.ssl_info.days_until_expiry == 90

@pytest.mark.asyncio
async def test_uptime_checker_ssl_expired(mock_ssl_info_expired):
    """Test uptime checker with expired SSL certificate"""
    with patch.object(ssl_checker, 'check_ssl_certificate', return_value=mock_ssl_info_expired):
        result = await uptime_checker.check(HTTPS_URL, ssl_monitoring_enabled=True)
        
        assert result.status == "down"
        assert result.ssl_info is not None
        assert result.ssl_info.is_expired == True
        assert "SSL Error" in result.error

@pytest.mark.asyncio
async def test_uptime_checker_ssl_expiring_soon(mock_ssl_info_expiring):
    """Test uptime checker with SSL certificate expiring soon"""
    with patch.object(ssl_checker, 'check_ssl_certificate', return_value=mock_ssl_info_expiring), \
         patch('httpx.AsyncClient') as mock_client:
        
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.25
        
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        result = await uptime_checker.check(HTTPS_URL, ssl_monitoring_enabled=True)
        
        assert result.status == "up"  # Still up, but with warning
        assert result.ssl_info is not None
        assert result.ssl_info.is_expiring_soon == True
        assert "expires in 15 days" in result.error

# Test SSL alert configuration
def test_ssl_alert_creation():
    """Test SSL alert configuration"""
    ssl_alert = SSLAlert(
        days_before_expiry=14,
        check_chain=True,
        alert_on_self_signed=True,
        alert_on_invalid=True
    )
    
    assert ssl_alert.days_before_expiry == 14
    assert ssl_alert.check_chain == True
    assert ssl_alert.alert_on_self_signed == True
    assert ssl_alert.alert_on_invalid == True

# Test monitor creation with SSL monitoring
def test_create_monitor_with_ssl():
    """Test creating monitor with SSL monitoring configuration"""
    with patch("services.storage_uptime.uptime_storage") as mock_storage, \
         patch("services.uptime_checker.uptime_checker") as mock_checker:
        
        mock_storage.create_monitor.return_value = "test-monitor-123"
        
        async def mock_check(*args, **kwargs):
            from services.uptime_checker import UptimeCheckResult
            return UptimeCheckResult("up", 250, 200, None, datetime.now(timezone.utc))
        
        mock_checker.check = AsyncMock(side_effect=mock_check)
        
        response = client.post(
            "/api/monitor",
            json={
                "url": HTTPS_URL,
                "name": "Google SSL Test",
                "frequency": 5,
                "ssl_monitoring_enabled": True,
                "alerts": {
                    "email": "admin@example.com",
                    "webhook": "https://hooks.example.com/ssl-alerts",
                    "threshold": 2,
                    "ssl_alerts": {
                        "days_before_expiry": 30,
                        "check_chain": True,
                        "alert_on_self_signed": True,
                        "alert_on_invalid": True
                    }
                }
            }
        )
        
        assert response.status_code == 200
        mock_storage.create_monitor.assert_called_once()

# Test SSL endpoint
def test_get_ssl_info_endpoint():
    """Test SSL information endpoint"""
    with patch("services.storage_uptime.uptime_storage") as mock_storage:
        # Mock monitor
        monitor = Monitor(
            id="test-123",
            url=HTTPS_URL,
            name="Test Monitor",
            ssl_monitoring_enabled=True,
            ssl_status="valid",
            ssl_cert_expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            ssl_cert_days_until_expiry=90,
            ssl_cert_issuer="Google Trust Services"
        )
        mock_storage.get_monitor.return_value = monitor
        
        # Mock logs with SSL info
        from models.uptime_log import UptimeLog
        ssl_log = UptimeLog(
            timestamp=datetime.now(timezone.utc),
            status="up",
            response_time=250,
            http_status=200,
            ssl_info=SSLInfo(
                is_valid=True,
                expires_at=datetime.now(timezone.utc) + timedelta(days=90),
                days_until_expiry=90,
                issuer="Google Trust Services"
            )
        )
        mock_storage.get_logs.return_value = [ssl_log]
        
        response = client.get("/api/monitor/test-123/ssl")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ssl_monitoring_enabled"] == True
        assert data["ssl_info"] is not None
        assert data["ssl_info"]["is_valid"] == True
        assert data["ssl_cert_days_until_expiry"] == 90

# Test SSL hostname validation
def test_ssl_hostname_validation():
    """Test SSL hostname validation logic"""
    # Test exact match
    assert ssl_checker._match_hostname("example.com", "example.com") == True
    
    # Test wildcard match
    assert ssl_checker._match_hostname("sub.example.com", "*.example.com") == True
    assert ssl_checker._match_hostname("example.com", "*.example.com") == False
    
    # Test no match
    assert ssl_checker._match_hostname("example.com", "other.com") == False

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 