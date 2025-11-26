# WiFi Analyzer - Quick Reference Guide

## 🚀 Quick Start

### 1. Installation

```bash
cd "Wifi Heatmap"
bash setup.sh
```

### 2. Start Services

```bash
# Terminal 1 - Scanner
cd wifi-collector
python3 scanner.py

# Terminal 2 - Dashboard
cd wifi-heatmap-dashboard
python3 app.py
```

### 3. Access URLs

- **Scanner Control**: http://pi.local:5001
- **Main Dashboard**: http://pi.local:5000
- **Interactive View**: http://pi.local:5000/interactive
- **Alerts Page**: http://pi.local:5000/alerts

---

## 📱 Common Tasks

### Change Room/Location

1. Visit http://pi.local:5001
2. Enter new room name
3. Click "Update Location"
4. Scanner immediately uses new location (no restart needed)

### View Real-Time Updates

1. Visit http://pi.local:5000/interactive
2. Watch "Live Updates" counter
3. See latest scans appear automatically
4. Charts auto-refresh every 5 minutes

### Check Alerts

1. Visit http://pi.local:5000/alerts
2. Click "Check for New Alerts" button
3. Review warnings by severity
4. Check alert details in data sections

### Get Channel Recommendations

1. Visit main dashboard or interactive view
2. Scroll to "2.4GHz Channel Analysis" section
3. Note recommended channel (1, 6, or 11)
4. See which channels have most/least congestion

---

## 🗄️ Database Management

### View Statistics

```bash
cd wifi-heatmap-dashboard
python3 db_maintenance.py stats
```

### Export Data

```bash
# Export last 7 days
python3 db_maintenance.py export backup.csv --days 7

# Export all data
python3 db_maintenance.py export full_backup.csv
```

### Clean Old Data

```bash
# Delete data older than 30 days
python3 db_maintenance.py cleanup --days 30
```

### Optimize Database

```bash
# Reclaim disk space
python3 db_maintenance.py vacuum
```

### Aggregate Old Data

```bash
# Convert data older than 7 days to hourly averages
python3 db_maintenance.py aggregate --days 7
```

---

## 🔧 API Usage

### Get Statistics

```bash
curl http://pi.local:5000/api/stats | jq
```

### Get Latest Scans

```bash
curl http://pi.local:5000/api/latest | jq
```

### Get Alerts

```bash
curl http://pi.local:5000/api/alerts | jq
```

### Trigger Alert Check

```bash
curl -X POST http://pi.local:5000/api/alerts/check | jq
```

### Get Channel Recommendations

```bash
curl http://pi.local:5000/api/channel_recommendations | jq
```

---

## 🤖 Auto-Start on Boot

### Install Services

```bash
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable wifi-scanner.service
sudo systemctl enable wifi-dashboard.service
sudo systemctl start wifi-scanner.service
sudo systemctl start wifi-dashboard.service
```

### Check Status

```bash
sudo systemctl status wifi-scanner.service
sudo systemctl status wifi-dashboard.service
```

### View Logs

```bash
sudo journalctl -u wifi-scanner.service -f
sudo journalctl -u wifi-dashboard.service -f
```

---

## 🐛 Troubleshooting

### Scanner Not Collecting Data

```bash
# Test nmcli manually
nmcli dev wifi list

# Check if database exists
ls -lh wifi-heatmap-dashboard/data/wifi_data.db

# View scanner logs
sudo journalctl -u wifi-scanner.service -n 50
```

### Dashboard Shows No Data

```bash
# Check database has records
sqlite3 wifi-heatmap-dashboard/data/wifi_data.db "SELECT COUNT(*) FROM wifi_scans"

# Test analyzer directly
cd wifi-heatmap-dashboard
python3 -c "from analyzer import load_all_data; print(len(load_all_data()))"
```

### High Memory Usage

```bash
# Check process memory
ps aux | grep python

# Increase scan interval (edit scanner.py)
# Change time.sleep(5) to time.sleep(10) or higher

# Aggregate old data
cd wifi-heatmap-dashboard
python3 db_maintenance.py aggregate --days 7
```

### Web Interface Not Accessible

```bash
# Check if services are running
ps aux | grep python

# Check ports are listening
netstat -tulpn | grep :5000
netstat -tulpn | grep :5001

# Check firewall
sudo ufw status
sudo ufw allow 5000
sudo ufw allow 5001
```

---

## 📊 Understanding the Data

### Signal Strength (dBm)

