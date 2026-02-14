"""
Module: Voice Activity Detection (VAD) Service
Purpose: Acts as the 'Gatekeeper'. Uses Silero-VAD to analyze audio chunks
         and determine if they contain human speech or just background noise.
"""

import numpy as np
import torch

class VoiceActivityDetector:
    def __init__(self, threshold: float = 0.5, sample_rate: int = 48000) -> None:
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
        """
        if self.sample_rate == 48000:
            audio_chunk = audio_chunk[::3]
            vad_sample_rate = 16000  # Silero VAD expects 16k
        elif self.sample_rate == 44100:
            # Fallback for old rate if used, though it's still slightly inaccurate without proper resampling
            audio_chunk = audio_chunk[::3]
            vad_sample_rate = 16000
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
        Reset the model state.
        
        Maintained for API consistency. This method is a no-op for stateless models.
        
        Returns:
            None
        """
        pass