#!/bin/bash
# Quick setup script for WiFi Analyzer on Raspberry Pi Zero 2 W

echo "🚀 WiFi Analyzer Setup Script"
echo "================================"
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "⚠️  Warning: This script is designed for Linux/Raspberry Pi"
    echo "   It may not work correctly on other systems."
    echo ""
fi

# Check if nmcli is available
echo "📡 Checking for NetworkManager..."
if ! command -v nmcli &> /dev/null; then
    echo "❌ nmcli not found! Installing NetworkManager..."
    sudo apt-get update
    sudo apt-get install -y network-manager
else
    echo "✅ NetworkManager is installed"
fi

# Check Python version
echo ""
echo "🐍 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Found Python $python_version"

# Install pip if needed
if ! command -v pip3 &> /dev/null; then
    echo "📦 Installing pip..."
    sudo apt-get install -y python3-pip
fi

# Install dependencies
echo ""
echo "📦 Installing Python dependencies..."
cd "$(dirname "$0")/wifi-heatmap-dashboard"
pip3 install -r requirements.txt

# Create necessary directories
echo ""
echo "📁 Creating directories..."
mkdir -p data
mkdir -p static

# Initialize database
echo ""
echo "🗄️  Initializing database..."
cd ../wifi-collector
python3 -c "from scanner import init_database; init_database(); print('✅ Database initialized')"

echo ""
echo "================================"
echo "✅ Setup Complete!"
echo ""
echo "📝 Next Steps:"
echo ""
echo "1. Start the WiFi Scanner (in one terminal):"
echo "   cd wifi-collector"
echo "   python3 scanner.py"
echo ""
echo "2. Start the Dashboard (in another terminal):"
echo "   cd wifi-heatmap-dashboard"
echo "   python3 app.py"
echo ""
echo "3. Access the interfaces:"
echo "   • Scanner Control: http://$(hostname -I | awk '{print $1}'):5001"
echo "   • Main Dashboard:  http://$(hostname -I | awk '{print $1}'):5000"
echo "   • Interactive View: http://$(hostname -I | awk '{print $1}'):5000/interactive"
echo "   • Alerts Page:     http://$(hostname -I | awk '{print $1}'):5000/alerts"
echo ""
echo "🎉 Happy WiFi Analyzing!"
