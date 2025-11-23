import pytest

from unittest.mock import MagicMock, patch, call

import queue

import threading

import socket

from backend.services.engine import recv_exact, playback_worker, receiver_loop


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

