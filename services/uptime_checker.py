import httpx
from datetime import datetime
from typing import Optional

class UptimeCheckResult:
    def __init__(self, status: str, response_time: Optional[int], error: Optional[str], timestamp: datetime):
        self.status = status  # "up" or "down"
        self.response_time = response_time  # in milliseconds
        self.error = error  # timeout, connection error, 5xx, etc.
        self.timestamp = timestamp

class UptimeChecker:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout  # seconds

    async def check(self, url: str) -> UptimeCheckResult:
        start = datetime.utcnow()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, follow_redirects=True)
                elapsed_ms = int(response.elapsed.total_seconds() * 1000)
                if response.status_code < 400:
                    return UptimeCheckResult("up", elapsed_ms, None, start)
                else:
                    return UptimeCheckResult("down", elapsed_ms, f"{response.status_code} {response.reason_phrase}", start)
        except httpx.TimeoutException:
            return UptimeCheckResult("down", None, "Timeout", start)
        except httpx.RequestError as e:
            return UptimeCheckResult("down", None, str(e), start)

# Singleton instance
uptime_checker = UptimeChecker()
