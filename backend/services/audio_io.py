"""Audio input/output service.

This module provides a small wrapper around PyAudio for microphone capture and speaker
playback. When PyAudio is unavailable (or hardware initialization fails), the service
falls back to a silent mode that returns zero-filled buffers and ignores playback.
"""

import logging
import time
import warnings
from typing import Optional, Union

import numpy as np
try:
    import pyaudio  # type: ignore
except ModuleNotFoundError as exc:
    pyaudio = None  # type: ignore
    _PYAUDIO_IMPORT_ERROR = exc

logger = logging.getLogger(__name__)


class AudioService:
    def __init__(self) -> None:
        """
        Initialize microphone capture and speaker playback.

        The service attempts to open both input and output streams. If PyAudio is not
        installed or the host cannot provide audio devices, the service operates in a
        silent mode suitable for tests and headless deployments.
        """
        # Audio configuration constants
        self.SAMPLE_RATE = 48000
        self.CHUNK_SIZE = 1536
        self.CHANNELS = 1
        self.FORMAT = None if pyaudio is None else pyaudio.paInt16
        
        # Safety flag for hardware availability
        self._pyaudio_available = False
        
        # Initialize to None to ensure cleanup works even if init fails partially
        self.pyaudio_instance: Optional["pyaudio.PyAudio"] = None  # type: ignore[name-defined]
        self.input_stream = None
        self.output_stream = None

        if pyaudio is None:
            warnings.warn(
                "PyAudio is not installed; AudioService will run in Silent/Mock mode. "
                f"Import error: {_PYAUDIO_IMPORT_ERROR}"
            )
            logger.error("PyAudio import error: %s", _PYAUDIO_IMPORT_ERROR)
            return
        
        try:
            # Initialize PyAudio
            self.pyaudio_instance = pyaudio.PyAudio()
            logger.info("PyAudio instance initialized successfully.")
        except Exception as exc:
            warnings.warn(
                f"Failed to initialize PyAudio: {exc}. Running in silent mode."
            )
            logger.error("PyAudio initialization error: %s", exc)
            self.pyaudio_instance = None
            return
        
        # Try to open input stream (microphone)
        try:
            self.input_stream = self.pyaudio_instance.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                input=True,
                frames_per_buffer=self.CHUNK_SIZE
            )
            logger.info("Audio input stream opened successfully.")
        except Exception as exc:
            warnings.warn(
                f"Failed to open audio input stream: {exc}. Input will be disabled."
            )
            logger.error("Audio input stream error: %s", exc)
            # Ensure stream is None if opening failed
            if self.input_stream is not None:
                try:
                    self.input_stream.stop_stream()
                    self.input_stream.close()
                except Exception:
                    pass
                self.input_stream = None
        
        # Try to open output stream (speakers)
        try:
            self.output_stream = self.pyaudio_instance.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                output=True,
                frames_per_buffer=self.CHUNK_SIZE
            )
            logger.info("Audio output stream opened successfully.")
        except Exception as exc:
            warnings.warn(
                f"Failed to open audio output stream: {exc}. Output will be disabled."
            )
            logger.error("Audio output stream error: %s", exc)
            # Ensure stream is None if opening failed
            if self.output_stream is not None:
                try:
                    self.output_stream.stop_stream()
                    self.output_stream.close()
                except Exception:
                    pass
                self.output_stream = None
        
        if self.input_stream is not None or self.output_stream is not None:
            self._pyaudio_available = True
            logger.info("AudioService initialized successfully.")
        else:
            logger.warning("AudioService initialized but no streams available. Running in Silent/Mock mode.")

    def read_chunk(self) -> np.ndarray:
        """
        Reads a single chunk of audio from the microphone stream.
        
        Returns:
            np.ndarray: A float32 array of audio samples normalized between -1.0 and 1.0.
                Returns a zero-filled array if hardware is unavailable or on overflow.
                This format is required by Silero VAD and Whisper processing pipelines.
        """
        if not self._pyaudio_available or self.input_stream is None:
            # Simulate real-time capture duration to avoid hammering CPU in Mock mode
            time.sleep(self.CHUNK_SIZE / self.SAMPLE_RATE)
            return np.zeros(self.CHUNK_SIZE, dtype=np.float32)
        
        try:
            raw_data = self.input_stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
        except IOError as exc:
            logger.warning("Audio input overflow: %s", exc)
            raw_data = b"\x00" * (self.CHUNK_SIZE * 2)
        
        audio_int16 = np.frombuffer(raw_data, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        
        return audio_float32

    def write_chunk(self, audio_data: Union[bytes, np.ndarray, None]) -> None:
        """
        Plays a chunk of audio out to the speakers.
        
        Accepts audio data as bytes or numpy array (float32 or int16) and writes
        it to the output stream. Automatically converts float32 arrays to int16
        format required by PyAudio.
        
        Args:
            audio_data: Audio data as bytes or numpy array (float32 normalized
                between -1.0 and 1.0, or int16). If None or hardware unavailable,
                the operation is silently skipped.
        
        Returns:
            None
        """
        if not self._pyaudio_available or self.output_stream is None:
            return

        if audio_data is None:
            return
        
        if isinstance(audio_data, np.ndarray):
            if audio_data.dtype == np.float32:
                audio_data = (audio_data * 32768.0).astype(np.int16)
            elif audio_data.dtype != np.int16:
                audio_data = audio_data.astype(np.int16)
            
            audio_bytes = audio_data.tobytes()
        else:
            audio_bytes = audio_data
        
        self.output_stream.write(audio_bytes)

    def close(self) -> None:
        """
        Cleanup resources.
        
        Stops and closes all audio streams (input and output), then terminates
        the PyAudio instance. Errors during cleanup are silently ignored to ensure
        resources are released even if streams are in an invalid state.
        """
        if self.input_stream is not None:
            try:
                self.input_stream.stop_stream()
                self.input_stream.close()
            except Exception:
                pass  # Ignore errors during cleanup
        
        if self.output_stream is not None:
            try:
                self.output_stream.stop_stream()
                self.output_stream.close()
            except Exception:
                pass  # Ignore errors during cleanup
        
        if self.pyaudio_instance is not None:
            try:
                self.pyaudio_instance.terminate()
            except Exception:
                pass  # Ignore errors during cleanup