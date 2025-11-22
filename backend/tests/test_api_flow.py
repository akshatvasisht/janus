import pytest
from fastapi.testclient import TestClient
from backend.server import app
from backend.common import engine_state

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_engine_state():
    """Reset engine state queues before each test to prevent loop binding errors"""
    engine_state.reset_queues()

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

        # 3. Verify State Update
        assert engine_state.control_state.is_streaming is True
        assert engine_state.control_state.mode == "text_only"

def test_websocket_partial_update():
    # Reset state
    engine_state.control_state.is_recording = False
    engine_state.control_state.emotion_override = "auto"

    with client.websocket_connect("/ws/janus") as websocket:
        # Send partial update (only emotion_override)
        websocket.send_json({
            "type": "control",
            "emotion_override": "urgent"
        })

        # Verify only target field changed
        assert engine_state.control_state.emotion_override == "urgent"
        # Should remain False
        assert engine_state.control_state.is_recording is False
