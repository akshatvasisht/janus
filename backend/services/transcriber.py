"""
Module: Transcription Service
Purpose: Converts raw audio buffers into text using Faster-Whisper.
         Optimized for CPU usage with Int8 quantization.
"""

# Standard library imports
# (none)

# Third-party imports
import numpy as np
from faster_whisper import WhisperModel

class Transcriber:
    def __init__(self, model_size: str = 'base.en') -> None:
        """
        Initialize the Whisper Model.
        
        Loads a Faster-Whisper model optimized for CPU inference with Int8
        quantization. This configuration provides a balance between accuracy
        and performance for wider hardware compatibility.
        
        Args:
            model_size: Model size identifier (e.g., 'base.en', 'distil-small.en').
                Default is 'base.en' for English-only transcription.
        """
        self.model = WhisperModel(
            model_size,
            device='cpu',
            compute_type='int8'
        )

    def transcribe_buffer(self, audio_buffer: np.ndarray) -> str:
        """
        Converts a collected buffer of speech into text.

        Args:
            audio_buffer: A numpy array containing the full spoken phrase.
                Assumed to be sampled at 44100 Hz. Will be automatically
                downsampled to 16kHz for Whisper processing.

        Returns:
            str: Transcribed text string with whitespace normalized.
                Returns empty string if no speech is detected.
        """
        if isinstance(audio_buffer, list):
            audio_buffer = np.concatenate(audio_buffer)
        
        if not isinstance(audio_buffer, np.ndarray):
            audio_buffer = np.array(audio_buffer, dtype=np.float32)
        
        if audio_buffer.dtype != np.float32:
            audio_buffer = audio_buffer.astype(np.float32)
        
        audio_16k = audio_buffer[::3]
        
        segments, info = self.model.transcribe(
            audio_16k,
            beam_size=1,
            language='en'
        )
        
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())
        
        full_text = ' '.join(text_parts).strip()
        return full_text

    def transcribe_file(self, file_path: str) -> str:
        """
        Transcribes an audio file directly from disk.
        
        Faster-Whisper handles format conversions (WebM/WAV/MP3/etc) automatically.
        
        Args:
            file_path: Path to the audio file. Supports various formats including
                WAV, WebM, MP3, and others supported by FFmpeg.
        
        Returns:
            str: Transcribed text string with whitespace normalized.
                Returns empty string if no speech is detected.
        """
        segments, info = self.model.transcribe(
            file_path,
            beam_size=1,
            language='en'
        )
        
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())
        
        full_text = ' '.join(text_parts).strip()
        return full_text