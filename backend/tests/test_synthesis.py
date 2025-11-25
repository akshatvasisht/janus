"""
Test Suite for Phase 4 Synthesizer Service
Tests the synthesizer's routing logic, prompt construction, and audio generation.
"""

import os
import sys
from unittest.mock import MagicMock, Mock, call, mock_open, patch

import numpy as np
import pytest
from fishaudio import FishAudio
from fishaudio.types import ReferenceAudio

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from backend.common.protocol import JanusMode, JanusPacket
from backend.services.synthesizer import Synthesizer

# Define constants locally for testing (in case they're not exported)
SAMPLE_RATE = 44100  # Hz


# ============================================================================
# Synthesizer Initialization Tests
# ============================================================================

@patch('backend.services.synthesizer.FishAudio')
class TestSynthesizerInit:
    """Tests for Synthesizer initialization."""
    
    @patch('backend.services.synthesizer.os.path.exists')
    @patch('backend.services.synthesizer.os.path.getmtime')
    def test_init_loads_reference(self, mock_mtime, mock_exists, mock_client_class):
        """Verify reference audio file is read as bytes when path provided."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Set up mocks for file system operations
        mock_exists.return_value = True
        mock_mtime.return_value = 12345.0
        
        # Mock file content
        fake_audio_bytes = b'fake audio data'
        
        with patch('builtins.open', mock_open(read_data=fake_audio_bytes)):
            synthesizer = Synthesizer(api_key="test_key", reference_audio_path="/fake/path.wav")
            
            # Verify FishAudio client was initialized
            mock_client_class.assert_called_once_with(api_key="test_key")
            
            # Verify reference audio bytes were loaded
            assert synthesizer.reference_audio_bytes == fake_audio_bytes
        
        # Verify file was opened correctly
        with patch('builtins.open', mock_open(read_data=fake_audio_bytes)) as mock_file:
            Synthesizer(api_key="test_key", reference_audio_path="/fake/path.wav")
            mock_file.assert_called_once_with("/fake/path.wav", 'rb')
    
    def test_init_no_reference(self, mock_client_class):
        """Verify synthesizer works without reference audio."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        synthesizer = Synthesizer(api_key="test_key")
        
        # Correct Assertion for Mocked Class Instance
        mock_client_class.assert_called_once_with(api_key="test_key")
        assert synthesizer.reference_audio_bytes is None


# ============================================================================
# Synthesizer Routing Tests
# ============================================================================

