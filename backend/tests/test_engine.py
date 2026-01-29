import queue
import socket
import threading
from unittest.mock import MagicMock

import numpy as np
import pytest

from backend.common import engine_state
from backend.services.engine import (
    apply_ducking_if_needed,
    playback_worker,
    recv_exact,
    receiver_loop,
)


def test_recv_exact_success():
    """Verify it reads exactly N bytes even if socket chunks them."""
    mock_sock = MagicMock()
    # Simulate receiving 2 bytes, then 2 bytes for a request of 4 bytes
    mock_sock.recv.side_effect = [b'AB', b'CD']
    result = recv_exact(mock_sock, 4)
    assert result == b'ABCD'


def test_recv_exact_closed():
    """Verify it returns None on connection close."""
    mock_sock = MagicMock()
    mock_sock.recv.return_value = b''
    result = recv_exact(mock_sock, 4)
    assert result is None


def test_playback_worker():
    """Verify audio bytes are pulled from queue and written to service."""
    mock_audio = MagicMock()
    q = queue.Queue()
    stop_event = threading.Event()
    
    q.put(b'audio_data')
    
    # Run worker in a thread that we stop immediately
    def stop_soon():
        import time
        time.sleep(0.1)
        stop_event.set()
        
    threading.Thread(target=stop_soon).start()
    playback_worker(mock_audio, q, stop_event)
    
    mock_audio.write_chunk.assert_called_with(b'audio_data')


def test_apply_ducking_if_needed_no_ducking_when_disabled_or_not_talking(reset_ducking_state):
    """Ducking should not modify audio when disabled or when user not talking."""
    state = reset_ducking_state
    original = np.array([1000, -2000, 3000], dtype=np.int16)
    audio_bytes = original.tobytes()

    # Case 1: ducking disabled, talking
    state.ducking_enabled = False
    state.is_talking = True
    out1 = apply_ducking_if_needed(audio_bytes, state)
    assert out1 == audio_bytes

    # Case 2: ducking enabled, not talking
    state.ducking_enabled = True
    state.is_talking = False
    out2 = apply_ducking_if_needed(audio_bytes, state)
    assert out2 == audio_bytes


def test_apply_ducking_if_needed_applies_gain_when_talking(reset_ducking_state):
    """Ducking should scale int16 PCM amplitudes when enabled and talking."""
    state = reset_ducking_state
    state.ducking_enabled = True
    state.is_talking = True
    state.ducking_level = 0.5

    original = np.array([1000, -2000, 0, 32767, -32768], dtype=np.int16)
    audio_bytes = original.tobytes()

    out_bytes = apply_ducking_if_needed(audio_bytes, state)
    out = np.frombuffer(out_bytes, dtype=np.int16)

    expected = np.clip(original.astype(np.float32) * 0.5, -32768, 32767).astype(np.int16)
    assert np.allclose(out, expected, atol=1)


@pytest.fixture
def reset_ducking_state():
    """Fixture to reset ducking-related control state between tests."""
    state = engine_state.control_state
    original_ducking_enabled = getattr(state, "ducking_enabled", True)
    original_ducking_level = getattr(state, "ducking_level", 0.25)
    original_is_talking = getattr(state, "is_talking", False)

    try:
        yield state
    finally:
        state.ducking_enabled = original_ducking_enabled
        state.ducking_level = original_ducking_level
        state.is_talking = original_is_talking

