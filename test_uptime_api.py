import requests
import json
from datetime import datetime

API_BASE = "http://127.0.0.1:8000/api"
TEST_URL = "https://www.elbrit.org"

def pretty_log(log):
    ts = datetime.fromisoformat(log['timestamp'])
    print(f"  - {ts.strftime('%Y-%m-%d %H:%M:%S')} → Status: {'🟢 UP' if log['status'] == 'up' else '🔴 DOWN'}"
          f" | Response: {log.get('response_time', '—')}ms"
          f"{' | Error: ' + log['error'] if log.get('error') else ''}")

def run_test():
    print("🚀 Uptime API Live Test")

    # 1. Add monitor
    print("\n📡 Adding monitor...")
    res = requests.post(f"{API_BASE}/monitor", json={"url": TEST_URL, "frequency": 5})
    if res.status_code != 200:
        print("❌ Add failed:", res.text)
        return
    monitor_id = res.json()
    print("✅ Monitor added → ID:", monitor_id)

    # 2. Check current status
    print("\n📊 Monitor Status:")
    res = requests.get(f"{API_BASE}/monitor/status")
    data = res.json()
    for mon in data:
        status = mon.get('lastStatus')
        checked = mon.get('lastChecked', '—')
        response = mon.get('lastResponseTime', '—')
        print(f"- {mon['url']} → Last Status: {'🟢 UP' if status == 'up' else ('🔴 DOWN' if status == 'down' else '⏳ PENDING')}"
            f" | Last Response: {response}ms"
            f" | Last Checked: {checked}")


    # 3. Get recent logs
    print("\n📜 Uptime Logs:")
    res = requests.get(f"{API_BASE}/monitor/{monitor_id}/history")
    if res.status_code == 200:
        logs = res.json()
        for log in logs[-5:]:
            pretty_log(log)
    else:
        print("❌ Logs fetch failed:", res.text)

    # 4. Cleanup
    print("\n🗑️ Cleaning up...")
    res = requests.delete(f"{API_BASE}/monitor/{monitor_id}")
    if res.status_code == 200:
        print("✅ Monitor deleted.")
    else:
        print("❌ Deletion failed:", res.text)

if __name__ == "__main__":
    run_test()