class TestSynthesizerRouting:
    """Tests for synthesize() routing logic."""
    
    @patch('backend.services.synthesizer.FishAudio')
    @patch.object(Synthesizer, '_generate_semantic_audio')
    def test_routing_semantic(self, mock_method, mock_client_class):
        """Verify synthesize() routes JanusMode.SEMANTIC_VOICE to _generate_semantic_audio."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_audio_bytes = b'fake semantic audio'
        mock_method.return_value = mock_audio_bytes
        
        synthesizer = Synthesizer(api_key="test_key")
        
        # Create packet with SEMANTIC_VOICE mode
        packet = JanusPacket(
            text="Hello",
            mode=JanusMode.SEMANTIC_VOICE,
            prosody={'energy': 'Normal', 'pitch': 'Normal'}
        )
        
        result = synthesizer.synthesize(packet)
        
        # Verify _generate_semantic_audio was called
        mock_method.assert_called_once_with(packet)
        assert result == mock_audio_bytes
    
    @patch('backend.services.synthesizer.FishAudio')
    @patch.object(Synthesizer, '_generate_fast_tts')
    def test_routing_text_only(self, mock_method, mock_client_class):
        """Verify JanusMode.TEXT_ONLY routes to _generate_fast_tts."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_audio_bytes = b'fake tts audio'
        mock_method.return_value = mock_audio_bytes
        
        synthesizer = Synthesizer(api_key="test_key")
        
        # Create packet with TEXT_ONLY mode
        packet = JanusPacket(
            text="Hello",
            mode=JanusMode.TEXT_ONLY,
            prosody={}
        )
        
        result = synthesizer.synthesize(packet)
        
        # Verify _generate_fast_tts was called
        mock_method.assert_called_once_with("Hello", "Auto")
        assert result == mock_audio_bytes
    
    @patch('backend.services.synthesizer.FishAudio')
    @patch.object(Synthesizer, '_generate_morse_audio')
    def test_routing_morse_code(self, mock_method, mock_client_class):
        """Verify JanusMode.MORSE_CODE routes to _generate_morse_audio."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_audio_bytes = b'fake morse audio'
        mock_method.return_value = mock_audio_bytes
        
        synthesizer = Synthesizer(api_key="test_key")
        
        # Create packet with MORSE_CODE mode
        packet = JanusPacket(
            text="SOS",
            mode=JanusMode.MORSE_CODE,
            prosody={}
        )
        
        result = synthesizer.synthesize(packet)
        
        # Verify _generate_morse_audio was called
        mock_method.assert_called_once_with("SOS")
        assert result == mock_audio_bytes


# ============================================================================
# Prompt Construction Tests
# ============================================================================

class TestPromptConstruction:
    """Tests for emotion prompt construction."""
    
    @patch('backend.services.synthesizer.FishAudio')
    def test_prompt_construction_override(self, mock_client_class):
        """Verify override_emotion creates prompt with parentheses format."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock API response
        mock_audio_result = b'fake audio bytes'
        mock_client.tts.convert.return_value = mock_audio_result
        
        synthesizer = Synthesizer(api_key="test_key")
        
        # Create packet with override emotion
        packet = JanusPacket(
            text="Hello world",
            mode=JanusMode.SEMANTIC_VOICE,
            prosody={'energy': 'Normal', 'pitch': 'Normal'},
            override_emotion="excited"
        )
        
        result = synthesizer._generate_semantic_audio(packet)
        
        # Verify client.tts.convert was called with correct prompt
        mock_client.tts.convert.assert_called_once()
        call_args = mock_client.tts.convert.call_args
        
        # Check that text parameter uses parentheses format (excited) not [excited]
        assert call_args.kwargs['text'].startswith('(excited)')
        assert 'Hello world' in call_args.kwargs['text']
    
    @patch('backend.services.synthesizer.FishAudio')
    def test_prompt_construction_prosody_mapping(self, mock_client_class):
        """Verify prosody mapping creates correct emotion tags."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Mock API response
        mock_audio_result = b'fake audio bytes'
        mock_client.tts.convert.return_value = mock_audio_result
        
        synthesizer = Synthesizer(api_key="test_key")
        
        # Test High pitch + Loud energy -> excited
        packet = JanusPacket(
            text="Test",
            mode=JanusMode.SEMANTIC_VOICE,
            prosody={'energy': 'Loud', 'pitch': 'High'},
            override_emotion="Auto"
        )
        
        result = synthesizer._generate_semantic_audio(packet)
        call_args = mock_client.tts.convert.call_args
        assert call_args.kwargs['text'].startswith('(excited)')
        
        # Test High pitch + Normal energy -> joyful
        packet.prosody = {'energy': 'Normal', 'pitch': 'High'}
        result = synthesizer._generate_semantic_audio(packet)
        call_args = mock_client.tts.convert.call_args
        assert call_args.kwargs['text'].startswith('(joyful)')
        
        # Test Low pitch + Normal energy -> relaxed
        packet.prosody = {'energy': 'Normal', 'pitch': 'Low'}
        result = synthesizer._generate_semantic_audio(packet)
        call_args = mock_client.tts.convert.call_args
        assert call_args.kwargs['text'].startswith('(relaxed)')


# ============================================================================
# Morse Code Generation Tests
# ============================================================================

class TestMorseCodeGeneration:
    """Tests for Morse code audio generation."""
    
    @patch('backend.services.synthesizer.FishAudio')
    def test_morse_code_generation(self, mock_client_class):
        """Verify JanusMode.MORSE_CODE returns bytes and 'SOS' generates correct duration."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        synthesizer = Synthesizer(api_key="test_key")
        
        # Create packet with MORSE_CODE mode
        packet = JanusPacket(
            text="SOS",
            mode=JanusMode.MORSE_CODE,
            prosody={}
        )
        
        result = synthesizer.synthesize(packet)
        
        # Verify result is bytes
        assert isinstance(result, bytes)
        assert len(result) > 0
        
        # Verify API was NOT called (Morse code is local generation)
        mock_client.tts.convert.assert_not_called()
        
        # Verify duration is approximately correct for "SOS"
        # SOS = ... --- ... (3 dots, 3 dashes, 3 dots)
        # Each dot: 0.1s tone + 0.1s silence = 0.2s
        # Each dash: 0.3s tone + 0.1s silence = 0.4s
        # Between letters: 0.3s silence
        # Expected: S(0.1+0.1+0.1+0.1+0.1+0.1+0.3) + O(0.3+0.1+0.3+0.1+0.3+0.1+0.3) + S(0.1+0.1+0.1+0.1+0.1+0.1+0.3)
        # S = 3 dots + 2 silences + letter gap = 3*0.1 + 2*0.1 + 0.3 = 0.8s
        # O = 3 dashes + 2 silences + letter gap = 3*0.3 + 2*0.1 + 0.3 = 1.4s
        # Total ≈ 0.8 + 1.4 + 0.8 = 3.0s
        # At 16000 Hz, 2 bytes per sample: 3.0 * 16000 * 2 = 96000 bytes
        
        audio_samples = len(result) // 2  # int16 = 2 bytes per sample
        duration_seconds = audio_samples / SAMPLE_RATE
        
        # Check duration is roughly correct (allow 20% tolerance)
        assert duration_seconds > 2.0  # At least 2 seconds
        assert duration_seconds < 5.0  # Less than 5 seconds


# ============================================================================
# API Failure Fallback Tests
# ============================================================================

class TestAPIFailureFallback:
    """Tests for API failure fallback logic."""
    
    @patch('backend.services.synthesizer.FishAudio')
    @patch.object(Synthesizer, '_generate_fast_tts')
    def test_api_failure_fallback(self, mock_fallback_method, mock_client_class):
        """Verify fallback to _generate_fast_tts when Fish Audio API raises exception."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Make API raise an exception
        mock_client.tts.convert.side_effect = Exception("API Error")
        
        mock_fallback_audio = b'fallback audio'
        mock_fallback_method.return_value = mock_fallback_audio
        
        synthesizer = Synthesizer(api_key="test_key")
        
        # Create packet with SEMANTIC_VOICE mode
        packet = JanusPacket(
            text="Hello",
            mode=JanusMode.SEMANTIC_VOICE,
            prosody={'energy': 'Normal', 'pitch': 'Normal'}
        )
        
        result = synthesizer._generate_semantic_audio(packet)
        
        # Verify fallback was called
        mock_fallback_method.assert_called_once_with("Hello", "Auto")
        assert result == mock_fallback_audio

