import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock, ANY
from main import app
from services.uptime_checker import UptimeCheckResult, uptime_checker
from services.storage_uptime import uptime_storage
from models.monitor import Monitor, AlertConfig
from models.uptime_log import UptimeLog

# Test client setup
client = TestClient(app)

# Mock data
MOCK_URL = "https://www.cursor.com"
MOCK_MONITOR_ID = "test-monitor-123"
MOCK_TIMESTAMP = datetime.now(timezone.utc)

@pytest.fixture
def mock_uptime_storage():
    with patch("services.storage_uptime.uptime_storage") as mock:
        # Mock monitor creation
        mock.create_monitor.return_value = MOCK_MONITOR_ID
        
        # Mock monitor retrieval
        mock_monitor = Monitor(
            id=MOCK_MONITOR_ID,
            url=MOCK_URL,
            name="Cursor Website",
            frequency=5,
            created_at=MOCK_TIMESTAMP,
            last_checked=MOCK_TIMESTAMP,
            last_status="up",
            last_response_time=250,  # Realistic response time
            http_status=200,
            failures_in_a_row=0,
            uptime_stats={"24h": 99.99, "7d": 99.95, "30d": 99.97},  # Realistic uptime stats
            alerts=AlertConfig(
                email="alerts@cursor.com",
                webhook="https://hooks.cursor.com/alerts",
                threshold=2
            ),
            is_public=True
        )
        mock.get_monitor.return_value = mock_monitor
        mock.get_all_monitors.return_value = [mock_monitor]
        mock.get_public_monitors.return_value = [mock_monitor]
        
        # Mock logs with realistic patterns
        mock_logs = [
            UptimeLog(
                timestamp=MOCK_TIMESTAMP - timedelta(minutes=i*5),
                status="up" if i % 20 != 0 else "down",  # Simulate occasional downtime
                response_time=250 + (i % 5) * 10,  # Varying response times
                http_status=200 if i % 20 != 0 else 503  # Occasional server errors
            )
            for i in range(100)  # Last 500 minutes of logs
        ]
        mock.get_logs.return_value = mock_logs
        
        yield mock

@pytest.fixture
def mock_uptime_checker():
    with patch("services.uptime_checker.uptime_checker") as mock:
        async def async_check(*args, **kwargs):
            return UptimeCheckResult(
                status="up",
                response_time=250,  # Realistic response time
                http_status=200,
                error=None,
                timestamp=MOCK_TIMESTAMP
            )
        mock.check = AsyncMock(side_effect=async_check)
        yield mock

# Test real website check
@pytest.mark.asyncio
async def test_real_website_check():
    """Test checking the actual cursor.com website"""
    result = await uptime_checker.check(MOCK_URL)
    
    assert result.status == "up"
    assert 100 <= result.response_time <= 5000  # Response time should be reasonable
    assert result.http_status == 200
    assert result.error is None

# Test monitor creation with real website
@pytest.mark.asyncio
async def test_create_monitor_real_website(mock_uptime_storage, mock_uptime_checker):
    with patch("api.monitor.uptime_storage", mock_uptime_storage), \
         patch("api.monitor.uptime_checker", mock_uptime_checker):
        response = client.post(
            "/api/monitor",
            json={
                "url": MOCK_URL,
                "name": "Cursor Website",
                "frequency": 1,  # Check every minute
                "alerts": {
                    "email": "alerts@cursor.com",
                    "webhook": "https://hooks.cursor.com/alerts",
                    "threshold": 2
                },
                "is_public": True
            }
        )
        
        assert response.status_code == 200
        assert response.json() == MOCK_MONITOR_ID
        mock_uptime_storage.create_monitor.assert_called_once()
        mock_uptime_checker.check.assert_awaited_once()

