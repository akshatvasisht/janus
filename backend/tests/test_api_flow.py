import time

import pytest
from fastapi.testclient import TestClient

from backend.api.types import EmotionOverride
from backend.common import engine_state
from backend.server import app

client = TestClient(app)

# Note: mock_audio_service and reset_engine_state fixtures are now provided
# globally by backend/tests/conftest.py, so no need for local fixtures here.

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_websocket_control_flow():
    # Reset state before test
    engine_state.control_state.is_streaming = False
    engine_state.control_state.mode = "semantic"

    with client.websocket_connect("/ws/janus") as websocket:
        # 1. Initial State
        assert engine_state.control_state.is_streaming is False

        # 2. Send Control Message
        websocket.send_json({
            "type": "control",
            "is_streaming": True,
            "mode": "text_only"
        })

        # Wait for async message processing to complete
        time.sleep(0.1)

        # 3. Verify State Update
        assert engine_state.control_state.is_streaming is True
        assert engine_state.control_state.mode == "text_only"

def test_websocket_partial_update():
    # Reset state
    engine_state.control_state.is_recording = False
    engine_state.control_state.emotion_override = EmotionOverride.AUTO

    with client.websocket_connect("/ws/janus") as websocket:
        # Send partial update (only emotion_override)
        websocket.send_json({
            "type": "control",
            "emotion_override": "panicked"
        })

        # Wait for async message processing to complete
        time.sleep(0.1)

        # Verify only target field changed
        assert engine_state.control_state.emotion_override == EmotionOverride.PANICKED
        # Should remain False
        assert engine_state.control_state.is_recording is False

def test_websocket_morse_mode():
    """Verify switching to Morse mode works via WebSocket control message."""
    # Reset state to default
    engine_state.control_state.mode = "semantic"

    with client.websocket_connect("/ws/janus") as websocket:
        # Send Control Message with "morse" mode
        websocket.send_json({
            "type": "control",
            "mode": "morse"
        })

        # Wait for async message processing to complete
        time.sleep(0.1)

        # Verify State Update
        # This confirms api.types.JanusMode.MORSE ("morse") is accepted and updated in the engine state
        assert engine_state.control_state.mode == "morse"
