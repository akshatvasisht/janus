"""
Module: Voice Activity Detection (VAD) Service
Purpose: Acts as the 'Gatekeeper'. Uses Silero-VAD to analyze audio chunks
         and determine if they contain human speech or just background noise.
"""

import torch
import numpy as np

class VoiceActivityDetector:
    def __init__(self, threshold: float = 0.5, sample_rate: int = 44100) -> None:
        """
        Initialize the VAD Model.
        
        Loads the pre-trained Silero-VAD model from torch.hub or local cache and
        configures it for speech detection. The model operates at 16kHz internally
        and will automatically downsample higher sample rates.
        
        Args:
            threshold: Sensitivity threshold between 0.0 and 1.0. Audio chunks with
                speech probability above this value are classified as speech.
                Default is 0.5.
            sample_rate: Input audio sample rate in Hz. Default is 44100 Hz.
                The model will downsample to 16kHz internally if needed.
        """
        self.threshold = threshold
        self.sample_rate = sample_rate
        
        # Load Silero VAD model v4 from torch.hub
        self.model, self.utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            onnx=False
        )
        
        # Set model to evaluation mode
        self.model.eval()

    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """
        Analyzes a single audio chunk to detect speech.

        Args:
            audio_chunk: A numpy array of float32 audio samples normalized between
                -1.0 and 1.0.

        Returns:
            bool: True if speech is detected (probability exceeds threshold),
                False otherwise.

        Note:
            Audio is downsampled from 44.1kHz to approximately 16kHz by taking
            every 3rd sample. This lightweight approach avoids heavy resampling
            libraries while maintaining acceptable accuracy for VAD.
        """
        # Downsample 44100 -> ~14700 (close enough for VAD) by taking every 3rd sample
        # Lightweight downsampling approach to avoid heavy resampling dependencies.
        if self.sample_rate == 44100:
            audio_chunk = audio_chunk[::3]
            vad_sample_rate = 16000  # Silero VAD expects 16k
        else:
            vad_sample_rate = self.sample_rate
        
        # Ensure audio is float32 and in correct shape
        if isinstance(audio_chunk, np.ndarray):
            audio_tensor = torch.from_numpy(audio_chunk).float()
        else:
            audio_tensor = audio_chunk.float()
        
        # Reshape to (1, samples) if needed
        if audio_tensor.dim() == 1:
            audio_tensor = audio_tensor.unsqueeze(0)
        
        # Get speech probability from model
        with torch.no_grad():
            speech_prob = self.model(audio_tensor, vad_sample_rate).item()
        
        # Return True if probability exceeds threshold
        return speech_prob > self.threshold

    def reset(self) -> None:
        """
        Reset the model state (if using a stateful recurrent model).
        
        Useful between distinct conversation turns. Silero VAD v4 is stateless,
        so this method is a no-op but maintained for API consistency.
        """
        # Silero VAD v4 is stateless, so this is a no-op
        # But we keep the method for API consistency
        pass