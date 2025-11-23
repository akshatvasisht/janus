"""
Test Suite for Phase 3 Transport Layer Components
Tests JanusPacket (Protocol) and LinkSimulator (Network Throttling)
"""

import pytest
import struct
import time
import socket
from unittest.mock import Mock, MagicMock, patch, call
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.common.protocol import JanusPacket, JanusMode
from backend.services.link_simulator import LinkSimulator, BYTES_PER_SECOND


# ============================================================================
# JanusPacket Tests
# ============================================================================

class TestJanusPacket:
    """Tests for JanusPacket protocol class."""
    
    def test_packet_serialization_cycle(self):
        """Test complete serialization cycle: create -> serialize -> deserialize -> verify fields."""
        # Create original packet
        original_packet = JanusPacket(
            text="Hello world",
            mode=JanusMode.SEMANTIC_VOICE,
            prosody={'energy': 'Normal', 'pitch': 'High'},
            override_emotion="Relaxed",
            timestamp=1234567890.0
        )
        
        # Serialize
        serialized = original_packet.serialize()
        assert isinstance(serialized, bytes)
        assert len(serialized) > 0
        
        # Deserialize
        deserialized_packet = JanusPacket.deserialize(serialized)
        
        # Verify all fields match
        assert deserialized_packet.text == original_packet.text
        assert deserialized_packet.mode == original_packet.mode
        assert deserialized_packet.prosody == original_packet.prosody
        assert deserialized_packet.override_emotion == original_packet.override_emotion
        assert deserialized_packet.timestamp == original_packet.timestamp
    
    def test_compact_keys(self):
        """Verify to_dict produces compact keys ('t', 'm', 'p', 'ts') not full names."""
        packet = JanusPacket(
            text="test",
            mode=JanusMode.TEXT_ONLY,
            prosody={'energy': 'Loud', 'pitch': 'Deep'},
            override_emotion="Panicked"
        )
        
        data_dict = packet.to_dict()
        
        # Verify compact keys exist
        assert 't' in data_dict
        assert 'm' in data_dict
        assert 'p' in data_dict
        assert 'ts' in data_dict
        assert 'o' in data_dict  # override_emotion when not "Auto"
        
        # Verify full names are NOT present
        assert 'text' not in data_dict
        assert 'mode' not in data_dict
        assert 'prosody' not in data_dict
        assert 'timestamp' not in data_dict
        assert 'override_emotion' not in data_dict
        
        # Verify values are correct
        assert data_dict['t'] == "test"
        assert data_dict['m'] == 1  # TEXT_ONLY = 1
        assert data_dict['p'] == {'energy': 'Loud', 'pitch': 'Deep'}
        assert data_dict['o'] == "Panicked"
    
    def test_override_emotion(self):
        """Verify 'Auto' is omitted from dict (optimization), but other values are included."""
        # Test with "Auto" (should be omitted)
        packet_auto = JanusPacket(
            text="test",
            mode=JanusMode.SEMANTIC_VOICE,
            prosody={},
            override_emotion="Auto"
        )
        dict_auto = packet_auto.to_dict()
        assert 'o' not in dict_auto  # Should be omitted
        
        # Test with other values (should be included)
        for emotion in ["Relaxed", "Panicked", "Joyful"]:
            packet = JanusPacket(
                text="test",
                mode=JanusMode.SEMANTIC_VOICE,
                prosody={},
                override_emotion=emotion
            )
            dict_result = packet.to_dict()
            assert 'o' in dict_result
            assert dict_result['o'] == emotion
    
    def test_deserialize_garbage(self):
        """Input random bytes, verify it handles error gracefully."""
        # Test with invalid bytes
        garbage_bytes = b'\x00\x01\x02\x03\xff\xfe\xfd'
        
        # Should raise an exception (msgpack will fail to unpack)
        with pytest.raises(Exception):  # Could be ValueError, Exception, etc.
            JanusPacket.deserialize(garbage_bytes)
    
    def test_from_dict_reconstruction(self):
        """Test from_dict correctly reconstructs packet from dictionary."""
        data = {
            't': 'reconstructed text',
            'm': 2,  # MORSE_CODE
            'p': {'energy': 'Quiet', 'pitch': 'Normal'},
            'o': 'Joyful',
            'ts': 9999999999.0
        }
        
        packet = JanusPacket.from_dict(data)
        
        assert packet.text == 'reconstructed text'
        assert packet.mode == JanusMode.MORSE_CODE
        assert packet.prosody == {'energy': 'Quiet', 'pitch': 'Normal'}
        assert packet.override_emotion == 'Joyful'
        assert packet.timestamp == 9999999999.0
    
    def test_timestamp_default(self):
        """Test timestamp defaults to current time if not provided."""
        packet = JanusPacket(
            text="test",
            mode=JanusMode.SEMANTIC_VOICE,
            prosody={}
        )
        
        # Timestamp should be close to current time (within 1 second)
        current_time = time.time()
        assert abs(packet.timestamp - current_time) < 1.0


