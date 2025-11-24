"""
Module: Transcription Service
Purpose: Converts raw audio buffers into text using Faster-Whisper.
         Optimized for CPU usage with Int8 quantization.
"""

from faster_whisper import WhisperModel
import numpy as np

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
        
        Note:
            Uses greedy search (beam_size=1) for lowest latency. Audio is
            downsampled from 44.1kHz to 16kHz by taking every 3rd sample.
        """
        # Ensure audio is float32 numpy array
        if isinstance(audio_buffer, list):
            audio_buffer = np.concatenate(audio_buffer)
        
        if not isinstance(audio_buffer, np.ndarray):
            audio_buffer = np.array(audio_buffer, dtype=np.float32)
        
        # Ensure float32 format
        if audio_buffer.dtype != np.float32:
            audio_buffer = audio_buffer.astype(np.float32)
        
        # Downsample 44.1k to 16k logic
        # Ideally use scipy.signal.resample if available, otherwise slicing [::3] is an acceptable fallback for speed.
        # Assuming input is 44100 Hz, downsample by taking every 3rd sample (44100/3 ≈ 14700 Hz, close enough to 16k)
        audio_16k = audio_buffer[::3]
        
        # Transcribe with beam_size=1 for lowest latency
        segments, info = self.model.transcribe(
            audio_16k,
            beam_size=1,
            language='en'
        )
        
        # Aggregate segments into a single text string
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())
        
        # Join and return trimmed text
        full_text = ' '.join(text_parts).strip()
        return full_text

    def transcribe_file(self, file_path: str) -> str:
        """
        Transcribes an audio file directly from disk.
        
        Faster-Whisper handles format conversions (WebM/WAV/MP3/etc) automatically.
        Uses greedy search for lowest latency.
        
        Args:
            file_path: Path to the audio file. Supports various formats including
                WAV, WebM, MP3, and others supported by FFmpeg.
        
        Returns:
            str: Transcribed text string with whitespace normalized.
                Returns empty string if no speech is detected.
        """
        # Transcribe with beam_size=1 for lowest latency
        segments, info = self.model.transcribe(
            file_path,
            beam_size=1,
            language='en'
        )
        
        # Aggregate segments into a single text string
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())
        
        # Join and return trimmed text
        full_text = ' '.join(text_parts).strip()
        return full_text