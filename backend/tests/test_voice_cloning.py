"""
Test Suite for Voice Cloning Features

Tests:
- /api/voice/verify endpoint behavior (unchanged by local TTS backend).
- Synthesizer integration with ModelManager for reference audio paths.
"""

import io
import os
import sys
from unittest.mock import MagicMock, mock_open, patch

import pytest
from fastapi.testclient import TestClient

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from backend.server import app
from backend.services.synthesizer import Synthesizer


# ============================================================================
# API Endpoint Tests
# ============================================================================


class TestVoiceVerificationAPI:
    """Tests for /api/voice/verify endpoint."""

    @patch("backend.api.endpoints.Transcriber")
    @patch("builtins.open", new_callable=mock_open)
    def test_verify_voice_success(self, mock_file_open, mock_transcriber_class) -> None:
        """Test successful voice verification with matching transcript."""
        # Setup mock transcriber
        mock_transcriber_instance = MagicMock()
        mock_transcriber_instance.transcribe_file.return_value = (
            "The quick brown fox jumps over the lazy dog."
        )
        mock_transcriber_class.return_value = mock_transcriber_instance

        client = TestClient(app)

        # Create dummy file upload
        file_content = b"fake audio content"
        file_obj = io.BytesIO(file_content)

        response = client.post(
            "/api/voice/verify",
            files={"audio_file": ("filename.wav", file_obj, "audio/wav")},
        )

        assert response.status_code == 200
        assert response.json() == {"status": "verified"}
        mock_transcriber_instance.transcribe_file.assert_called_once()

    @patch("backend.api.endpoints.Transcriber")
    @patch("builtins.open", new_callable=mock_open)
    def test_verify_voice_failure(self, mock_file_open, mock_transcriber_class) -> None:
        """Test failed voice verification with non-matching transcript."""
        mock_transcriber_instance = MagicMock()
        mock_transcriber_instance.transcribe_file.return_value = "Something completely different."
        mock_transcriber_class.return_value = mock_transcriber_instance

        client = TestClient(app)

        file_content = b"fake audio content"
        file_obj = io.BytesIO(file_content)

        response = client.post(
            "/api/voice/verify",
            files={"audio_file": ("filename.wav", file_obj, "audio/wav")},
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "failed",
            "transcript": "Something completely different.",
        }
        mock_transcriber_instance.transcribe_file.assert_called_once()


# ============================================================================
# Synthesizer / ModelManager Integration Tests
# ============================================================================


@patch("backend.services.synthesizer.ModelManager")
def test_synthesizer_uses_default_enrollment_for_voice_cloning(mock_mm: MagicMock) -> None:
    """Synthesizer should default to backend/assets/enrollment.wav when no path provided."""
    synth = Synthesizer()

    assert "backend" in synth.reference_audio_path
    assert synth.reference_audio_path.endswith(os.path.join("assets", "enrollment.wav"))

    mock_mm.assert_called_once()
    _, kwargs = mock_mm.call_args
    assert kwargs.get("ref_audio_path") == synth.reference_audio_path


@patch("backend.services.synthesizer.ModelManager")
def test_synthesizer_respects_reference_audio_env_override(
    mock_mm: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REFERENCE_AUDIO_PATH (or explicit constructor path) should be forwarded to ModelManager."""
    custom_path = "/tmp/custom_enrollment.wav"
    synth = Synthesizer(reference_audio_path=custom_path)

    assert synth.reference_audio_path == custom_path

    mock_mm.assert_called_once()
    _, kwargs = mock_mm.call_args
    assert kwargs.get("ref_audio_path") == custom_path

