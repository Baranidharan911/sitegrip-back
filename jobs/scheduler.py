import asyncio
from services.uptime_checker import uptime_checker
from services.storage_uptime import uptime_storage
from models.uptime_log import UptimeLog
import time

CHECK_INTERVAL_SECONDS = 300  # 5 minutes

class UptimeScheduler:
    def __init__(self):
        self._running = False

    async def start(self):
        self._running = True
        print("🔄 Uptime scheduler started.")
        while self._running:
            await self._run_once()
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)

    async def _run_once(self):
        print("📡 Running uptime check for all monitors...")
        monitors = uptime_storage.get_all_monitors()
        for monitor in monitors:
            try:
                result = await uptime_checker.check(monitor.url)

                # Save log
                log = UptimeLog(
                    timestamp=result.timestamp,
                    status=result.status,
                    response_time=result.response_time,
                    error=result.error,
                )
                uptime_storage.save_log(monitor.id, log)

                # Update monitor status
                uptime_storage.update_monitor_status(
                    monitor.id,
                    result.status,
                    result.response_time,
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
                }
                uptime_storage.monitors.document(monitor.id).update({
                    "uptimeStats": stats
                })

                print(f"✅ Checked {monitor.url}: {result.status.upper()} ({result.response_time} ms)")

            except Exception as e:
                print(f"❌ Error checking {monitor.url}: {e}")

    def stop(self):
        self._running = False
        print("⛔ Uptime scheduler stopped.")

# Singleton instance to import
uptime_scheduler = UptimeScheduler()
