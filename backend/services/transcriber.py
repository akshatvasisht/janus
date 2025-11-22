"""
Module: Transcription Service
Purpose: Converts raw audio buffers into text using Faster-Whisper.
         Optimized for CPU usage with Int8 quantization.
"""

from faster_whisper import WhisperModel
import numpy as np

class Transcriber:
    def __init__(self, model_size='base.en'):
        """
        Initialize the Whisper Model.
        1. Load 'faster-whisper' model (e.g., 'distil-small.en' or 'base.en').
        2. CONFIGURATION CRITICAL:
           - Set device='cpu' (assuming hackathon laptop).
           - Set compute_type='int8' (Quantization for speed).
        """
        self.model = WhisperModel(
            model_size,
            device='cpu',
            compute_type='int8'
        )

    def transcribe_buffer(self, audio_buffer):
        """
        Converts a collected buffer of speech into text.

        Args:
            audio_buffer: A large numpy array containing the full spoken phrase.

        Steps:
        1. Run model.transcribe() on the audio_buffer.
        2. Set beam_size=1 (Greedy search) for lowest latency.
        3. Aggregate the segments into a single text string.
        4. Return the text string.
        """
        # Ensure audio is float32 numpy array
        if isinstance(audio_buffer, list):
            audio_buffer = np.concatenate(audio_buffer)
        
        if not isinstance(audio_buffer, np.ndarray):
            audio_buffer = np.array(audio_buffer, dtype=np.float32)
        
        # Ensure float32 format
        if audio_buffer.dtype != np.float32:
            audio_buffer = audio_buffer.astype(np.float32)
        
        # Transcribe with beam_size=1 for lowest latency
        segments, info = self.model.transcribe(
            audio_buffer,
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