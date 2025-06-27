import httpx
import asyncio
from datetime import datetime, timezone
from typing import Optional

class UptimeCheckResult:
    def __init__(self, status: str, response_time: Optional[int], http_status: Optional[int], error: Optional[str], timestamp: datetime):
        self.status = status  # "up" or "down"
        self.response_time = response_time  # in milliseconds
        self.http_status = http_status  # HTTP status code
        self.error = error  # timeout, connection error, 5xx, etc.
        self.timestamp = timestamp

class UptimeChecker:
    def __init__(self, timeout: int = 10, max_retries: int = 3, retry_delay: int = 15):
        self.timeout = timeout  # seconds
        self.max_retries = max_retries
        self.retry_delay = retry_delay  # seconds

    async def check(self, url: str) -> UptimeCheckResult:
        start = datetime.now(timezone.utc)
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, follow_redirects=True)
                    elapsed_ms = int(response.elapsed.total_seconds() * 1000)
                    
                    if response.status_code < 400:
                        return UptimeCheckResult("up", elapsed_ms, response.status_code, None, start)
                    else:
                        last_error = f"{response.status_code} {response.reason_phrase}"
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(self.retry_delay)
                            continue
                        return UptimeCheckResult("down", elapsed_ms, response.status_code, last_error, start)
                        
            except httpx.TimeoutException:
                last_error = "Timeout"
            except httpx.RequestError as e:
                last_error = str(e)
            except Exception as e:
                last_error = str(e)
            
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay)
                continue
            
            return UptimeCheckResult("down", None, None, last_error, start)

# Singleton instance
uptime_checker = UptimeChecker()
