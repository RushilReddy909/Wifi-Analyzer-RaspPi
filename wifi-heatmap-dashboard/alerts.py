"""
Alert System for WiFi Analyzer
Monitors network conditions and sends notifications for signal degradation
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import json

DB_PATH = Path(__file__).parent / "data" / "wifi_data.db"
ALERTS_FILE = Path(__file__).parent / "data" / "alerts.json"

# Alert thresholds
SIGNAL_DEGRADATION_THRESHOLD = -10  # dBm drop to trigger alert
POOR_SIGNAL_THRESHOLD = -80  # dBm absolute threshold
NETWORK_DISAPPEARANCE_MINUTES = 30  # Minutes without seeing a network

class AlertSystem:
    def __init__(self):
        self.alerts = self.load_alerts()
    
    def load_alerts(self):
        """Load previous alerts from file"""
        if ALERTS_FILE.exists():
            with open(ALERTS_FILE, 'r') as f:
                return json.load(f)
        return []
    
    def save_alerts(self):
        """Save alerts to file"""
        ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(ALERTS_FILE, 'w') as f:
            json.dump(self.alerts, f, indent=2)
    
    def add_alert(self, alert_type, message, severity="warning", data=None):
        """Add a new alert"""
        alert = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": alert_type,
            "message": message,
            "severity": severity,
            "data": data or {}
        }
        self.alerts.append(alert)
        self.save_alerts()
        return alert
    
    def check_signal_degradation(self, room, ssid):
        """Check if signal has degraded significantly"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get recent signals (last hour vs previous hour)
        cutoff_recent = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        cutoff_previous = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            SELECT AVG(signal) as avg_signal
            FROM wifi_scans
            WHERE room = ? AND ssid = ? AND timestamp >= ?
        """, (room, ssid, cutoff_recent))
        recent_avg = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT AVG(signal) as avg_signal
            FROM wifi_scans
            WHERE room = ? AND ssid = ? AND timestamp >= ? AND timestamp < ?
        """, (room, ssid, cutoff_previous, cutoff_recent))
        previous_avg = cursor.fetchone()[0]
        
        conn.close()
        
        if recent_avg and previous_avg:
            recent_dbm = recent_avg / 2.0 - 100.0
            previous_dbm = previous_avg / 2.0 - 100.0
            degradation = recent_dbm - previous_dbm
            
            if degradation < SIGNAL_DEGRADATION_THRESHOLD:
                return self.add_alert(
                    "signal_degradation",
                    f"Signal degradation detected for {ssid} in {room}",
                    severity="warning",
                    data={
                        "room": room,
                        "ssid": ssid,
                        "previous_signal": round(previous_dbm, 1),
                        "current_signal": round(recent_dbm, 1),
                        "degradation": round(degradation, 1)
                    }
                )
        
        return None
    
    def check_poor_signal(self):
        """Check for networks with consistently poor signal"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            SELECT room, ssid, AVG(signal) as avg_signal
            FROM wifi_scans
            WHERE timestamp >= ?
            GROUP BY room, ssid
            HAVING avg_signal > 0
        """, (cutoff,))
        
        alerts = []
        for row in cursor.fetchall():
            room, ssid, avg_signal = row
            signal_dbm = avg_signal / 2.0 - 100.0
            
            if signal_dbm < POOR_SIGNAL_THRESHOLD:
                alert = self.add_alert(
                    "poor_signal",
                    f"Poor signal detected for {ssid} in {room}",
                    severity="info",
                    data={
                        "room": room,
                        "ssid": ssid,
                        "signal": round(signal_dbm, 1)
                    }
                )
                alerts.append(alert)
        
        conn.close()
        return alerts
    
    def check_network_disappearance(self):
        """Check for networks that have disappeared"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cutoff_recent = (datetime.now() - timedelta(minutes=NETWORK_DISAPPEARANCE_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
        cutoff_old = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        
        # Find networks seen in the past but not recently
        cursor.execute("""
            SELECT DISTINCT room, ssid
            FROM wifi_scans
            WHERE timestamp >= ? AND timestamp < ?
            AND (room, ssid) NOT IN (
                SELECT DISTINCT room, ssid
                FROM wifi_scans
                WHERE timestamp >= ?
            )
        """, (cutoff_old, cutoff_recent, cutoff_recent))
        
        alerts = []
        for row in cursor.fetchall():
            room, ssid = row
            alert = self.add_alert(
                "network_disappeared",
                f"Network {ssid} not seen in {room} for {NETWORK_DISAPPEARANCE_MINUTES} minutes",
                severity="warning",
                data={
                    "room": room,
                    "ssid": ssid,
                    "minutes_missing": NETWORK_DISAPPEARANCE_MINUTES
                }
            )
            alerts.append(alert)
        
        conn.close()
        return alerts
    
    def check_all(self):
        """Run all alert checks"""
        alerts = []
        
        # Check for poor signals
        alerts.extend(self.check_poor_signal())
        
        # Check for network disappearances
        alerts.extend(self.check_network_disappearance())
        
        return alerts
    
    def get_recent_alerts(self, hours=24):
        """Get alerts from last N hours"""
        cutoff = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        return [alert for alert in self.alerts if alert["timestamp"] >= cutoff]
    
    def clear_old_alerts(self, days=7):
        """Remove alerts older than N days"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        self.alerts = [alert for alert in self.alerts if alert["timestamp"] >= cutoff]
        self.save_alerts()


def run_alert_checks():
    """Convenience function to run all checks"""
    alert_system = AlertSystem()
    new_alerts = alert_system.check_all()
    
    if new_alerts:
        print(f"Generated {len(new_alerts)} new alerts:")
        for alert in new_alerts:
            print(f"  [{alert['severity'].upper()}] {alert['message']}")
    else:
        print("No new alerts generated")
    
    return new_alerts


if __name__ == "__main__":
    # Run alert checks when executed directly
    run_alert_checks()
