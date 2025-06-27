import asyncio
from datetime import datetime, timedelta
from services.uptime_checker import uptime_checker
from services.storage_uptime import uptime_storage
from models.uptime_log import UptimeLog

MIN_CHECK_INTERVAL = 60  # 1 minute in seconds

class UptimeScheduler:
    def __init__(self):
        self._running = False
        self._last_checks = {}  # monitor_id -> last check time

    async def start(self):
        self._running = True
        print("🔄 Uptime scheduler started.")
        while self._running:
            await self._run_once()
            await asyncio.sleep(MIN_CHECK_INTERVAL)

    async def _run_once(self):
        now = datetime.utcnow()
        monitors = uptime_storage.get_all_monitors()
        
        for monitor in monitors:
            try:
                # Check if it's time to check this monitor
                last_check = self._last_checks.get(monitor.id)
                if last_check:
                    next_check = last_check + timedelta(minutes=monitor.frequency)
                    if now < next_check:
                        continue

                # Perform the check
                result = await uptime_checker.check(str(monitor.url))

                # Save log
                log = UptimeLog(
                    timestamp=result.timestamp,
                    status=result.status,
                    response_time=result.response_time,
                    http_status=result.http_status,
                    error=result.error,
                )
                uptime_storage.save_log(monitor.id, log)

                # Update monitor status
                uptime_storage.update_monitor_status(
                    monitor.id,
                    result.status,
                    result.response_time,
                    result.http_status,
                    result.timestamp,
                )

                # Incident logic
                if result.status == "down":
                    uptime_storage.start_incident(
                        monitor.id,
                        result.error or "Unknown",
                        result.timestamp
                    )
                else:  # result.status == "up"
                    uptime_storage.end_incident(
                        monitor.id,
                        result.timestamp
                    )

                # Update uptime %
                stats = {
                    "24h": uptime_storage.calculate_uptime_percentage(monitor.id, 1440),
                    "7d": uptime_storage.calculate_uptime_percentage(monitor.id, 10080),
                    "30d": uptime_storage.calculate_uptime_percentage(monitor.id, 43200),
                }
                uptime_storage.update_monitor(monitor.id, uptime_stats=stats)

                # Update last check time
                self._last_checks[monitor.id] = now

                print(f"✅ Checked {monitor.url}: {result.status.upper()} ({result.response_time} ms)")

            except Exception as e:
                print(f"❌ Error checking {monitor.url}: {e}")

    def stop(self):
        self._running = False
        print("⛔ Uptime scheduler stopped.")

# Singleton instance to import
uptime_scheduler = UptimeScheduler()
