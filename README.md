# WiFi Heatmap Analyzer for Raspberry Pi Zero 2 W

Advanced WiFi network analysis and monitoring system optimized for Raspberry Pi Zero 2 W.

## 🚀 New Features

### 1. **Enhanced Data Collection**

- **Extended Metadata**: Now captures BSSID/MAC addresses, channel numbers, frequency, encryption type, and vendor information
- **SQLite Database**: Replaced CSV files with efficient SQLite database for better performance and scalability
- **Automatic Schema**: Database with proper indexing for fast queries

### 2. **Web-Based Room Control**

- **Control Panel**: Web interface at `http://<pi-ip>:5001` to change scanning location without editing code
- **Real-Time Updates**: Change rooms on-the-fly during scanning
- **No SSH Required**: Update location from any device on your network

### 3. **Time-Series Trending**

- **Historical Analysis**: Track signal strength changes over 24 hours
- **Top Networks**: Automatic focus on most frequently seen networks
- **15-Minute Intervals**: Smoothed trend lines for easier pattern recognition

### 4. **Channel Overlap Analysis**

- **2.4GHz Congestion Map**: Visual representation of channel usage across channels 1-14
- **Interference Detection**: Shows which channels overlap and interfere with each other
- **Smart Recommendations**: Suggests best channel (1, 6, or 11) with least congestion
- **Color-Coded**: Red (high congestion), Orange (medium), Green (low)

### 5. **Interactive Dashboard**

- **Plotly Charts**: Interactive, zoomable visualizations
- **Two View Modes**: Static (matplotlib) and Interactive (Plotly) dashboards
- **Real-Time Updates**: Server-Sent Events for live data streaming
- **Statistics Cards**: Network count, room count, total scans displayed prominently

### 6. **Alert System**

- **Signal Degradation Detection**: Alerts when signal drops >10 dBm
- **Poor Signal Warnings**: Notifications for networks below -80 dBm
- **Network Disappearance**: Alerts when known networks go offline for >30 minutes
- **Alert Dashboard**: Dedicated page at `/alerts` to view all warnings
- **Persistent Storage**: Alerts saved to JSON file for historical tracking

### 7. **Comprehensive Statistics**

- **Network Overview**: Unique networks, rooms scanned, total scans
- **Date Range Tracking**: Shows earliest to latest scan timestamps
- **Security Analysis**: Breakdown of encryption types (WPA2, WPA3, Open, etc.)
- **Per-Room Averages**: Quick comparison of signal quality across locations

### 8. **REST API Endpoints**

- `GET /api/stats` - Network statistics
- `GET /api/latest` - Latest scan data (last hour)
- `GET /api/alerts` - Recent alerts (last 24h)
- `GET /api/alerts/check` - Trigger alert checks manually
- `GET /api/channel_recommendations` - Channel optimization data
- `GET /stream` - Server-Sent Events for real-time updates

## 📋 Requirements

```
flask>=2.3.0
pandas>=2.0.0
matplotlib>=3.7.0
plotly>=5.14.0
```

## 🔧 Installation

1. **Install Dependencies**:

```bash
pip install -r wifi-heatmap-dashboard/requirements.txt
```

2. **Start the Scanner** (on Raspberry Pi):

```bash
cd wifi-collector
python scanner.py
```

- Collector runs on port 5001 (control panel)
- Database created at `wifi-heatmap-dashboard/data/wifi_data.db`

3. **Start the Dashboard**:

```bash
cd wifi-heatmap-dashboard
python app.py
```

- Dashboard runs on port 5000

## 🖥️ Dashboard Access

- **Main Dashboard**: `http://<pi-ip>:5000/`
- **Interactive View**: `http://<pi-ip>:5000/interactive`
- **Alerts Page**: `http://<pi-ip>:5000/alerts`
- **Scanner Control**: `http://<pi-ip>:5001/`

## 📊 Features Overview

### Static Dashboard (`/`)

- WiFi signal heatmap (room vs network)
- Average signal per room bar chart
- 24-hour signal trends
- Channel congestion analysis
- Channel recommendations
- Network statistics

### Interactive Dashboard (`/interactive`)

- All static features plus:
- Real-time data streaming
- Interactive Plotly charts (zoom, pan, hover)
- Live scan counter
- Latest scans feed (last 20)
- Auto-refresh every 5 minutes

### Alerts Dashboard (`/alerts`)

- Last 24 hours of alerts
- Color-coded by severity (warning, error, info)
- Manual alert check trigger
- Alert counts by type
- Auto-refresh every 5 minutes

### Scanner Control Panel (`:5001`)

- Change scanning location/room name
- View current location
- Simple web interface
- No need to edit code or restart scanner

## 🎯 Channel Recommendations

The system analyzes 2.4GHz channel usage and provides:

- **Best Channel**: Least congested among channels 1, 6, and 11
- **Non-Overlapping Channels**: Always recommends 1, 6, or 11 (only truly non-overlapping channels)
- **Congestion Map**: Visual heatmap showing which channels interfere
- **Network Count**: Number of networks on each channel

### Why Channels 1, 6, and 11?

2.4GHz WiFi channels are 20 MHz wide but only 5 MHz apart. Only channels 1, 6, and 11 don't overlap:

- Channel 1: 2401-2423 MHz
- Channel 6: 2426-2448 MHz
- Channel 11: 2451-2473 MHz

