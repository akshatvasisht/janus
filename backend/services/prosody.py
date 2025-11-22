"""
Module: Prosody Extraction Service
Purpose: Uses Aubio to extract the 'Emotional Metadata' (Pitch and Energy)
         from the audio signal. This allows the receiver to 'hallucinate' the tone.
"""

import aubio
import numpy as np

class ProsodyExtractor:
    def __init__(self, sample_rate=16000, hop_size=512):
        """
        Initialize Aubio analyzers.
        1. Create a Pitch detection object (method='yin' or 'yinfft').
           - Set tolerance and unit (Hz).
        2. Store sample rate and hop size for calculations.
        """
        self.sample_rate = sample_rate
        self.hop_size = hop_size
        
        # Create pitch detector (using 'yin' method)
        self.pitch_detector = aubio.pitch('yin', 4096, hop_size, sample_rate)
        self.pitch_detector.set_unit('Hz')
        self.pitch_detector.set_tolerance(0.8)

    def analyze_buffer(self, audio_buffer):
        """
        Analyzes a full phrase buffer to extract average prosody metrics.

        Args:
            audio_buffer: Numpy array of the spoken phrase.

        Steps:
        1. Calculate ENERGY (Volume):
           - Compute Root Mean Square (RMS) of the buffer.
           - Map RMS to a simple scale (0-10) or tags (Quiet, Normal, Loud).
        
        2. Calculate PITCH (Tone):
           - Since Aubio processes streams, iterate through the buffer in chunks.
           - For each chunk, get the fundamental frequency (F0).
           - Filter out 0.0 values (silence/unvoiced).
           - Calculate the average F0 of the voiced segments.
           - Map average F0 to tags (Deep, Normal, High/Excited).

        3. Return a metadata dictionary:
           {
               'energy': 'High',
               'pitch': 'Normal',
               'speed': 'Fast' (Optional: calculated by duration vs word count later)
           }
        """
        # Ensure audio_buffer is numpy array
        if isinstance(audio_buffer, list):
            audio_buffer = np.concatenate(audio_buffer)
        
        if not isinstance(audio_buffer, np.ndarray):
            audio_buffer = np.array(audio_buffer, dtype=np.float32)
        
        # Ensure float32 format
        if audio_buffer.dtype != np.float32:
            audio_buffer = audio_buffer.astype(np.float32)
        
        # 1. Calculate ENERGY (RMS)
        rms = np.sqrt(np.mean(audio_buffer ** 2))
        
        # Map RMS to tags (typical RMS range for speech: 0.01-0.3)
        if rms < 0.05:
            energy_tag = 'Quiet'
        elif rms < 0.15:
            energy_tag = 'Normal'
        else:
            energy_tag = 'Loud'
        
        # 2. Calculate PITCH (F0)
        pitch_values = []
        
        # Process buffer in hop_size chunks
        total_samples = len(audio_buffer)
        for i in range(0, total_samples, self.hop_size):
            chunk = audio_buffer[i:i + self.hop_size]
            
            # Pad chunk if needed to match hop_size
            if len(chunk) < self.hop_size:
                chunk = np.pad(chunk, (0, self.hop_size - len(chunk)), mode='constant')
            
            # Get pitch for this chunk
            pitch = self.pitch_detector(chunk)[0]
            
            # Filter out 0.0 values (silence/unvoiced)
            if pitch > 0.0:
                pitch_values.append(pitch)
        
        # Calculate average F0 of voiced segments
        if len(pitch_values) > 0:
            avg_pitch = np.mean(pitch_values)
            
            # Map average F0 to tags (typical male: 85-180Hz, female: 165-255Hz)
            if avg_pitch < 120:
                pitch_tag = 'Deep'
            elif avg_pitch < 200:
                pitch_tag = 'Normal'
            else:
                pitch_tag = 'High'
        else:
            # No voiced segments detected
            pitch_tag = 'Normal'  # Default
        
        # 3. Return metadata dictionary
        return {
            'energy': energy_tag,
            'pitch': pitch_tag
        }