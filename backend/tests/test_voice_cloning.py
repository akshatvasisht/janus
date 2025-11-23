"""
Test Suite for Voice Cloning Features
Tests the voice verification API endpoint and Synthesizer hot-reload functionality.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
import sys
import os
import io

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from fastapi.testclient import TestClient
from backend.server import app
from backend.services.synthesizer import Synthesizer


# ============================================================================
# API Endpoint Tests
# ============================================================================

class TestVoiceVerificationAPI:
    """Tests for /api/voice/verify endpoint."""
    
    @patch('backend.api.endpoints.Transcriber')
    @patch('builtins.open', new_callable=mock_open)
    def test_verify_voice_success(self, mock_file_open, mock_transcriber_class):
        """Test successful voice verification with matching transcript."""
        # Setup mock transcriber
        mock_transcriber_instance = MagicMock()
        mock_transcriber_instance.transcribe_file.return_value = "The quick brown fox jumps over the lazy dog."
        mock_transcriber_class.return_value = mock_transcriber_instance
        
        # Create TestClient
        client = TestClient(app)
        
        # Create dummy file upload
        file_content = b"fake audio content"
        file_obj = io.BytesIO(file_content)
        
        # Make POST request
        response = client.post(
            "/api/voice/verify",
            files={"audio_file": ("filename.wav", file_obj, "audio/wav")}
        )
        
        # Assertions
        assert response.status_code == 200
        assert response.json() == {"status": "verified"}
        
        # Verify transcriber was called
        mock_transcriber_instance.transcribe_file.assert_called_once()
    
    @patch('backend.api.endpoints.Transcriber')
    @patch('builtins.open', new_callable=mock_open)
    def test_verify_voice_failure(self, mock_file_open, mock_transcriber_class):
        """Test failed voice verification with non-matching transcript."""
        # Setup mock transcriber
        mock_transcriber_instance = MagicMock()
        mock_transcriber_instance.transcribe_file.return_value = "Something completely different."
        mock_transcriber_class.return_value = mock_transcriber_instance
        
        # Create TestClient
        client = TestClient(app)
        
        # Create dummy file upload
        file_content = b"fake audio content"
        file_obj = io.BytesIO(file_content)
        
        # Make POST request
        response = client.post(
            "/api/voice/verify",
            files={"audio_file": ("filename.wav", file_obj, "audio/wav")}
        )
        
        # Assertions
        assert response.status_code == 200
        assert response.json() == {
            "status": "failed",
            "transcript": "Something completely different."
        }
        
        # Verify transcriber was called
        mock_transcriber_instance.transcribe_file.assert_called_once()


# ============================================================================
# Synthesizer Hot-Reload Tests
# ============================================================================

@patch('backend.services.synthesizer.FishAudio')
class TestSynthesizerHotReload:
    """Tests for Synthesizer hot-reload functionality."""
    
    @patch('backend.services.synthesizer.os.path.getmtime')
    @patch('backend.services.synthesizer.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_hot_reload_trigger(self, mock_file_open, mock_exists, mock_getmtime, mock_client_class):
        """Test that hot-reload correctly detects file changes and caches reads."""
        # Setup mock FishAudio client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Setup mock file system operations
        mock_exists.return_value = True
        
        # Create mock file content
        fake_audio_bytes = b'fake audio data'
        mock_file_open.return_value.read.return_value = fake_audio_bytes
        
        # Set initial mtime for first load
        mock_getmtime.return_value = 100.0
        
        # Initialize Synthesizer with explicit path to avoid real path resolution
        synthesizer = Synthesizer(api_key="test_key", reference_audio_path="dummy.wav")
        
        # Verify initial load happened (from __init__)
        # Reset mocks to track only subsequent calls
        initial_open_calls = mock_file_open.call_count
        assert initial_open_calls >= 1, "File should be loaded during initialization"
        
        # Reset mocks to track only new calls from here
        mock_file_open.reset_mock()
        mock_getmtime.reset_mock()
        
        # Step 1: Call _check_and_reload_reference_audio with same timestamp (100.0)
        # Since mtime matches, it should NOT reload (caching works)
        mock_getmtime.return_value = 100.0
        
        synthesizer._check_and_reload_reference_audio()
        
        # Verify file was NOT re-read (caching works)
        assert mock_file_open.call_count == 0, "File should not be re-read when mtime hasn't changed"
        # Verify getmtime was called to check
        assert mock_getmtime.call_count >= 1
        
        # Step 2: Update getmtime to return 200.0 and call again - should re-read (hot-reload works)
        mock_file_open.reset_mock()
        mock_getmtime.reset_mock()
        mock_getmtime.return_value = 200.0
        
        synthesizer._check_and_reload_reference_audio()
        
        # Verify file WAS re-read (hot-reload works)
        assert mock_file_open.call_count >= 1, "File should be re-read when mtime changes"
        # Verify getmtime was called to check for changes
        assert mock_getmtime.call_count >= 1

