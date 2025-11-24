"""
Module: Link Simulator (The 'Application-Layer Throttle')
Purpose: Simulates the physics of a 300bps connection.
         Instead of throttling the actual network card (which breaks API calls),
         this module calculates how long a packet *would* take to travel at 300bps
         and sleeps for that duration, visualizing the 'upload' in the terminal.
"""

import socket
import time
import struct
import os


# Constants
BAUD_RATE = 300  # Bits per second
BYTES_PER_SECOND = BAUD_RATE / 8  # 37.5 bytes per second


class LinkSimulator:
    """
    Network Simulator that throttles transmission to simulate 300bps connection.
    Supports both UDP (localhost) and TCP (ngrok) modes.
    TCP mode uses length-prefixed framing to handle stream-oriented protocol.
    """
    
    def __init__(self, target_ip: str = "127.0.0.1", target_port: int = 5005, use_tcp: bool = False) -> None:
        """
        Initialize the Link Simulator.
        
        Args:
            target_ip: Target IP address. Default is "127.0.0.1".
            target_port: Target port number. Default is 5005.
            use_tcp: Whether to use TCP instead of UDP. Default is False.
                TCP mode uses length-prefixed framing for stream-oriented protocol.
        """
        self.target_ip = target_ip
        self.target_port = target_port
        self.use_tcp = use_tcp
        self.socket = None
        self._create_socket()
    
    def _create_socket(self) -> None:
        """
        Initialize UDP or TCP socket based on use_tcp flag.
        
        Creates and connects the appropriate socket type. For TCP, attempts to
        connect to the target address. Connection errors are logged but do not
        raise exceptions.
        """
        if self.use_tcp:
            # TCP socket (SOCK_STREAM)
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Connect to target for TCP
            try:
                self.socket.connect((self.target_ip, self.target_port))
            except ConnectionRefusedError:
                print(f"Warning: Could not connect to {self.target_ip}:{self.target_port}")
        else:
            # UDP socket (SOCK_DGRAM)
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    def transmit(self, payload_bytes: bytes) -> None:
        """
        Send data with a simulated 300bps delay.
        
        Calculates transmission delay based on packet size and simulates the
        slow connection by sleeping for the calculated duration. Visualizes
        progress in the terminal and then transmits the data via socket.
        
        Args:
            payload_bytes: Binary payload (bytes) - the msgpack serialized packet.
                For TCP mode, a 4-byte length prefix is automatically added.
        """
        # TCP Framing: Add 4-byte length prefix for TCP mode
        if self.use_tcp:
            payload_length = len(payload_bytes)
            header = struct.pack('>I', payload_length)  # Big-endian unsigned int
            framed_payload = header + payload_bytes
            total_bytes = len(framed_payload)
        else:
            # UDP mode: no framing needed
            framed_payload = payload_bytes
            total_bytes = len(payload_bytes)
        
        # Calculate simulation delay
        delay = total_bytes / BYTES_PER_SECOND
        
        # Log transfer start
        print(f"Transmitting {total_bytes} bytes @ {BAUD_RATE}bps...", end=" ", flush=True)
        
        # Execute delay (the "fake" throttle) with visualization
        self._visualize_progress(delay)
        
        # Actual transmission
        try:
            if self.use_tcp:
                # TCP: send all data (header + payload)
                self.socket.sendall(framed_payload)
            else:
                # UDP: sendto (fire-and-forget)
                self.socket.sendto(framed_payload, (self.target_ip, self.target_port))
        except Exception as e:
            print(f"\nTransmission error: {e}")
    
    def _visualize_progress(self, duration: float) -> None:
        """
        Visualize transmission progress in the terminal.
        
        Prints a progress bar with "#" characters to provide visual feedback
        during the simulated transmission delay.
        
        Args:
            duration: Duration in seconds to simulate. Progress bar is divided
                into 20 steps for smooth visualization.
        """
        num_steps = 20  # Number of progress bar ticks
        tick_time = duration / num_steps
        
        for i in range(num_steps):
            time.sleep(tick_time)
            print("#", end="", flush=True)
        
        print(" Done")
    
    def close(self) -> None:
        """
        Cleanup socket connection.
        
        Closes the socket if it exists and resets it to None. Safe to call
        multiple times.
        """
        if self.socket:
            self.socket.close()
            self.socket = None
