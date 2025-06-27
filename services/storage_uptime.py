from typing import Optional, List, Dict
from datetime import datetime, timedelta
import httpx
from db.firestore import get_firestore_client
from models.monitor import Monitor, AlertConfig
from models.uptime_log import UptimeLog
from models.incident import Incident
from pydantic import ValidationError

db = get_firestore_client()

MONITOR_COLLECTION = "monitors"
INCIDENT_COLLECTION = "incidents"

class UptimeStorageService:
    def __init__(self):
        self.monitors = db.collection(MONITOR_COLLECTION)

    # --- MONITOR CRUD ---

    def create_monitor(
        self, 
        url: str, 
        name: Optional[str] = None,
        frequency: int = 5,
        alerts: Optional[AlertConfig] = None,
        is_public: bool = False
    ) -> str:
        doc_ref = self.monitors.document()
        monitor = Monitor(
            id=doc_ref.id,
            url=url,
            name=name or url,
            frequency=frequency,
            alerts=alerts,
            is_public=is_public,
            created_at=datetime.utcnow(),
        )
        doc_ref.set(monitor.dict())
        return doc_ref.id

    def update_monitor(self, monitor_id: str, **updates) -> None:
        self.monitors.document(monitor_id).update(updates)

    def delete_monitor(self, monitor_id: str):
        self.monitors.document(monitor_id).delete()

    def get_monitor(self, monitor_id: str) -> Optional[Monitor]:
        doc = self.monitors.document(monitor_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        data["id"] = doc.id
        return Monitor(**data)

    def get_all_monitors(self) -> List[Monitor]:
        query = self.monitors.stream()
        monitors = []
        for doc in query:
            data = doc.to_dict()
            data["id"] = doc.id
            try:
                monitors.append(Monitor(**data))
            except ValidationError:
                continue
        return monitors

    def get_public_monitors(self) -> List[Monitor]:
        query = self.monitors.where("is_public", "==", True).stream()
        monitors = []
        for doc in query:
            data = doc.to_dict()
            data["id"] = doc.id
            try:
                monitors.append(Monitor(**data))
            except ValidationError:
                continue
        return monitors

    # --- LOGGING ---

    def save_log(self, monitor_id: str, log: UptimeLog):
        log_ref = self.monitors.document(monitor_id).collection("logs").document(log.timestamp.isoformat())
        log_ref.set(log.dict())

    def get_logs(self, monitor_id: str, since_minutes: int = 1440) -> List[UptimeLog]:
        since = datetime.utcnow() - timedelta(minutes=since_minutes)
        logs_ref = self.monitors.document(monitor_id).collection("logs")
        query = logs_ref.where("timestamp", ">=", since).order_by("timestamp")
        return [UptimeLog(**doc.to_dict()) for doc in query.stream()]

    # --- STATUS UPDATES ---

    def update_monitor_status(
        self, 
        monitor_id: str, 
        status: str, 
        response_time: Optional[int], 
        http_status: Optional[int],
        timestamp: datetime
    ):
        monitor = self.get_monitor(monitor_id)
        if not monitor:
            return

        updates = {
            "last_checked": timestamp,
            "last_status": status,
            "last_response_time": response_time,
            "http_status": http_status,
        }

        # Update failures counter
        if status == "down":
            updates["failures_in_a_row"] = monitor.failures_in_a_row + 1
            
            # Check if we need to send alerts
            if monitor.alerts and monitor.failures_in_a_row + 1 >= monitor.alerts.threshold:
                self._send_alert(monitor, "down")
        else:  # status == "up"
            if monitor.failures_in_a_row > 0:  # Site recovered
                self._send_alert(monitor, "up")
            updates["failures_in_a_row"] = 0

        self.monitors.document(monitor_id).update(updates)

    # --- INCIDENT TRACKING ---

    def start_incident(self, monitor_id: str, reason: str, timestamp: datetime):
        doc_ref = db.collection(INCIDENT_COLLECTION).document()
        incident = Incident(
            monitor_id=monitor_id,
            started_at=timestamp,
            reason=reason,
        )
        doc_ref.set(incident.dict())

    def end_incident(self, monitor_id: str, recovery_time: datetime):
        query = db.collection(INCIDENT_COLLECTION) \
            .where("monitor_id", "==", monitor_id) \
            .where("ended_at", "==", None) \
            .order_by("started_at", direction="DESCENDING") \
            .limit(1)

        docs = list(query.stream())
        if not docs:
            return

        doc = docs[0]
        data = doc.to_dict()
        duration = int((recovery_time - data["started_at"]).total_seconds() / 60)

        doc.reference.update({
            "ended_at": recovery_time,
            "duration_minutes": duration
        })

    # --- ADVANCED: Calculate Real Uptime % ---

    def calculate_uptime_percentage(self, monitor_id: str, minutes: int = 1440) -> float:
        logs = self.get_logs(monitor_id, since_minutes=minutes)
        if not logs:
            return 100.0
        total = len(logs)
        up_count = sum(1 for log in logs if log.status == "up")
        return round((up_count / total) * 100, 2)

    # --- ALERTS ---

    async def _send_alert(self, monitor: Monitor, status: str):
        if not monitor.alerts:
            return

        message = self._build_alert_message(monitor, status)

        # Send email alert
        if monitor.alerts.email:
            # TODO: Implement email sending
            print(f"📧 Would send email to {monitor.alerts.email}: {message}")

        # Send webhook alert
        if monitor.alerts.webhook:
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        str(monitor.alerts.webhook),
                        json={
                            "monitor_id": monitor.id,
                            "status": status,
                            "message": message,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    )
            except Exception as e:
                print(f"Failed to send webhook alert: {e}")

    def _build_alert_message(self, monitor: Monitor, status: str) -> str:
        site_name = monitor.name or monitor.url
        if status == "down":
            return f"🔴 {site_name} is DOWN! Failed {monitor.failures_in_a_row} times in a row."
        else:  # status == "up"
            return f"✅ {site_name} is back UP after {monitor.failures_in_a_row} failures."

# Instantiate for import
uptime_storage = UptimeStorageService()
