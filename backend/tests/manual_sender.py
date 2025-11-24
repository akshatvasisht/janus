"""
Manual Integration Tool for Testing Receiver
Sends test packets to the running receiver for manual testing.
"""

# Standard library imports
import os
import socket
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Local imports
from common.protocol import JanusMode, JanusPacket


def send_test_packet(text, mode, tcp=False, prosody=None, override_emotion=None):
    """
    Send a test packet to the receiver.
    
    Args:
        text: Text content for the packet.
        mode: JanusMode enum value (SEMANTIC_VOICE, TEXT_ONLY, MORSE_CODE).
        tcp: If True, use TCP; if False, use UDP.
        prosody: Optional prosody dictionary. Defaults to {'energy': 'Normal', 'pitch': 'Normal'}.
        override_emotion: Optional override emotion. Defaults to "Auto".
    
    Returns:
        None
    """
    # Default prosody if not provided
    if prosody is None:
        prosody = {'energy': 'Normal', 'pitch': 'Normal'}
    
    # Create JanusPacket
    packet = JanusPacket(
        text=text,
        mode=mode,
        prosody=prosody,
        override_emotion=override_emotion
    )
    
    # Serialize packet
    serialized_bytes = packet.serialize()
    
    # Determine target address (Read from ENV or default to localhost)
    target_ip = os.getenv("TARGET_IP", "127.0.0.1")
    target_port = int(os.getenv("TARGET_PORT", 5005))

    if tcp:
        # TCP mode: connect and send with length prefix
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((target_ip, target_port))
            
            # Prepend 4-byte big-endian length header
            payload_length = len(serialized_bytes)
            header = struct.pack('>I', payload_length)
            framed_payload = header + serialized_bytes
            
            # Send data
            sock.sendall(framed_payload)
            print(f"Sent TCP packet: {len(framed_payload)} bytes (payload: {payload_length} bytes)")
        except ConnectionRefusedError:
            print(f"Error: Could not connect to {target_ip}:{target_port}")
            print("Make sure the receiver is running!")
        finally:
            sock.close()
    else:
        # UDP mode: send datagram
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(serialized_bytes, (target_ip, target_port))
            print(f"Sent UDP packet: {len(serialized_bytes)} bytes")
        except Exception as e:
            print(f"Error sending UDP packet: {e}")
        finally:
            sock.close()


if __name__ == "__main__":
    # Check if we are in TCP mode (e.g. for Ngrok)
    use_tcp = os.getenv("USE_TCP", "False").lower() == "true"

    print(f"Configuration: TCP={use_tcp}")

    print("Sending test packet: 'Hello World'")
    send_test_packet(
        text="Hello World",
        mode=JanusMode.SEMANTIC_VOICE,
        tcp=use_tcp
    )
    
    print("\nTest packet sent successfully!")
    print("Check the receiver console for output.")

