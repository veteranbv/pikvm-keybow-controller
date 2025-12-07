#!/usr/bin/env python3
"""
Key Index Discovery Script
==========================
Prints key index when any button is pressed on the Keybow Mini.
Useful for mapping physical buttons to their software indices.

Keybow Mini key mapping (discovered):
    Key 6 = Physical LEFT
    Key 3 = Physical CENTER
    Key 0 = Physical RIGHT
"""

import keybow
import signal

keybow.setup()

@keybow.on()
def handle_key(index, state):
    action = "pressed" if state else "released"
    print(f"Key {index} {action}")

print("Press any key to see its index. Ctrl+C to exit.\n")
print("Expected mapping for Keybow Mini:")
print("  Physical LEFT   = Key 6")
print("  Physical CENTER = Key 3")
print("  Physical RIGHT  = Key 0")
print()

signal.pause()
