#!/usr/bin/env python3
"""
LED Index Discovery Script
==========================
Cycles through LED indices 0-11 to identify which physical LED
corresponds to each index on the Keybow Mini.

Keybow Mini LED mapping (discovered):
    LED 9 = Physical LEFT
    LED 6 = Physical CENTER
    LED 3 = Physical RIGHT
"""

import keybow
import time

keybow.setup()

print("Testing LED indices 0-11...")
print("Watch which LED lights up for each index.\n")

for i in range(12):
    # Turn off all LEDs
    for j in range(12):
        keybow.set_led(j, 0, 0, 0)
    
    # Light up current index
    keybow.set_led(i, 255, 255, 255)
    keybow.show()
    
    print(f"LED index {i} is ON")
    time.sleep(1.5)

# Turn off all LEDs
for i in range(12):
    keybow.set_led(i, 0, 0, 0)
keybow.show()

print("\nDone. Keybow Mini uses indices 3, 6, 9 for the three keys.")
