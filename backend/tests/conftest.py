"""
Centralized pytest configuration and fixtures.

Provides global fixtures for hardware mocking and state management that apply
to all tests automatically, eliminating the need for repetitive mocking code.
"""

import os

if os.getenv("ENABLE_QWEN3_TTS_TESTS"):
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

import numpy as np
import pytest

from backend.api.types import EmotionOverride, JanusMode
from backend.common import engine_state


def pytest_configure(config):
    """Register filterwarnings for known third-party deprecations (torch, audioread)."""
    config.addinivalue_line(
        "filterwarnings",
        "ignore::DeprecationWarning:torch.jit._script",
    )
    config.addinivalue_line(
        "filterwarnings",
        "ignore::DeprecationWarning:audioread.rawread",
    )


class MockAudioService:
    """
    Mock AudioService that replaces real hardware with controllable test doubles.
    
    Provides the same interface as AudioService but reads from configurable
    patterns (defaults to zeros) and captures all written audio bytes for test
    assertions instead of playing to speakers. Used by the global mock_audio_service
    fixture to eliminate hardware dependencies in tests.
    """
    
    def __init__(self):
        """Initialize the mock audio service."""
        self.SAMPLE_RATE = 44100
        self.CHUNK_SIZE = 512
        self.CHANNELS = 1
        self.FORMAT = None  # Not used in mock
        
        # Storage for written audio chunks
        self.written_audio_chunks: list[bytes] = []
        
        # Input pattern: list of numpy arrays (float32) to return from read_chunk()
        # When None or exhausted, returns zeros
        self._input_pattern: list[np.ndarray] | None = None
        self._pattern_index: int = 0
        
        # Track if service was closed
        self._closed = False
    
    def read_chunk(self) -> np.ndarray:
        """
        Read a chunk of audio data.
        
        Returns:
            np.ndarray: Audio chunk as float32 array, normalized [-1.0, 1.0]
        """
        if self._closed:
            return np.zeros(self.CHUNK_SIZE, dtype=np.float32)
        
        # If pattern is set and not exhausted, return next chunk
        if self._input_pattern is not None and self._pattern_index < len(self._input_pattern):
            chunk = self._input_pattern[self._pattern_index]
            self._pattern_index += 1
            # Ensure chunk is correct size
            if len(chunk) != self.CHUNK_SIZE:
                # Pad or truncate to match CHUNK_SIZE
                if len(chunk) < self.CHUNK_SIZE:
                    chunk = np.pad(chunk, (0, self.CHUNK_SIZE - len(chunk)), mode='constant')
                else:
                    chunk = chunk[:self.CHUNK_SIZE]
            return chunk.astype(np.float32)
        
        # Default: return zeros (silence)
        return np.zeros(self.CHUNK_SIZE, dtype=np.float32)
    
    def write_chunk(self, audio_data: bytes | np.ndarray | None) -> None:
        """
        Write audio data (captures instead of playing).
        
        Args:
            audio_data: Audio data as bytes or numpy array
        """
        if self._closed or audio_data is None:
            return
        
        # Convert to bytes if needed
        if isinstance(audio_data, np.ndarray):
            if audio_data.dtype == np.float32:
                audio_data = (audio_data * 32768.0).astype(np.int16)
            elif audio_data.dtype != np.int16:
                audio_data = audio_data.astype(np.int16)
            audio_bytes = audio_data.tobytes()
        else:
            audio_bytes = audio_data
        
        # Store written audio for test assertions
        self.written_audio_chunks.append(audio_bytes)
    
    def close(self) -> None:
        """Mark service as closed."""
        self._closed = True
    
    def set_input_pattern(self, pattern: list[np.ndarray]) -> None:
        """
        Set the input pattern for read_chunk().
        
        Args:
            pattern: List of numpy arrays (float32) to return sequentially.
                    Each array should be CHUNK_SIZE samples.
        """
        self._input_pattern = pattern
        self._pattern_index = 0
    
    def reset(self) -> None:
        """Reset the mock state (clears written chunks and pattern)."""
        self.written_audio_chunks.clear()
        self._input_pattern = None
        self._pattern_index = 0
        self._closed = False


# Global instance that will be shared across tests
# This is set by the fixture and can be accessed by tests that need it
_global_mock_audio_service: MockAudioService | None = None


@pytest.fixture(autouse=True)
def mock_audio_service(monkeypatch):
    """
    Global fixture that replaces AudioService with MockAudioService.
    
    This fixture automatically applies to all tests, eliminating the need
    for manual @patch decorators in individual test files.
    
    Tests can inject this fixture to access the mock instance directly.
    """
    global _global_mock_audio_service
    
    # Create a new mock instance for each test
    mock_service = MockAudioService()
    _global_mock_audio_service = mock_service
    
    # Patch AudioService class to return our mock
    def mock_audio_service_factory(*args, **kwargs):
        """Factory function that returns the mock instance."""
        return mock_service
    
    # Patch at the module level where AudioService is defined
    monkeypatch.setattr('backend.services.audio_io.AudioService', mock_audio_service_factory)
    
    # Also patch common import paths
    monkeypatch.setattr('backend.server.AudioService', mock_audio_service_factory)
    monkeypatch.setattr('backend.scripts.sender_main.AudioService', mock_audio_service_factory)
    monkeypatch.setattr('backend.scripts.receiver_main.AudioService', mock_audio_service_factory)
    monkeypatch.setattr('backend.services.engine.AudioService', mock_audio_service_factory)
    
    yield mock_service
    
    # Cleanup
    mock_service.reset()
    _global_mock_audio_service = None


@pytest.fixture(autouse=True)
def reset_engine_state():
    """
    Reset engine_state queues and control_state before each test.
    
    Ensures test isolation by clearing any state left over from previous tests.
    """
    # Reset queues
    engine_state.reset_queues()
    
    # Reset control state to defaults
    state = engine_state.control_state
    state.mode = JanusMode.SEMANTIC
    state.is_streaming = False
    state.is_recording = False
    state.emotion_override = EmotionOverride.AUTO
    state.ducking_enabled = True
    state.ducking_level = 0.25
    state.is_talking = False