- **-30 to -50 dBm**: Excellent signal
- **-50 to -60 dBm**: Good signal
- **-60 to -70 dBm**: Fair signal
- **-70 to -80 dBm**: Weak signal
- **-80 to -90 dBm**: Very weak signal
- **Below -90 dBm**: Unusable

### Channel Recommendations

- **Channels 1, 6, 11**: Only non-overlapping 2.4GHz channels
- **Green bars**: Low congestion (good)
- **Orange bars**: Medium congestion (okay)
- **Red bars**: High congestion (avoid)

### Alert Types

- **Warning** (Orange): Signal degradation or network disappeared
- **Info** (Blue): Poor signal quality detected
- **Error** (Red): Critical issues (reserved for future use)

---

## 💾 Backup & Restore

### Backup Everything

```bash
# Stop services
sudo systemctl stop wifi-scanner.service wifi-dashboard.service

# Backup database and alerts
cp wifi-heatmap-dashboard/data/wifi_data.db wifi_data_backup_$(date +%Y%m%d).db
cp wifi-heatmap-dashboard/data/alerts.json alerts_backup_$(date +%Y%m%d).json

# Export to CSV
cd wifi-heatmap-dashboard
python3 db_maintenance.py export backup_$(date +%Y%m%d).csv

# Restart services
sudo systemctl start wifi-scanner.service wifi-dashboard.service
```

### Restore Database

```bash
# Stop services
sudo systemctl stop wifi-scanner.service wifi-dashboard.service

# Restore database
cp wifi_data_backup_20251125.db wifi-heatmap-dashboard/data/wifi_data.db

# Restart services
sudo systemctl start wifi-scanner.service wifi-dashboard.service
```

---

## 🎨 Customization

### Change Scan Interval

Edit `wifi-collector/scanner.py`:

```python
time.sleep(5)  # Change 5 to your desired seconds
```

### Adjust Alert Thresholds

Edit `wifi-heatmap-dashboard/alerts.py`:

```python
SIGNAL_DEGRADATION_THRESHOLD = -10  # Change to -15 for less sensitive
POOR_SIGNAL_THRESHOLD = -80         # Change to -75 for stricter
NETWORK_DISAPPEARANCE_MINUTES = 30  # Change to 60 for longer wait
```

### Change Dashboard Port

Edit `wifi-heatmap-dashboard/app.py`:

```python
app.run(host="0.0.0.0", port=5000, ...)  # Change 5000 to desired port
```

### Change Control Panel Port

Edit `wifi-collector/scanner.py`:

```python
control_app.run(host="0.0.0.0", port=5001, ...)  # Change 5001 to desired port
```

---

## 📈 Performance Tips

### For Better Performance on Pi Zero 2 W:

1. **Increase scan interval**: 10-30 seconds instead of 5
2. **Aggregate old data**: Keep only 7 days of detailed data
3. **Limit chart generation**: Only generate when viewing dashboard
4. **Reduce retention**: Delete data older than 30 days
5. **Use static dashboard**: Less CPU than interactive view
6. **Disable debug mode**: Set `debug=False` in app.py
7. **Schedule maintenance**: Run weekly `vacuum` and `aggregate`

---

## 🔗 Key Files

| File                | Purpose                       |
| ------------------- | ----------------------------- |
| `scanner.py`        | WiFi scanning + control panel |
| `app.py`            | Main dashboard server         |
| `analyzer.py`       | Data analysis & visualization |
| `alerts.py`         | Alert system & checks         |
| `db_maintenance.py` | Database management tool      |
| `data/wifi_data.db` | SQLite database               |
| `data/alerts.json`  | Alert history                 |
| `static/*.png`      | Generated chart images        |

---

## 📞 Quick Commands Cheat Sheet

```bash
# Start everything
cd wifi-collector && python3 scanner.py &
cd wifi-heatmap-dashboard && python3 app.py &

# Stop everything
pkill -f scanner.py
pkill -f app.py

# Database stats
python3 db_maintenance.py stats

# Check alerts
python3 alerts.py

# Export today's data
python3 db_maintenance.py export today.csv --days 1

# Clean old data
python3 db_maintenance.py cleanup --days 30

# Optimize DB
python3 db_maintenance.py vacuum

# View logs
tail -f /var/log/syslog | grep python

# Check services
systemctl status wifi-*.service

# Restart services
sudo systemctl restart wifi-scanner.service wifi-dashboard.service
```

---

**Last Updated**: November 25, 2025
