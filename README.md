# PiKVM Keybow Mini Controller

Physical 3-button controller for navigating PiKVM Switch ports without needing another device.

## Why I Built This

I have a PiKVM V4 Plus with two daisy-chained Switch units controlling 8 servers in my homelab rack. It's connected to a pull-out KVM console with HDMI and USBpassthrough, so I can view any server directly on the built-in monitor.

The problem: to switch between servers, I had to pull out my phone, open the PiKVM web UI, authenticate, navigate to the switch page, and tap the port I wanted. For quick tasks like checking POST screens or BIOS settings across multiple machines, this friction added up fast.

What I actually wanted was dead simple—three physical buttons: **Previous**, **Home**, and **Next**. Press a button, switch ports, done. No screens, no authentication prompts, no context switching.

So I built exactly that. A Raspberry Pi Zero W with a Pimoroni Keybow Mini sits next to the rack. Three mechanical keys with RGB feedback. The whole interaction takes under a second and I never have to look away from what I'm doing.

Three buttons, no auth prompts, no phone. Problem solved.

This is a control-only device. For visual status displays showing which server is active, see the [Enviro+ Display](https://github.com/veteranbv/pikvm-enviro-display) or [unified Display Controller](https://github.com/veteranbv/pikvm-display-controller) projects.

## Button Layout

```text
┌─────────┐  ┌─────────┐  ┌─────────┐
│  PREV   │  │  HOME   │  │  NEXT   │
│ (wrap)  │  │(port 0) │  │ (wrap)  │
└─────────┘  └─────────┘  └─────────┘
   LEFT        CENTER       RIGHT
```

- **LEFT (Prev)**: Navigate to previous port with wrap-around (port 0 → port 7)
- **CENTER (Home)**: Jump directly to port 0
- **RIGHT (Next)**: Navigate to next port with wrap-around (port 7 → port 0)

## LED Feedback

| Color | Meaning |
|-------|---------|
| Dim White | Idle/Ready |
| Orange | Previous port (success) |
| Cyan | Next port (success) |
| Green | Home/Port 0 (success) |
| Red | Error (API timeout, network issue) |

## Project Structure

```bash
pikvm-keybow-controller/
├── README.md                 # This file
├── .env                      # Your local config (gitignored)
├── .env.example              # Template for .env
├── .gitignore
├── src/
│   └── pikvm_keybow.py       # Main controller script
├── systemd/
│   └── pikvm-keybow.service.template  # Systemd unit template
└── scripts/
    ├── install.sh            # Installation script
    ├── led_test.py           # LED index discovery
    └── key_test.py           # Key index discovery
```

## Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
nano .env
```

| Variable | Description | Example |
|----------|-------------|---------|
| `PIKVM_HOST` | PiKVM HTTPS URL matching its certificate | `https://pikvm.example.net` |
| `PIKVM_USER` | API username | `admin` |
| `PIKVM_PASS` | API password | `secretpass` |
| `TOTAL_PORTS` | Number of switch ports | `8` |

> **Warning**: Never commit `.env` - it contains secrets and is gitignored.

For HTTPS API requests, the controller verifies the certificate chain and hostname.
For a private issuer, set `REQUESTS_CA_BUNDLE` in `.env` or the service environment
to a readable PEM file containing the issuing CA certificates. Keep server
private keys on the PiKVM. Publicly trusted certificates use Requests' default
trust store. Untrusted or mismatched certificates cause an API error;
configure the correct certificate and trust file before restarting the service.

To run the TLS regression tests, install the existing `requests` dependency and
OpenSSL, then run `python3 -m unittest discover -s tests -v`. The tests use a
local HTTPS server and synthetic credentials. They do not initialize GPIO or
send commands to a PiKVM.

## Hardware Notes

### Keybow Mini Index Mapping

The Keybow Mini uses non-sequential indices for both keys and LEDs:

| Physical Position | Key Index | LED Index |
|-------------------|-----------|-----------|
| LEFT | 6 | 9 |
| CENTER | 3 | 6 |
| RIGHT | 0 | 3 |

This was discovered through testing - the Keybow library doesn't document this clearly.

### Required Hardware

- Raspberry Pi Zero W (or Zero 2 W)
- Pimoroni Keybow Mini (3-key version)
- Micro USB power supply
- MicroSD card (8GB+)

## Installation

### 1. Flash Raspberry Pi OS

Use Raspberry Pi Imager to flash **Raspberry Pi OS Lite (32-bit)**.

> **Important**: Pi Zero W requires 32-bit OS (ARMv6 architecture)

Pre-configure via Imager (Ctrl+Shift+X):

- Set hostname
- Enable SSH with password authentication
- Set username/password
- Configure WiFi credentials

### 2. Enable SPI

```bash
sudo raspi-config
# Navigate: Interface Options → SPI → Enable
sudo reboot
```

Verify SPI is enabled:

```bash
ls /dev/spi*
# Should show: /dev/spidev0.0  /dev/spidev0.1
```

### 3. Run Installation Script

Clone this repo to the Pi and run the installer:

```bash
git clone https://github.com/veteranbv/pikvm-keybow-controller.git
cd pikvm-keybow-controller
./scripts/install.sh
```

The installer will:

- Install system dependencies
- Create a Python virtual environment in `~/pikvm-ctrl`
- Install required Python packages
- Copy the controller script
- Generate and install the systemd service for your user

### 4. Configure Credentials

Edit the `.env` file with your PiKVM connection details:

```bash
nano ~/pikvm-ctrl/.env
```

### 5. Test Manually

```bash
cd ~/pikvm-ctrl
source venv/bin/activate
python pikvm_keybow.py
```

Press buttons to verify functionality.

### 6. Enable and Start Service

```bash
sudo systemctl enable pikvm-keybow
sudo systemctl start pikvm-keybow
```

Check status:

```bash
sudo systemctl status pikvm-keybow
journalctl -u pikvm-keybow -f
```

## PiKVM API Reference

### Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/switch` | GET | Get current switch state |
| `/api/switch/set_active?port=N` | POST | Set specific port (0-7) |

### Example Response

```json
{
  "ok": true,
  "result": {
    "summary": {
      "active_port": 3
    }
  }
}
```

### Authentication

Uses HTTP Basic Auth. Credentials are read from the `.env` file.

## Troubleshooting

### GPIO Edge Detection Error

```bash
RuntimeError: Failed to add edge detection
```

**Solution**: Use `rpi-lgpio` instead of `RPi.GPIO`:

```bash
pip uninstall RPi.GPIO
pip install rpi-lgpio
```

### SPI Not Found

```bash
FileNotFoundError: /dev/spidev0.0
```

**Solution**: Enable SPI via `raspi-config` and reboot.

### Network Timeout

**Check**:

1. Pi can reach PiKVM: `curl -k https://YOUR_PIKVM_IP/api/switch -u admin:password`
2. Firewall allows traffic between controller and PiKVM on port 443
3. If your Pi Zero's WiFi and PiKVM are on different VLANs, ensure you have a firewall rule allowing traffic between them

### Wrong Button Mapping

Use `scripts/key_test.py` to verify key indices match your hardware.

### LEDs Not Lighting

Use `scripts/led_test.py` to verify LED indices.

## Related Projects

This is part of a three-project suite for PiKVM control and monitoring:

- **[PiKVM Keybow Controller](https://github.com/veteranbv/pikvm-keybow-controller)** - Physical 3-button controller (Pi Zero W + Keybow Mini) - *This project*
- **[PiKVM Enviro Display](https://github.com/veteranbv/pikvm-enviro-display)** - Status display with environmental sensors (Pico W + Enviro+ Pack)
- **[PiKVM Display Controller](https://github.com/veteranbv/pikvm-display-controller)** - Unified 5-button controller with display (Pico W + GFX Pack)

Each project addresses different aspects of physical interaction with PiKVM:

- **Keybow**: Best for simple port switching with tactile mechanical keys
- **Enviro Display**: Best for status monitoring with large color display and sensors
- **Display Controller**: Best for compact all-in-one control and status in a single device

## Resources

- [Pimoroni Keybow](https://github.com/pimoroni/keybow-python)
- [PiKVM API Docs](https://docs.pikvm.org/api/)

## License

MIT
