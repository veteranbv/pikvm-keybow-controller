#!/bin/bash
#
# PiKVM Keybow Controller Installation Script
# ============================================
# Run this on the target Raspberry Pi Zero W after fresh OS install.
#
# Prerequisites:
#   - Raspberry Pi OS Lite (32-bit) - required for Pi Zero W ARMv6
#   - SPI enabled via raspi-config
#   - Network connectivity to PiKVM
#

set -e

INSTALL_DIR="$HOME/pikvm-ctrl"
SERVICE_NAME="pikvm-keybow"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== PiKVM Keybow Controller Installation ==="
echo ""
echo "Installing as user: $USER"
echo "Install directory: $INSTALL_DIR"
echo ""

# Check SPI is enabled
if [ ! -e /dev/spidev0.0 ]; then
    echo "ERROR: SPI not enabled!"
    echo "Run: sudo raspi-config -> Interface Options -> SPI -> Enable"
    exit 1
fi
echo "✓ SPI enabled"

# Install system dependencies
echo ""
echo "Installing system packages..."
sudo apt update
sudo apt install -y python3-venv python3-dev

# Create project directory
echo ""
echo "Creating project directory..."
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Create virtual environment
echo ""
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo ""
echo "Installing Python packages..."
pip install --upgrade pip
pip install keybow requests spidev rpi-lgpio python-dotenv

# Copy main script
if [ -f "$SCRIPT_DIR/../src/pikvm_keybow.py" ]; then
    cp "$SCRIPT_DIR/../src/pikvm_keybow.py" "$INSTALL_DIR/"
    echo "✓ Copied pikvm_keybow.py"
else
    echo "WARNING: pikvm_keybow.py not found in ../src/"
    echo "You'll need to copy it manually"
fi

# Copy .env.example if .env doesn't exist
if [ ! -f "$INSTALL_DIR/.env" ]; then
    if [ -f "$SCRIPT_DIR/../.env.example" ]; then
        cp "$SCRIPT_DIR/../.env.example" "$INSTALL_DIR/.env"
        echo "✓ Copied .env.example to .env (edit with your credentials)"
    fi
else
    echo "✓ .env already exists, skipping"
fi

# Generate and install systemd service from template
echo ""
echo "Installing systemd service..."
TEMPLATE_FILE="$SCRIPT_DIR/../systemd/pikvm-keybow.service.template"
if [ -f "$TEMPLATE_FILE" ]; then
    sed -e "s|{{USER}}|$USER|g" \
        -e "s|{{INSTALL_DIR}}|$INSTALL_DIR|g" \
        "$TEMPLATE_FILE" | sudo tee /etc/systemd/system/pikvm-keybow.service > /dev/null
    echo "✓ Generated service file for user '$USER'"
else
    echo "WARNING: Service template not found at $TEMPLATE_FILE"
fi
sudo systemctl daemon-reload

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit $INSTALL_DIR/.env with your PiKVM credentials"
echo "  2. Test manually: cd $INSTALL_DIR && source venv/bin/activate && python pikvm_keybow.py"
echo "  3. Enable service: sudo systemctl enable $SERVICE_NAME"
echo "  4. Start service: sudo systemctl start $SERVICE_NAME"
echo "  5. Check status: sudo systemctl status $SERVICE_NAME"
echo ""