# Test monitor update with real config
@pytest.mark.asyncio
async def test_update_monitor_real_config(mock_uptime_storage):
    with patch("api.monitor.uptime_storage", mock_uptime_storage):
        response = client.put(
            f"/api/monitor/{MOCK_MONITOR_ID}",
            json={
                "name": "Cursor Production Website",
                "frequency": 5,  # Increase check interval
                "alerts": {
                    "email": "devops@cursor.com",
                    "webhook": "https://hooks.cursor.com/alerts/high-priority",
                    "threshold": 1  # More sensitive alerting
                }
            }
        )
        
        assert response.status_code == 200
        assert response.json() == {"success": True}
        mock_uptime_storage.update_monitor.assert_called_once()

# Test monitor history with realistic timeframes
@pytest.mark.asyncio
async def test_get_monitor_history_timeframes(mock_uptime_storage):
    with patch("api.monitor.uptime_storage", mock_uptime_storage):
        # Test last hour
        response = client.get(f"/api/monitor/{MOCK_MONITOR_ID}/history?hours=1")
        assert response.status_code == 200
        logs = response.json()
        up_logs = [log for log in logs if log["status"] == "up"]
        assert len(up_logs) >= 11  # At least 11/12 checks should be up

        # Test last 24 hours
        response = client.get(f"/api/monitor/{MOCK_MONITOR_ID}/history?hours=24")
        assert response.status_code == 200
        logs = response.json()
        up_logs = [log for log in logs if log["status"] == "up"]
        total_logs = len(logs)
        uptime_percentage = (len(up_logs) / total_logs) * 100 if total_logs > 0 else 0
        assert uptime_percentage >= 95.0  # At least 95% uptime

# Test error scenarios
@pytest.mark.asyncio
async def test_error_scenarios():
    # Test timeout
    with patch("services.uptime_checker.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.side_effect = asyncio.TimeoutError()
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        result = await uptime_checker.check(MOCK_URL)
        assert result.status == "down"
        assert result.error == "Timeout"

    # Test DNS failure
    with patch("services.uptime_checker.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.side_effect = Exception("DNS resolution failed")
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        result = await uptime_checker.check(MOCK_URL)
        assert result.status == "down"
        assert "DNS" in result.error

    # Test SSL error
    with patch("services.uptime_checker.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.side_effect = Exception("SSL certificate verification failed")
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        result = await uptime_checker.check(MOCK_URL)
        assert result.status == "down"
        assert "SSL" in result.error

# Test retry logic
@pytest.mark.asyncio
async def test_retry_logic():
    with patch("services.uptime_checker.httpx.AsyncClient") as mock_client, \
         patch("services.uptime_checker.asyncio.sleep") as mock_sleep:  # Mock sleep to speed up test
        
        mock_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.25
        
        mock_instance.get.side_effect = [
            Exception("Connection failed"),
            Exception("Connection failed"),
            mock_response
        ]
        mock_client.return_value.__aenter__.return_value = mock_instance
        
        result = await uptime_checker.check(MOCK_URL)
        assert result.status == "up"
        assert mock_instance.get.await_count == 3
        assert mock_sleep.await_count == 2  # Should sleep between retries

# Test alert thresholds
@pytest.mark.asyncio
async def test_alert_thresholds():
    monitor = Monitor(
        id=MOCK_MONITOR_ID,
        url=MOCK_URL,
        name="Cursor Website",
        alerts=AlertConfig(
            email="alerts@cursor.com",
            webhook="https://hooks.cursor.com/alerts",
            threshold=2
        ),
        failures_in_a_row=2
    )
    
    # Test alert message formatting
    with patch("services.storage_uptime.print") as mock_print, \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        
        await uptime_storage._send_alert(monitor, "down")
        
        # Verify email alert
        mock_print.assert_called_once_with(
            "📧 Would send email to alerts@cursor.com: 🔴 Cursor Website is DOWN! Failed 2 times in a row."
        )
        
        # Verify webhook alert
        mock_post.assert_awaited_once_with(
            str(monitor.alerts.webhook),
            json={
                "monitor_id": monitor.id,
                "status": "down",
                "message": "🔴 Cursor Website is DOWN! Failed 2 times in a row.",
                "timestamp": ANY
            }
        )

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 