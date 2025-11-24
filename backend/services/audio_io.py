"""
Module: Audio Input/Output Service
Purpose: Handles the raw interface with the microphone and speakers using PyAudio.
         It provides a stream for reading raw bytes and converting them to numpy arrays
         which are required for AI processing.
"""

import pyaudio
import numpy as np
import warnings
import logging

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self):
        """
        Initialize the Audio Service.
        1. Setup PyAudio instance.
        2. Define constants for Sample Rate (e.g., 44100Hz), Chunk Size (e.g., 512), and Channels (Mono).
        3. Open a specific input stream for the Microphone.
        4. Open a specific output stream for the Speakers (for later playback).
        """
        # Audio configuration constants
        self.SAMPLE_RATE = 44100
        self.CHUNK_SIZE = 512
        self.CHANNELS = 1
        self.FORMAT = pyaudio.paInt16
        
        # Safety flag for hardware availability
        self._pyaudio_available = False
        
        # Initialize to None to ensure cleanup works even if init fails partially
        self.pyaudio_instance = None
        self.input_stream = None
        self.output_stream = None
        
        try:
            # Initialize PyAudio
            self.pyaudio_instance = pyaudio.PyAudio()
            logger.info("PyAudio instance initialized successfully.")
        except Exception as e:
            warnings.warn(f"Failed to initialize PyAudio: {e}. Running in Silent/Mock mode.")
            logger.error(f"PyAudio initialization error: {e}")
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
        except Exception as e:
            warnings.warn(f"Failed to open audio input stream: {e}. Input will be disabled.")
            logger.error(f"Audio input stream error: {e}")
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
        except Exception as e:
            warnings.warn(f"Failed to open audio output stream: {e}. Output will be disabled.")
            logger.error(f"Audio output stream error: {e}")
            # Ensure stream is None if opening failed
            if self.output_stream is not None:
                try:
                    self.output_stream.stop_stream()
                    self.output_stream.close()
                except Exception:
                    pass
                self.output_stream = None
        
        # Set availability flag only if at least one stream is available
        if self.input_stream is not None or self.output_stream is not None:
            self._pyaudio_available = True
            logger.info("✅ AudioService initialized successfully.")
        else:
            logger.warning("AudioService initialized but no streams available. Running in Silent/Mock mode.")

    def read_chunk(self):
        """
        Reads a single chunk of audio from the microphone stream.
        
        Steps:
        1. Read 'Chunk Size' bytes from the input stream.
        2. Handle any potential overflow errors (if computer is slow).
        3. Convert raw bytes into a Float32 NumPy array (normalized between -1.0 and 1.0).
           - This format is required by Silero VAD and Whisper.
        4. Return the numpy array.
        """
        if not self._pyaudio_available or self.input_stream is None:
            # Return silent data if initialization failed or input stream failed to initialize
            return np.zeros(self.CHUNK_SIZE, dtype=np.float32)
        
        try:
            # Read raw bytes from input stream
            raw_data = self.input_stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
        except IOError as e:
            # Handle overflow gracefully - log and return zeros
            print(f"Audio input overflow: {e}")
            raw_data = b'\x00' * (self.CHUNK_SIZE * 2)  # 2 bytes per sample (int16)
        
        # Convert bytes to numpy array (int16)
        audio_int16 = np.frombuffer(raw_data, dtype=np.int16)
        
        # Convert to float32 normalized between -1.0 and 1.0
        audio_float32 = audio_int16.astype(np.float32) / 32768.0
        
        return audio_float32

    def write_chunk(self, audio_data):
        """
        Plays a chunk of audio out to the speakers.
        
        Steps:
        1. Receive audio data (likely bytes or numpy array).
        2. Write data to the output stream.
        """
        if not self._pyaudio_available or self.output_stream is None:
            # Skip writing if no hardware is available or output stream failed to initialize
            return
        
        # Convert numpy array to int16 if needed
        if isinstance(audio_data, np.ndarray):
            if audio_data.dtype == np.float32:
                # Normalize from -1.0 to 1.0 range to int16
                audio_data = (audio_data * 32768.0).astype(np.int16)
            elif audio_data.dtype != np.int16:
                audio_data = audio_data.astype(np.int16)
            
            # Convert to bytes
            audio_bytes = audio_data.tobytes()
        else:
            # Assume it's already bytes
            audio_bytes = audio_data
        
        # Write to output stream
        self.output_stream.write(audio_bytes)

    def close(self):
        """
        Cleanup resources.
        1. Stop and close streams.
        2. Terminate PyAudio instance.
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