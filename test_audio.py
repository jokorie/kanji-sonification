#!/usr/bin/env python3
"""
Simple test to verify pyo audio recording works.
"""

from pyo import *

# Initialize server
s = Server(sr=44100, buffersize=512)
s.boot()
s.start()

# Create a simple sine wave
osc = Sine(freq=440, mul=0.5)  # 440 Hz, amplitude 0.5
osc.out()

# Record for 2 seconds
print("Recording test sine wave...")
s.recstart("test_output.wav")

import time
time.sleep(2)  # Record for 2 seconds

s.recstop()
print("Recording stopped.")

s.stop()
s.shutdown()

print("Test recording saved to test_output.wav")
