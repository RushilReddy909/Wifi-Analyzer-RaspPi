# Systemd Service Installation

## Auto-Start on Boot

To run the WiFi analyzer automatically on Raspberry Pi boot:

### 1. Install Services

```bash
# Copy service files
sudo cp systemd/wifi-scanner.service /etc/systemd/system/
sudo cp systemd/wifi-dashboard.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload
```

### 2. Enable Services

```bash
# Enable auto-start on boot
sudo systemctl enable wifi-scanner.service
sudo systemctl enable wifi-dashboard.service
```

### 3. Start Services

```bash
# Start immediately
sudo systemctl start wifi-scanner.service
sudo systemctl start wifi-dashboard.service
```

### 4. Check Status

```bash
# View service status
sudo systemctl status wifi-scanner.service
sudo systemctl status wifi-dashboard.service

# View logs
sudo journalctl -u wifi-scanner.service -f
sudo journalctl -u wifi-dashboard.service -f
```

## Service Management Commands

```bash
# Stop services
sudo systemctl stop wifi-scanner.service
sudo systemctl stop wifi-dashboard.service

# Restart services
sudo systemctl restart wifi-scanner.service
sudo systemctl restart wifi-dashboard.service

# Disable auto-start
sudo systemctl disable wifi-scanner.service
sudo systemctl disable wifi-dashboard.service
```

## Troubleshooting

### Service won't start

Check the path in the service file matches your installation:

```bash
# Edit service file if needed
sudo nano /etc/systemd/system/wifi-scanner.service

# Update WorkingDirectory and ExecStart paths
# Then reload and restart
sudo systemctl daemon-reload
sudo systemctl restart wifi-scanner.service
```

### Permission Issues

Ensure the pi user has access:

```bash
# Change ownership if needed
sudo chown -R pi:pi "/home/pi/Wifi Heatmap"

# Make scripts executable
chmod +x "/home/pi/Wifi Heatmap/wifi-collector/scanner.py"
chmod +x "/home/pi/Wifi Heatmap/wifi-heatmap-dashboard/app.py"
```

### View Detailed Logs

```bash
# Last 50 lines
sudo journalctl -u wifi-scanner.service -n 50

# Follow logs in real-time
sudo journalctl -u wifi-scanner.service -f

# Logs since last boot
sudo journalctl -u wifi-scanner.service -b
```

## Note

Make sure to update the paths in the service files if your installation directory is different from `/home/pi/Wifi Heatmap/`.
