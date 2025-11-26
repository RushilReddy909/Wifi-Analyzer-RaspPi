import subprocess
import time
import sqlite3
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify
import threading

# The path logic correctly points to the central database location
DB_PATH = Path(__file__).parent.parent / "wifi-heatmap-dashboard" / "data" / "wifi_data.db"
location = "Test"   # Default location - changeable via web control panel

# Flask app for room control
control_app = Flask(__name__)

def init_database():
    """Initialize SQLite database with schema and necessary indexes."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Schema must match the fields collected
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wifi_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            room TEXT NOT NULL,
            ssid TEXT NOT NULL,
            bssid TEXT,
            signal INTEGER,
            channel INTEGER,
            frequency TEXT,
            security TEXT,
            vendor TEXT
        )
    """)
    
    # Indexes speed up data retrieval and analysis
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp ON wifi_scans(timestamp)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_room ON wifi_scans(room)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ssid ON wifi_scans(ssid)
    """)
    
    conn.commit()
    conn.close()

def scan_wifi():
    """
    Triggers a fresh WiFi scan and collects metadata using nmcli.
    Robustly handles the split output format.
    """
    
    # 1. Trigger a fresh scan using sudo to handle authorization issues
    # NOTE: This will require a password prompt upon manual run.
    try:
        subprocess.run(
            ["sudo", "nmcli", "dev", "wifi", "rescan"], 
            timeout=5,
            check=True,
            capture_output=True
        )
        # Crucial delay: Give the adapter time to compile new results
        time.sleep(1.5)
    except subprocess.TimeoutExpired:
        print("Warning: WiFi rescan command timed out.")
    except subprocess.CalledProcessError as e:
        # This will catch the password prompt failure if running via systemd without passwordless sudo
        print(f"Error during SUDO rescan command: {e.stderr.decode()}")
    except Exception as e:
        print(f"Error triggering rescan: {e}")

    # 2. Fetch the newly scanned results
    try:
        # Fetch 7 core fields: IN-USE, SSID, BSSID, SIGNAL, CHAN, FREQ, SECURITY
        output = subprocess.check_output(
            ["nmcli", "-t", "-f", "IN-USE,SSID,BSSID,SIGNAL,CHAN,FREQ,SECURITY", "dev", "wifi", "list"],
            timeout=30
        ).decode("utf-8")
    except Exception as e:
        print(f"Error fetching WiFi list: {e}")
        return []

    results = []
    
    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue

        try:
            # We must use the total number of expected parts to parse correctly, 
            # as the BSSID (AA:BB:CC:DD:EE:FF) adds 5 extra colons.
            # Expected parts: 1 (IN-USE) + 1 (SSID) + 6 (BSSID octets) + 1 (SIGNAL) + 1 (CHAN) + 1 (FREQ) + 1 (SECURITY) = 12 total
            parts = line.split(':')
            
            if len(parts) < 12:
                # Malformed line or missing fields
                continue

            # --- Parsing the 12 parts ---
            in_use = parts[0]
            ssid = parts[1] 
            
            # Reconstruct BSSID from the 6 octets (parts[2] through parts[7])
            bssid = ":".join(parts[2:8]) 
            
            signal = parts[8]      # SIGNAL is at index 8 after 1 (IN-USE) + 1 (SSID) + 6 (BSSID)
            channel = parts[9]
            frequency = parts[10]
            security = parts[11]
            
            # --- Cleanup and Validation ---
            if ssid == "--" or ssid.strip() == "":
                continue

            # Signal cleanup and conversion (must be integer)
            cleaned_signal = signal.strip().replace('\\', '')
            try:
                raw_signal = int(cleaned_signal)
            except ValueError:
                # This should no longer trigger due to BSSID fix, but keeps robust
                print(f"Warning: Skipping record due to invalid signal value: {cleaned_signal} for {ssid}")
                continue
                
            # --- Final Data Structure ---
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            vendor = bssid[:8] if bssid and len(bssid) >= 8 else ""

            results.append({
                "timestamp": timestamp,
                "room": location,
                "ssid": ssid,
                "bssid": bssid,
                "signal": raw_signal, 
                "channel": channel.strip() if channel else None,
                "frequency": frequency.strip() if frequency else None,
                "security": security.strip() if security else None,
                "vendor": vendor
            })

        except Exception as e:
            print(f"Error parsing line '{line[:50]}...': {e}")
            continue

    return results

def save_to_database(scan_results):
    """Save scan results to SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for result in scan_results:
        cursor.execute("""
            INSERT INTO wifi_scans (timestamp, room, ssid, bssid, signal, channel, frequency, security, vendor)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result["timestamp"],
            result["room"],
            result["ssid"],
            result["bssid"],
            result["signal"],
            result["channel"],
            result["frequency"],
            result["security"],
            result["vendor"]
        ))
    
    conn.commit()
    conn.close()

@control_app.route("/")
def control_panel():
    """Simple web interface for changing room/location (Scanner Control Panel)"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WiFi Scanner Control</title>
        <style>
            body { font-family: Arial; background: #1a1a1a; color: white; padding: 20px; }
            .container { max-width: 600px; margin: 0 auto; }
            h1 { color: #4a9eff; }
            input, button { padding: 10px; margin: 10px 0; font-size: 16px; }
            input { width: 300px; background: #333; color: white; border: 1px solid #555; }
            button { background: #4a9eff; color: white; border: none; cursor: pointer; padding: 10px 20px; }
            button:hover { background: #357abd; }
            .status { margin-top: 20px; padding: 15px; background: #2a2a2a; border-radius: 5px; }
            .success { color: #4ade80; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📡 WiFi Scanner Control Panel</h1>
            <p>Current Location: <strong id="currentLoc">{{ current_location }}</strong></p>
            <form id="locationForm">
                <input type="text" id="newLocation" placeholder="Enter new room/location name" required>
                <button type="submit">Update Location</button>
            </form>
            <div class="status" id="status"></div>
            <p style="margin-top: 30px; font-size: 0.9em; color: #aaa;">
                Access the main dashboard at: 
                <a href="http://{{ request.host.split(':')[0] }}:5000" style="color: #4ade80;">http://{{ request.host.split(':')[0] }}:5000</a>
            </p>
        </div>
        <script>
            document.getElementById('locationForm').onsubmit = async (e) => {
                e.preventDefault();
                const newLoc = document.getElementById('newLocation').value;
                const response = await fetch('/set_location', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({location: newLoc})
                });
                const data = await response.json();
                if (data.success) {
                    document.getElementById('currentLoc').textContent = newLoc;
                    document.getElementById('status').innerHTML = '<span class="success">✓ Location updated successfully!</span>';
                    document.getElementById('newLocation').value = '';
                } else {
                    document.getElementById('status').innerHTML = '<span style="color:#ef4444">✗ Error updating location</span>';
                }
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(html, current_location=location)

@control_app.route("/set_location", methods=["POST"])
def set_location():
    """API endpoint to change scanning location"""
    global location
    data = request.get_json()
    new_location = data.get("location", "").strip()
    
    if new_location:
        location = new_location
        return jsonify({"success": True, "location": location})
    
    return jsonify({"success": False, "error": "Invalid location"}), 400

def run_control_server():
    """Run Flask control server in background thread"""
    control_app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)


if __name__ == "__main__":
    # Initialize database
    init_database()
    print("Database initialized")
    
    # Start control server in background thread
    control_thread = threading.Thread(target=run_control_server, daemon=True)
    control_thread.start()
    print("Control panel started on http://0.0.0.0:5001")
    
    # Main scanning loop
    while True:
        networks = scan_wifi()
        
        if networks:
            # Save to database
            save_to_database(networks)
            
            print(f"Scan complete at {location}: {len(networks)} networks saved to database")
            # Print first few networks for debugging
            for net in networks[:3]:
                # Signal is raw (0-100) and convert to dBm for display
                try:
                    signal_dbm = int(net['signal']) / 2.0 - 100.0
                except ValueError:
                    signal_dbm = "N/A"
                    
                print(f"  - {net['ssid']}: {signal_dbm:.2f} dBm, Channel {net['channel']}")
        else:
            print(f"Warning: No networks found in scan at {location}. Retrying...")
        
        time.sleep(5)