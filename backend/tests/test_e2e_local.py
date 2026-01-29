"""
End-to-End Loopback Test Suite

Tests the complete Sender→Receiver pipeline in memory without physical hardware.
Validates that multiple conversation turns work correctly, catching deadlock bugs.
"""

import os
import struct
import threading
import time
from typing import Any

import numpy as np
import pytest

from backend.common.protocol import JanusMode, JanusPacket
from backend.services.prosody import ProsodyExtractor
from backend.services.synthesizer import Synthesizer
from backend.services.transcriber import Transcriber
from backend.services.vad import VoiceActivityDetector


# ============================================================================
# Mock Classes for External Dependencies
# ============================================================================

class MockTranscriber:
    """Mock Transcriber that returns predictable text."""
    
    def __init__(self, *args, **kwargs):
        """Initialize mock transcriber."""
        self._call_count = 0
    
    def transcribe_buffer(self, audio_buffer: Any) -> str:
        """
        Return predictable text based on call count.
        
        Args:
            audio_buffer: Audio buffer (ignored in mock)
        
        Returns:
            str: Predictable transcription text
        """
        self._call_count += 1
        return f"test message {self._call_count}"


class MockSynthesizer:
    """Mock Synthesizer that returns valid WAV bytes."""
    
    def __init__(self, *args, **kwargs):
        """Initialize mock synthesizer."""
        self._call_count = 0
    
    def synthesize(self, packet: JanusPacket) -> bytes:
        """
        Generate synthetic WAV bytes.
        
        Args:
            packet: JanusPacket to synthesize
        
        Returns:
            bytes: Valid WAV file bytes
        """
        self._call_count += 1
        
        # Generate synthetic sine wave audio (440Hz A4 note, 0.5s duration)
        sample_rate = 44100
        duration = 0.5
        frequency = 440.0
        
        num_samples = int(sample_rate * duration)
        t = np.linspace(0, duration, num_samples, dtype=np.float32)
        audio_data = 0.3 * np.sin(2 * np.pi * frequency * t, dtype=np.float32)
        
        # Convert to int16 PCM
        audio_int16 = (audio_data * 32768.0).astype(np.int16)
        
        # Create valid WAV header following RIFF format (RIFF header + fmt chunk + data chunk)
        data_size = len(audio_int16) * 2  # 2 bytes per sample for int16 PCM
        file_size = 36 + data_size
        
        wav_header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',  # Format string
            b'RIFF',                # ChunkID
            file_size,              # ChunkSize
            b'WAVE',                # Format
            b'fmt ',                # Subchunk1ID
            16,                     # Subchunk1Size (PCM)
            1,                      # AudioFormat (PCM)
            1,                      # NumChannels (mono)
            sample_rate,            # SampleRate
            sample_rate * 2,        # ByteRate
            2,                      # BlockAlign
            16,                     # BitsPerSample
            b'data',                # Subchunk2ID
            data_size               # Subchunk2Size
        )
        
        # Combine header + audio data
        wav_bytes = wav_header + audio_int16.tobytes()
        
        return wav_bytes


class MockVAD:
    """Mock VAD that returns True for speech, False for silence based on audio amplitude."""
    
    def __init__(self, *args, **kwargs):
        """Initialize mock VAD."""
        self.threshold = 0.01  # Amplitude threshold for speech detection
    
    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """
        Detect speech based on audio amplitude.
        
        Args:
            audio_chunk: Audio chunk as numpy array
        
        Returns:
            bool: True if speech detected, False otherwise
        """
        # Simple amplitude-based detection
        max_amplitude = np.max(np.abs(audio_chunk))
        return max_amplitude > self.threshold
    
    def reset(self) -> None:
        """Reset VAD state (no-op for mock)."""
        pass


class MockProsodyExtractor:
    """Mock ProsodyExtractor that returns default prosody values."""
    
    def __init__(self, *args, **kwargs):
        """Initialize mock prosody extractor."""
        pass
    
    def analyze_buffer(self, audio_buffer: Any) -> dict[str, str]:
        """
        Return default prosody values.
        
        Args:
            audio_buffer: Audio buffer (ignored in mock)
        
        Returns:
            dict: Prosody metadata with 'energy' and 'pitch' keys
        """
        return {'energy': 'Normal', 'pitch': 'Normal'}


# ============================================================================
# Synthetic Audio Pattern Generator
# ============================================================================

