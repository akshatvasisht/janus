#!/usr/bin/env python3
"""
Utility script to list all available PyAudio input and output devices.
Helps in identifying device indices for configuration.
"""
import pyaudio
import sys

def list_devices():
    p = pyaudio.PyAudio()
    print(f"PyAudio Version: {pyaudio.__version__}")
    print(f"Default Input Device: {p.get_default_input_device_info() if p.get_device_count() > 0 else 'None'}")
    print(f"Default Output Device: {p.get_default_output_device_info() if p.get_device_count() > 0 else 'None'}")
    
    print("\nAll Devices:")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        print(f"Index {i}: {info['name']} (Inputs: {info['maxInputChannels']}, Outputs: {info['maxOutputChannels']})")
    
    p.terminate()

if __name__ == "__main__":
    try:
        list_devices()
    except Exception as e:
        print(f"Error: {e}")
