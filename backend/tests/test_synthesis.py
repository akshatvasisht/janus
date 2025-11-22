"""
Test Suite for Phase 4 Synthesizer Service
Tests the synthesizer's routing logic, prompt construction, and audio generation.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call, mock_open
import sys
import os
import numpy as np

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.synthesizer import Synthesizer, SAMPLE_RATE
from common.protocol import JanusPacket, JanusMode


# ============================================================================
# Synthesizer Initialization Tests
# ============================================================================

class TestSynthesizerInit:
    """Tests for Synthesizer initialization."""
    
    @patch('services.synthesizer.Session')
    def test_init_loads_reference(self, mock_session_class):
        """Verify reference audio file is read as bytes when path provided."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        # Mock file content
        fake_audio_bytes = b'fake audio data'
        
        with patch('builtins.open', mock_open(read_data=fake_audio_bytes)):
            synthesizer = Synthesizer(api_key="test_key", reference_audio_path="/fake/path.wav")
            
            # Verify Session was initialized
            mock_session_class.assert_called_once_with(api_key="test_key")
            
            # Verify reference audio bytes were loaded
            assert synthesizer.reference_audio_bytes == fake_audio_bytes
        
        # Verify file was opened correctly
        with patch('builtins.open', mock_open(read_data=fake_audio_bytes)) as mock_file:
            Synthesizer(api_key="test_key", reference_audio_path="/fake/path.wav")
            mock_file.assert_called_once_with("/fake/path.wav", 'rb')
    
    @patch('services.synthesizer.Session')
    def test_init_no_reference(self, mock_session_class):
        """Verify synthesizer works without reference audio."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        synthesizer = Synthesizer(api_key="test_key")
        
        assert synthesizer.reference_audio_bytes is None
        assert synthesizer.session == mock_session


# ============================================================================
# Synthesizer Routing Tests
# ============================================================================

class TestSynthesizerRouting:
    """Tests for synthesize() routing logic."""
    
    @patch('services.synthesizer.Session')
    def test_routing_semantic(self, mock_session_class):
        """Verify synthesize() routes JanusMode.SEMANTIC_VOICE to _generate_semantic_audio."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        synthesizer = Synthesizer(api_key="test_key")
        
        # Mock the semantic audio generation method
        mock_audio_bytes = b'fake semantic audio'
        synthesizer._generate_semantic_audio = Mock(return_value=mock_audio_bytes)
        
        # Create packet with SEMANTIC_VOICE mode
        packet = JanusPacket(
            text="Hello",
            mode=JanusMode.SEMANTIC_VOICE,
            prosody={'energy': 'Normal', 'pitch': 'Normal'}
        )
        
        result = synthesizer.synthesize(packet)
        
        # Verify _generate_semantic_audio was called
        synthesizer._generate_semantic_audio.assert_called_once_with(packet)
        assert result == mock_audio_bytes
    
    @patch('services.synthesizer.Session')
    def test_routing_text_only(self, mock_session_class):
        """Verify JanusMode.TEXT_ONLY routes to _generate_fast_tts."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        synthesizer = Synthesizer(api_key="test_key")
        
        # Mock the fast TTS method
        mock_audio_bytes = b'fake tts audio'
        synthesizer._generate_fast_tts = Mock(return_value=mock_audio_bytes)
        
        # Create packet with TEXT_ONLY mode
        packet = JanusPacket(
            text="Hello",
            mode=JanusMode.TEXT_ONLY,
            prosody={}
        )
        
        result = synthesizer.synthesize(packet)
        
        # Verify _generate_fast_tts was called
        synthesizer._generate_fast_tts.assert_called_once_with("Hello")
        assert result == mock_audio_bytes
    
    @patch('services.synthesizer.Session')
    def test_routing_morse_code(self, mock_session_class):
        """Verify JanusMode.MORSE_CODE routes to _generate_morse_audio."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        synthesizer = Synthesizer(api_key="test_key")
        
        # Mock the morse code method
        mock_audio_bytes = b'fake morse audio'
        synthesizer._generate_morse_audio = Mock(return_value=mock_audio_bytes)
        
        # Create packet with MORSE_CODE mode
        packet = JanusPacket(
            text="SOS",
            mode=JanusMode.MORSE_CODE,
            prosody={}
        )
        
        result = synthesizer.synthesize(packet)
        
        # Verify _generate_morse_audio was called
        synthesizer._generate_morse_audio.assert_called_once_with("SOS")
        assert result == mock_audio_bytes


# ============================================================================
# Prompt Construction Tests
# ============================================================================

class TestPromptConstruction:
    """Tests for emotion prompt construction."""
    
    @patch('services.synthesizer.Session')
    @patch('services.synthesizer.TTSRequest')
    @patch('services.synthesizer.ReferenceAudio')
    def test_prompt_construction(self, mock_ref_audio_class, mock_tts_request_class, mock_session_class):
        """Verify override_emotion='Excited' creates prompt starting with '[Excited]'."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        # Mock API response
        mock_audio_result = b'fake audio bytes'
        mock_session.synthesize.return_value = mock_audio_result
        
        synthesizer = Synthesizer(api_key="test_key")
        
        # Create packet with override emotion
        packet = JanusPacket(
            text="Hello world",
            mode=JanusMode.SEMANTIC_VOICE,
            prosody={'energy': 'Normal', 'pitch': 'Normal'},
            override_emotion="Excited"
        )
        
        result = synthesizer._generate_semantic_audio(packet)
        
        # Verify TTSRequest was created with correct prompt
        mock_tts_request_class.assert_called_once()
        call_args = mock_tts_request_class.call_args
        
        # Check that text parameter starts with [Excited]
        assert call_args.kwargs['text'].startswith('[Excited]')
        assert 'Hello world' in call_args.kwargs['text']


# ============================================================================
# Morse Code Generation Tests
# ============================================================================

class TestMorseCodeGeneration:
    """Tests for Morse code audio generation."""
    
    @patch('services.synthesizer.Session')
    def test_morse_code_generation(self, mock_session_class):
        """Verify JanusMode.MORSE_CODE returns bytes and 'SOS' generates correct duration."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
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
        mock_session.synthesize.assert_not_called()
        
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
    
    @patch('services.synthesizer.Session')
    @patch('services.synthesizer.TTSRequest')
    @patch('services.synthesizer.ReferenceAudio')
    def test_api_failure_fallback(self, mock_ref_audio_class, mock_tts_request_class, mock_session_class):
        """Verify fallback to _generate_fast_tts when Fish Audio API raises exception."""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        # Make API raise an exception
        mock_session.synthesize.side_effect = Exception("API Error")
        
        synthesizer = Synthesizer(api_key="test_key")
        
        # Mock the fast TTS fallback
        mock_fallback_audio = b'fallback audio'
        synthesizer._generate_fast_tts = Mock(return_value=mock_fallback_audio)
        
        # Create packet with SEMANTIC_VOICE mode
        packet = JanusPacket(
            text="Hello",
            mode=JanusMode.SEMANTIC_VOICE,
            prosody={'energy': 'Normal', 'pitch': 'Normal'}
        )
        
        result = synthesizer._generate_semantic_audio(packet)
        
        # Verify fallback was called
        synthesizer._generate_fast_tts.assert_called_once_with("Hello")
        assert result == mock_fallback_audio