def generate_speech_pattern(
    duration_seconds: float = 2.0,
    sample_rate: int = 44100,
    chunk_size: int = 512,
    frequency: float = 440.0,
    amplitude: float = 0.5
) -> list[np.ndarray]:
    """
    Generate a pattern of audio chunks simulating speech.
    
    Args:
        duration_seconds: Duration of speech in seconds
        sample_rate: Sample rate in Hz
        chunk_size: Number of samples per chunk
        frequency: Frequency of sine wave in Hz
        amplitude: Amplitude of sine wave (0.0 to 1.0)
    
    Returns:
        list[np.ndarray]: List of audio chunks as float32 arrays
    """
    total_samples = int(sample_rate * duration_seconds)
    num_chunks = (total_samples + chunk_size - 1) // chunk_size  # Ceiling division
    
    chunks = []
    for i in range(num_chunks):
        start_sample = i * chunk_size
        end_sample = min(start_sample + chunk_size, total_samples)
        num_samples_in_chunk = end_sample - start_sample
        
        if num_samples_in_chunk == 0:
            break
        
        # Generate sine wave
        t = np.linspace(
            start_sample / sample_rate,
            end_sample / sample_rate,
            num_samples_in_chunk,
            dtype=np.float32
        )
        chunk = amplitude * np.sin(2 * np.pi * frequency * t, dtype=np.float32)
        chunks.append(chunk)
    
    return chunks


def generate_silence_pattern(
    duration_seconds: float = 1.0,
    sample_rate: int = 44100,
    chunk_size: int = 512
) -> list[np.ndarray]:
    """
    Generate a pattern of silence chunks.
    
    Args:
        duration_seconds: Duration of silence in seconds
        sample_rate: Sample rate in Hz
        chunk_size: Number of samples per chunk
    
    Returns:
        list[np.ndarray]: List of zero-filled audio chunks
    """
    total_samples = int(sample_rate * duration_seconds)
    num_chunks = (total_samples + chunk_size - 1) // chunk_size
    
    chunks = []
    for _ in range(num_chunks):
        chunk = np.zeros(chunk_size, dtype=np.float32)
        chunks.append(chunk)
    
    return chunks


def generate_conversation_pattern(num_turns: int = 2) -> list[np.ndarray]:
    """
    Generate a pattern simulating multiple conversation turns.
    
    Each turn consists of:
    - Speech phase (2 seconds of sine wave)
    - Silence phase (1 second of zeros to trigger VAD threshold)
    
    Args:
        num_turns: Number of conversation turns to generate
    
    Returns:
        list[np.ndarray]: Combined pattern of speech and silence chunks
    """
    pattern = []
    
    for turn in range(num_turns):
        # Speech phase
        speech_chunks = generate_speech_pattern(
            duration_seconds=2.0,
            frequency=440.0,
            amplitude=0.5
        )
        pattern.extend(speech_chunks)
        
        # Silence phase (must exceed SILENCE_THRESHOLD_CHUNKS = 16)
        silence_chunks = generate_silence_pattern(duration_seconds=1.0)
        pattern.extend(silence_chunks)
    
    return pattern


# ============================================================================
# E2E Test
# ============================================================================