## 🚨 Alert System

The alert system monitors for three types of issues:

### 1. Signal Degradation

- Triggers when signal drops >10 dBm compared to previous hour
- Helps identify interference or hardware issues
- Tracked per room and network

### 2. Poor Signal Quality

- Alerts for networks consistently below -80 dBm
- Indicates areas needing additional access points
- Helps optimize router placement

### 3. Network Disappearance

- Detects when previously seen networks go offline >30 minutes
- Could indicate router failure or configuration changes
- Useful for monitoring critical networks

### Running Manual Alert Checks

```bash
cd wifi-heatmap-dashboard
python alerts.py
```

Or trigger via API:

```bash
curl http://<pi-ip>:5000/api/alerts/check
```

## 🔄 Database Schema

```sql
CREATE TABLE wifi_scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    room TEXT NOT NULL,
    ssid TEXT NOT NULL,
    bssid TEXT,           -- MAC address
    signal INTEGER,       -- 0-100 scale
    channel INTEGER,      -- 1-14 for 2.4GHz
    frequency TEXT,       -- e.g., "2437 MHz"
    security TEXT,        -- e.g., "WPA2"
    vendor TEXT           -- First 3 octets of MAC
);
```

Indexes on: `timestamp`, `room`, `ssid` for fast queries.

## 📈 Performance Optimizations for Pi Zero 2 W

- **Incremental Rendering**: Charts cached and regenerated only when needed
- **Database Indexing**: Fast queries even with thousands of scans
- **Selective Loading**: Time-based filtering to limit data processing
- **Efficient Resampling**: 15-minute intervals for trend charts
- **Background Threading**: Scanner control panel runs in daemon thread
- **Static Assets**: Matplotlib images pre-rendered, reducing CPU load

## 🐛 Troubleshooting

### Scanner Won't Start

```bash
# Check if nmcli is available
nmcli --version

# Test WiFi scanning manually
nmcli dev wifi list
```

### Database Errors

```bash
# Check database exists
ls -lh wifi-heatmap-dashboard/data/wifi_data.db

# View recent scans
sqlite3 wifi-heatmap-dashboard/data/wifi_data.db "SELECT * FROM wifi_scans ORDER BY timestamp DESC LIMIT 10;"
```

### Dashboard Not Loading

```bash
# Check if data exists
python -c "from analyzer import load_all_data; print(len(load_all_data()))"

# Check for errors
tail -f /var/log/syslog | grep python
```

### Memory Issues on Pi Zero 2 W

- Reduce scan interval: Change `time.sleep(5)` to `time.sleep(10)` in scanner.py
- Limit data retention: Run regular cleanups
- Archive old data: Export to CSV and delete from database

## 🔮 Future Enhancement Ideas

- **GPS Integration**: Add GPS coordinates for outdoor mapping
- **Bluetooth Scanning**: Detect nearby BLE beacons for automatic location
- **PDF Reports**: Generate exportable reports with all charts
- **Email Alerts**: Send notifications via SMTP
- **Network Quality Score**: Combined metric (signal + channel congestion)
- **AP Vendor Detection**: Identify router manufacturers from MAC OUI
- **Multi-Floor Support**: 3D visualization for multi-story buildings
- **Comparison Mode**: Side-by-side room comparisons
- **Export to Ekahau**: Convert data for professional WiFi planning tools

## 📄 File Structure

```
Wifi Heatmap/
├── wifi-collector/
│   ├── scanner.py          # Enhanced scanner with DB, control panel
│   └── mover.py            # Legacy file mover (not needed with DB)
└── wifi-heatmap-dashboard/
    ├── app.py              # Flask app with new endpoints
    ├── analyzer.py         # Analysis functions + Plotly
    ├── alerts.py           # Alert system (NEW)
    ├── requirements.txt    # Dependencies
    ├── data/
    │   ├── wifi_data.db    # SQLite database (AUTO-CREATED)
    │   └── alerts.json     # Alert history (AUTO-CREATED)
    ├── static/
    │   ├── heatmap.png     # Generated heatmap
    │   ├── barchart.png    # Generated bar chart
    │   ├── trends.png      # Generated trend chart
    │   └── channel_overlap.png  # Channel analysis
    └── templates/
        ├── index.html      # Static dashboard (UPDATED)
        ├── interactive.html # Interactive dashboard (NEW)
        └── alerts.html     # Alerts page (NEW)
```

## 🤝 Contributing

Feel free to extend this project with:

- Additional alert types
- More visualization options
- Integration with other WiFi tools
- Mobile app companion
- Automated scheduling for scans

## 📝 License

This project is for personal/educational use. Respect network privacy and only scan networks you own or have permission to monitor.

## 🎉 Changelog

### Version 2.0 (Current)

- ✅ SQLite database storage
- ✅ Enhanced metadata collection (BSSID, channel, security)
- ✅ Web-based room control panel
- ✅ Time-series trending analysis
- ✅ Channel overlap detection
- ✅ Interactive Plotly dashboards
- ✅ Real-time updates via SSE
- ✅ Alert system with notifications
- ✅ REST API endpoints
- ✅ Improved UI with dark theme

### Version 1.0 (Original)

- Basic WiFi scanning with nmcli
- CSV file storage
- Static matplotlib visualizations
- Flask dashboard
- Manual room changes via code edits
