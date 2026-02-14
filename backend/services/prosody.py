"""
Module: Prosody Extraction Service
Purpose: Uses Aubio to extract the 'Emotional Metadata' (Pitch and Energy)
         from the audio signal. This allows the receiver to 'hallucinate' the tone.
"""

import aubio
import numpy as np

class ProsodyExtractor:
    def __init__(self, sample_rate: int = 48000, hop_size: int = 512) -> None:
        """
        Initialize Aubio analyzers.
        
        Creates a pitch detection object using the YIN algorithm for fundamental
        frequency (F0) extraction. Configures tolerance and unit settings for
        accurate pitch analysis.
        
        Args:
            sample_rate: Audio sample rate in Hz. Default is 44100 Hz.
            hop_size: Analysis hop size in samples. Default is 512 samples.
                Smaller values provide higher temporal resolution at the cost
                of increased computation.
        
        Returns:
            None
        """
        self.sample_rate = sample_rate
        self.hop_size = hop_size
        
        # Create pitch detector (using 'yin' method)
        self.pitch_detector = aubio.pitch('yin', 4096, hop_size, sample_rate)
        self.pitch_detector.set_unit('Hz')
        self.pitch_detector.set_tolerance(0.8)

    def analyze_buffer(self, audio_buffer: np.ndarray) -> dict[str, str]:
        """
        Analyzes a full phrase buffer to extract average prosody metrics.

        Computes energy (RMS-based volume) and pitch (fundamental frequency F0)
        from the audio buffer. Processes the buffer in chunks using Aubio's
        streaming interface to extract pitch values, then aggregates results
        into categorical tags.

        Args:
            audio_buffer: Numpy array of float32 audio samples representing
                the spoken phrase. Should be normalized between -1.0 and 1.0.

        Returns:
            dict[str, str]: Metadata dictionary with keys:
                - 'energy': Volume level tag ('Quiet', 'Normal', or 'Loud')
                - 'pitch': Pitch level tag ('Deep', 'Normal', or 'High')
                
                Pitch values of 0.0 (silence/unvoiced segments) are filtered out
                before calculating the average. If no voiced segments are detected,
                pitch defaults to 'Normal'.
        """
        if isinstance(audio_buffer, list):
            audio_buffer = np.concatenate(audio_buffer)
        
        if not isinstance(audio_buffer, np.ndarray):
            audio_buffer = np.array(audio_buffer, dtype=np.float32)
        
        if audio_buffer.dtype != np.float32:
            audio_buffer = audio_buffer.astype(np.float32)
        
        rms = np.sqrt(np.mean(audio_buffer ** 2))
        
        if rms < 0.05:
            energy_tag = 'Quiet'
        elif rms < 0.15:
            energy_tag = 'Normal'
        else:
            energy_tag = 'Loud'
        
        pitch_values = []
        total_samples = len(audio_buffer)
        for i in range(0, total_samples, self.hop_size):
            chunk = audio_buffer[i:i + self.hop_size]
            
            if len(chunk) < self.hop_size:
                chunk = np.pad(chunk, (0, self.hop_size - len(chunk)), mode='constant')
            
            pitch = self.pitch_detector(chunk)[0]
            
            if pitch > 0.0:
                pitch_values.append(pitch)
        
        if len(pitch_values) > 0:
            avg_pitch = np.mean(pitch_values)
            
            if avg_pitch < 120:
                pitch_tag = 'Deep'
            elif avg_pitch < 200:
                pitch_tag = 'Normal'
            else:
                pitch_tag = 'High'
        else:
            pitch_tag = 'Normal'
        
        return {
            'energy': energy_tag,
            'pitch': pitch_tag
        }