@pytest.mark.timeout(30)
def test_e2e_loopback_multiple_turns(monkeypatch, mock_audio_service):
    """
    E2E test: Sender and Receiver communicate over localhost with multiple turns.
    
    Validates the complete pipeline works end-to-end, that multiple conversation
    turns are processed correctly, and that no deadlock occurs after the first
    transmission. Uses synthetic audio patterns and real network sockets to test
    the full Sender→Receiver pipeline without physical hardware.
    
    Args:
        monkeypatch: Pytest fixture for patching modules and environment variables.
        mock_audio_service: Mock AudioService fixture from conftest.py.
    """
    # Setup: Patch external dependencies
    monkeypatch.setattr('backend.services.transcriber.Transcriber', MockTranscriber)
    monkeypatch.setattr('backend.services.synthesizer.Synthesizer', MockSynthesizer)
    monkeypatch.setattr('backend.services.vad.VoiceActivityDetector', MockVAD)
    monkeypatch.setattr('backend.services.prosody.ProsodyExtractor', MockProsodyExtractor)
    
    # Also patch in scripts modules
    monkeypatch.setattr('backend.scripts.sender_main.Transcriber', MockTranscriber)
    monkeypatch.setattr('backend.scripts.sender_main.VoiceActivityDetector', MockVAD)
    monkeypatch.setattr('backend.scripts.sender_main.ProsodyExtractor', MockProsodyExtractor)
    monkeypatch.setattr('backend.scripts.receiver_main.Synthesizer', MockSynthesizer)
    
    # Set environment variables for network configuration
    test_port = "5006"  # Use different port to avoid conflicts
    monkeypatch.setenv("TARGET_IP", "127.0.0.1")
    monkeypatch.setenv("TARGET_PORT", test_port)
    monkeypatch.setenv("RECEIVER_PORT", test_port)
    monkeypatch.setenv("USE_TCP", "false")  # Use UDP for simplicity
    monkeypatch.setenv("FISH_AUDIO_API_KEY", "test_key")  # Required but not used with mock
    
    # Import after patching
    from backend.scripts import receiver_main, sender_main
    
    # mock_audio_service is injected by the conftest fixture
    # Reset it to ensure clean state
    mock_audio_service.reset()
    
    # Generate conversation pattern (2 turns)
    conversation_pattern = generate_conversation_pattern(num_turns=2)
    mock_audio_service.set_input_pattern(conversation_pattern)
    
    # Create stop events for threads
    sender_stop_event = threading.Event()
    receiver_stop_event = threading.Event()
    
    # Track exceptions from threads
    thread_exceptions = []
    
    def sender_wrapper():
        """Wrapper to catch exceptions from sender thread."""
        try:
            sender_main.main_loop(stop_event=sender_stop_event)
        except Exception as e:
            thread_exceptions.append(("sender", e))
    
    def receiver_wrapper():
        """Wrapper to catch exceptions from receiver thread."""
        try:
            receiver_main.receiver_loop(stop_event=receiver_stop_event)
        except Exception as e:
            thread_exceptions.append(("receiver", e))
    
    # Start receiver thread first (it needs to bind to port)
    receiver_thread = threading.Thread(target=receiver_wrapper, daemon=True)
    receiver_thread.start()
    
    # Wait for receiver to be ready
    time.sleep(0.5)
    
    # Start sender thread
    sender_thread = threading.Thread(target=sender_wrapper, daemon=True)
    sender_thread.start()
    
    # Let threads run for sufficient time to process multiple turns
    # Pattern has ~86 chunks per turn (2s speech) + ~43 chunks silence = ~129 chunks per turn
    # At 512 samples/chunk, 44100Hz, that's ~1.5 seconds per turn
    # With 2 turns, we need at least 3 seconds, plus processing time
    max_runtime = 15.0  # Generous timeout
    start_time = time.time()
    
    try:
        # Wait for pattern to complete or timeout
        while time.time() - start_time < max_runtime:
            # Check if we've received at least 2 audio chunks (2 turns)
            if len(mock_audio_service.written_audio_chunks) >= 2:
                # Give a bit more time for cleanup
                time.sleep(0.5)
                break
            time.sleep(0.1)
    finally:
        # Signal threads to stop
        sender_stop_event.set()
        receiver_stop_event.set()
        
        # Wait for threads to finish
        sender_thread.join(timeout=2)
        receiver_thread.join(timeout=2)
    
    # Check for thread exceptions
    if thread_exceptions:
        for thread_name, exc in thread_exceptions:
            print(f"Exception in {thread_name} thread: {exc}")
        # Don't fail immediately - check if we got results anyway
    
    # Verification: Assert multiple audio chunks were received
    written_chunks = mock_audio_service.written_audio_chunks
    
    # Critical assertion: Must receive at least 2 chunks (proving multiple turns work)
    assert len(written_chunks) >= 2, (
        f"Expected at least 2 audio chunks (multiple turns), but got {len(written_chunks)}. "
        f"This indicates a deadlock bug after the first transmission."
    )
    
    # Assert each chunk is non-empty
    assert all(len(chunk) > 0 for chunk in written_chunks), (
        "Some audio chunks are empty, indicating synthesis failure."
    )
    
    # Assert chunks have reasonable size (WAV files should be > 1000 bytes)
    assert all(len(chunk) > 1000 for chunk in written_chunks), (
        f"Audio chunks are too small. Expected > 1000 bytes per chunk, "
        f"but got sizes: {[len(c) for c in written_chunks]}"
    )
    
    # Success: Multiple turns processed correctly
    print(f"✓ E2E test passed: Received {len(written_chunks)} audio chunks across multiple turns")
