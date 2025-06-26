from typing import Optional, List
from datetime import datetime, timedelta
from db.firestore import get_firestore_client
from models.monitor import Monitor
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

    def create_monitor(self, url: str, frequency: int = 5) -> str:
        doc_ref = self.monitors.document()
        monitor = Monitor(
            id=doc_ref.id,
            url=url,
            frequency=frequency,
            created_at=datetime.utcnow(),
        )
        doc_ref.set(monitor.dict())
        return doc_ref.id

    def delete_monitor(self, monitor_id: str):
        self.monitors.document(monitor_id).delete()

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

    def update_monitor_status(self, monitor_id: str, status: str, response_time: Optional[int], timestamp: datetime):
        self.monitors.document(monitor_id).update({
            "lastChecked": timestamp,
            "lastStatus": status,
            "lastResponseTime": response_time,
        })

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

# Instantiate for import
uptime_storage = UptimeStorageService()
