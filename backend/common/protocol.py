"""
Module: Protocol Definition
Purpose: Defines the 'Janus Packet' structure and handles the binary serialization.
         This module acts as the contract between the Sender (Ear) and Receiver (Mouthpiece).
         It uses MessagePack to ensure the payload is as small as possible.
"""

# Standard library imports
import enum
import time
from typing import Optional

# Third-party imports
import msgpack


class JanusMode(enum.IntEnum):
    """
    Transmission Modes for the Janus Packet.
    """
    SEMANTIC_VOICE = 0  # Full semantic (Text + Prosody Data)
    TEXT_ONLY = 1       # Text only (no prosody, receiver uses default voice)
    MORSE_CODE = 2      # Morse code (structure only, no implementation yet)


class JanusPacket:
    """
    The Packet Structure for Janus communication.
    Uses compact keys to minimize payload size.
    """
    
    def __init__(
        self,
        text: str,
        mode: JanusMode,
        prosody: dict[str, str],
        override_emotion: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> None:
        """
        Initialize a Janus Packet.
        
        Args:
            text: The transcribed text content.
            mode: Transmission mode (JanusMode enum).
            prosody: Prosody metadata dictionary with 'energy' and 'pitch' keys.
            override_emotion: Optional override emotion. Defaults to "Auto".
            timestamp: Optional timestamp. If None, uses current time.
        
        Returns:
            None
        """
        self.text = text
        self.mode = mode
        self.prosody = prosody
        self.override_emotion = override_emotion if override_emotion is not None else "Auto"
        self.timestamp = timestamp if timestamp is not None else time.time()
    
    def to_dict(self) -> dict:
        """
        Convert class attributes into a raw dictionary for serialization.
        
        Uses short keys to minimize payload size.
        
        Returns:
            dict: Dictionary with compact keys ('t', 'm', 'p', 'o', 'ts').
        """
        result = {
            't': self.text,
            'm': int(self.mode),
            'p': self.prosody,
            'ts': self.timestamp
        }
        
        if self.override_emotion != "Auto":
            result['o'] = self.override_emotion
        
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> "JanusPacket":
        """
        Reconstruct the Packet object from a raw dictionary.
        
        Args:
            data: Dictionary with compact keys ('t', 'm', 'p', 'o', 'ts')
        
        Returns:
            JanusPacket: Reconstructed packet object
        """
        text = data.get('t', '')
        mode = JanusMode(data.get('m', 0))
        prosody = data.get('p', {})
        override_emotion = data.get('o', 'Auto')
        timestamp = data.get('ts', time.time())
        
        return cls(text, mode, prosody, override_emotion, timestamp)
    
    def serialize(self) -> bytes:
        """
        Convert the Packet object into a compact binary byte string.
        
        Uses MessagePack for efficient serialization.
        
        Returns:
            bytes: Compact binary payload.
        """
        data_dict = self.to_dict()
        return msgpack.packb(data_dict, use_bin_type=True)
    
    @classmethod
    def deserialize(cls, payload_bytes: bytes) -> "JanusPacket":
        """
        Convert binary bytes back into a Packet object.
        
        Args:
            payload_bytes: Binary payload (bytes)
        
        Returns:
            JanusPacket: Deserialized packet object
        """
        data_dict = msgpack.unpackb(payload_bytes, raw=False)
        return cls.from_dict(data_dict)
