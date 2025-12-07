#!/usr/bin/env python3
"""
PiKVM Keybow Mini Controller
============================
Physical 3-button controller for PiKVM Switch port navigation.

Hardware: Raspberry Pi Zero W + Pimoroni Keybow Mini
Target: PiKVM V4 Plus with daisy-chained Switch units

Button Layout:
    [LEFT]    [CENTER]    [RIGHT]
      ↓          ↓          ↓
     Prev       Home       Next
    (wrap)    (port 0)   (wrap)

LED Feedback:
    - Dim white: Idle/ready
    - Orange: Previous port
    - Cyan: Next port
    - Green: Home (port 0)
    - Red: Error

Configuration:
    Set environment variables or create .env file with:
    - PIKVM_HOST: PiKVM URL (e.g., https://10.0.0.100)
    - PIKVM_USER: API username
    - PIKVM_PASS: API password
    - TOTAL_PORTS: Number of switch ports (default: 8)
"""

import os
import signal
import sys

import keybow
import requests
from requests.auth import HTTPBasicAuth
import urllib3

# Load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, rely on environment variables

# Disable SSL warnings for self-signed cert
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =============================================================================
# CONFIGURATION (from environment)
# =============================================================================

PIKVM_HOST = os.getenv("PIKVM_HOST")
PIKVM_USER = os.getenv("PIKVM_USER")
PIKVM_PASS = os.getenv("PIKVM_PASS")
TOTAL_PORTS = int(os.getenv("TOTAL_PORTS", "8"))

# Validate required config
if not all([PIKVM_HOST, PIKVM_USER, PIKVM_PASS]):
    print("ERROR: Missing required environment variables!")
    print("Set PIKVM_HOST, PIKVM_USER, and PIKVM_PASS")
    print("Either export them or create a .env file")
    sys.exit(1)

# Keybow Mini key indices (non-sequential hardware mapping)
KEY_LEFT = 6    # Physical left button
KEY_CENTER = 3  # Physical center button
KEY_RIGHT = 0   # Physical right button

# Keybow Mini LED indices (also non-sequential)
LED_LEFT = 9
LED_CENTER = 6
LED_RIGHT = 3

# LED Colors (R, G, B)
COLOR_IDLE = (20, 20, 20)      # Dim white
COLOR_PREV = (255, 100, 0)     # Orange
COLOR_NEXT = (0, 255, 100)     # Cyan
COLOR_HOME = (0, 255, 0)       # Green
COLOR_ERROR = (255, 0, 0)      # Red

# =============================================================================
# API FUNCTIONS
# =============================================================================

def get_current_port():
    """Query PiKVM API for current active port."""
    try:
        resp = requests.get(
            f"{PIKVM_HOST}/api/switch",
            auth=HTTPBasicAuth(PIKVM_USER, PIKVM_PASS),
            verify=False,
            timeout=5
        )
        data = resp.json()
        return data["result"]["summary"]["active_port"]
    except Exception as e:
        print(f"Error getting port: {e}")
        return None


def set_port(port):
    """Set PiKVM to specific port number."""
    try:
        resp = requests.post(
            f"{PIKVM_HOST}/api/switch/set_active?port={port}",
            auth=HTTPBasicAuth(PIKVM_USER, PIKVM_PASS),
            verify=False,
            timeout=5
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"Error setting port: {e}")
        return False

# =============================================================================
# LED FUNCTIONS
# =============================================================================

def set_all_leds(r, g, b):
    """Set all three button LEDs to the same color."""
    keybow.set_led(LED_LEFT, r, g, b)
    keybow.set_led(LED_CENTER, r, g, b)
    keybow.set_led(LED_RIGHT, r, g, b)
    keybow.show()


def flash_led(led_index, color, duration=0.2):
    """Flash a specific LED then return to idle."""
    import time
    keybow.set_led(led_index, *color)
    keybow.show()
    time.sleep(duration)
    set_all_leds(*COLOR_IDLE)


def flash_error():
    """Flash all LEDs red to indicate error."""
    import time
    set_all_leds(*COLOR_ERROR)
    time.sleep(0.3)
    set_all_leds(*COLOR_IDLE)

# =============================================================================
# NAVIGATION FUNCTIONS
# =============================================================================

def go_prev():
    """Navigate to previous port with wrap-around."""
    current = get_current_port()
    if current is None:
        flash_error()
        return
    
    new_port = (current - 1) % TOTAL_PORTS
    if set_port(new_port):
        flash_led(LED_LEFT, COLOR_PREV)
        print(f"Switched to port {new_port}")
    else:
        flash_error()


def go_next():
    """Navigate to next port with wrap-around."""
    current = get_current_port()
    if current is None:
        flash_error()
        return
    
    new_port = (current + 1) % TOTAL_PORTS
    if set_port(new_port):
        flash_led(LED_RIGHT, COLOR_NEXT)
        print(f"Switched to port {new_port}")
    else:
        flash_error()


def go_home():
    """Jump directly to port 0."""
    if set_port(0):
        flash_led(LED_CENTER, COLOR_HOME)
        print("Switched to port 0 (home)")
    else:
        flash_error()

# =============================================================================
# KEY HANDLER
# =============================================================================

@keybow.on()
def handle_key(index, state):
    """Handle key press events."""
    if not state:  # Only act on key down
        return
    
    if index == KEY_LEFT:
        go_prev()
    elif index == KEY_CENTER:
        go_home()
    elif index == KEY_RIGHT:
        go_next()

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("PiKVM Keybow Controller starting...")
    print(f"Target: {PIKVM_HOST}")
    print(f"Ports: {TOTAL_PORTS}")
    print("Button mapping: [PREV] [HOME] [NEXT]")
    
    # Initialize with idle LEDs
    keybow.setup()
    set_all_leds(*COLOR_IDLE)
    
    print("Ready. Waiting for button presses...")
    
    # Keep running until interrupted
    signal.pause()


if __name__ == "__main__":
    main()