# ============================================================================
# LinkSimulator Tests
# ============================================================================

class TestLinkSimulator:
    """Tests for LinkSimulator network throttling class."""
    
    @patch('backend.services.link_simulator.socket.socket')
    def test_initialization_defaults(self, mock_socket_class):
        """Verify UDP socket created by default."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        simulator = LinkSimulator(target_ip="127.0.0.1", target_port=5005, use_tcp=False)
        
        # Verify UDP socket (SOCK_DGRAM) was created
        mock_socket_class.assert_called_once_with(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )
        # Should NOT call connect (UDP doesn't connect)
        mock_socket.connect.assert_not_called()
    
    @patch('backend.services.link_simulator.socket.socket')
    def test_tcp_socket_creation(self, mock_socket_class):
        """Verify TCP socket created when use_tcp=True."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        simulator = LinkSimulator(target_ip="127.0.0.1", target_port=5005, use_tcp=True)
        
        # Verify TCP socket (SOCK_STREAM) was created
        mock_socket_class.assert_called_once_with(
            socket.AF_INET,
            socket.SOCK_STREAM
        )
        # Should call connect for TCP
        mock_socket.connect.assert_called_once_with(("127.0.0.1", 5005))
    
    @patch('backend.services.link_simulator.socket.socket')
    def test_ngrok_autodetect(self, mock_socket_class):
        """Init with ngrok host, verify TCP mode is used."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        # Note: ngrok detection happens in sender_main, but we can test LinkSimulator accepts use_tcp=True
        simulator = LinkSimulator(target_ip="0.tcp.ngrok.io", target_port=12345, use_tcp=True)
        
        # Verify TCP socket was created
        mock_socket_class.assert_called_with(
            socket.AF_INET,
            socket.SOCK_STREAM
        )
        mock_socket.connect.assert_called_with(("0.tcp.ngrok.io", 12345))
    
    @patch('backend.services.link_simulator.time.sleep')
    @patch('backend.services.link_simulator.socket.socket')
    def test_throttling_math(self, mock_socket_class, mock_sleep):
        """Call transmit(150 bytes), verify sleep called with ~4.0s (150/37.5)."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        simulator = LinkSimulator(use_tcp=False)
        
        # Transmit 150 bytes
        payload = b'x' * 150
        simulator.transmit(payload)
        
        # Calculate expected delay: 150 / 37.5 = 4.0 seconds
        expected_delay = 150 / BYTES_PER_SECOND
        
        # Verify sleep was called (multiple times for progress bar)
        assert mock_sleep.called
        # Check that total sleep time matches expected delay
        # Progress bar sleeps 20 times, so each sleep should be expected_delay / 20
        expected_sleep_per_tick = expected_delay / 20
        # Verify all sleep calls are approximately correct
        for sleep_call in mock_sleep.call_args_list:
            actual_sleep_time = sleep_call[0][0]
            assert abs(actual_sleep_time - expected_sleep_per_tick) < 0.01
    
    @patch('backend.services.link_simulator.time.sleep')
    @patch('backend.services.link_simulator.socket.socket')
    def test_tcp_framing(self, mock_socket_class, mock_sleep):
        """Init in TCP mode, call transmit(b'hello'), verify sendall received framed payload."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        simulator = LinkSimulator(use_tcp=True)
        
        payload = b'hello'
        simulator.transmit(payload)
        
        # Verify sendall was called (not sendto)
        mock_socket.sendall.assert_called_once()
        mock_socket.sendto.assert_not_called()
        
        # Get the actual data sent
        sent_data = mock_socket.sendall.call_args[0][0]
        
        # Verify it starts with 4-byte length prefix
        assert len(sent_data) == len(payload) + 4
        
        # Extract length prefix (big-endian unsigned int)
        length_prefix = sent_data[:4]
        payload_length = struct.unpack('>I', length_prefix)[0]
        
        assert payload_length == len(payload)  # Should be 5
        assert sent_data[4:] == payload  # Rest should be original payload
    
    @patch('backend.services.link_simulator.time.sleep')
    @patch('backend.services.link_simulator.socket.socket')
    def test_udp_no_framing(self, mock_socket_class, mock_sleep):
        """Init in UDP mode, call transmit, verify sendto received raw bytes."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        simulator = LinkSimulator(target_ip="127.0.0.1", target_port=5005, use_tcp=False)
        
        payload = b'hello world'
        simulator.transmit(payload)
        
        # Verify sendto was called (not sendall)
        mock_socket.sendto.assert_called_once()
        mock_socket.sendall.assert_not_called()
        
        # Get the actual data sent
        sent_data = mock_socket.sendto.call_args[0][0]
        target_address = mock_socket.sendto.call_args[0][1]
        
        # Verify raw bytes (no framing)
        assert sent_data == payload
        assert target_address == ("127.0.0.1", 5005)
    
    @patch('backend.services.link_simulator.socket.socket')
    def test_socket_error_handling(self, mock_socket_class):
        """Mock socket to raise ConnectionRefusedError, verify initialization handles it gracefully."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        # Make connect raise ConnectionRefusedError
        mock_socket.connect.side_effect = ConnectionRefusedError("Connection refused")
        
        # Should not raise exception, just print warning
        simulator = LinkSimulator(target_ip="127.0.0.1", target_port=5005, use_tcp=True)
        
        # Simulator should still be created (socket exists even if connect failed)
        assert simulator.socket is not None
    
    @patch('backend.services.link_simulator.time.sleep')
    @patch('backend.services.link_simulator.socket.socket')
    def test_transmit_error_handling(self, mock_socket_class, mock_sleep):
        """Test transmit handles socket errors gracefully."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        simulator = LinkSimulator(use_tcp=False)
        
        # Make sendto raise an exception
        mock_socket.sendto.side_effect = Exception("Network error")
        
        # Should not raise exception, just print error
        payload = b'test'
        simulator.transmit(payload)  # Should complete without raising
    
    @patch('backend.services.link_simulator.time.sleep')
    @patch('backend.services.link_simulator.socket.socket')
    def test_tcp_framing_length_calculation(self, mock_socket_class, mock_sleep):
        """Verify TCP framing includes header in delay calculation."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket
        
        simulator = LinkSimulator(use_tcp=True)
        
        payload = b'x' * 100  # 100 bytes
        simulator.transmit(payload)
        
        # Total bytes should be 100 (payload) + 4 (header) = 104
        # Expected delay: 104 / 37.5
        expected_delay = 104 / BYTES_PER_SECOND
        expected_sleep_per_tick = expected_delay / 20
        
        # Verify sleep calls match expected delay (accounting for header)
        for sleep_call in mock_sleep.call_args_list:
            actual_sleep_time = sleep_call[0][0]
            assert abs(actual_sleep_time - expected_sleep_per_tick) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

