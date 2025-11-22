"""
Module: Voice Activity Detection (VAD) Service
Purpose: Acts as the 'Gatekeeper'. Uses Silero-VAD to analyze audio chunks
         and determine if they contain human speech or just background noise.
"""

import torch
import numpy as np

class VoiceActivityDetector:
    def __init__(self, threshold=0.5):
        """
        Initialize the VAD Model.
        1. Load the pre-trained 'silero-vad' model from torch.hub or local cache.
        2. Set the sensitivity threshold (e.g., 0.5). Values above this are 'Speech', below are 'Silence'.
        """
        self.threshold = threshold
        self.sample_rate = 16000
        
        # Load Silero VAD model v4 from torch.hub
        self.model, self.utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            onnx=False
        )
        
        # Set model to evaluation mode
        self.model.eval()

    def is_speech(self, audio_chunk):
        """
        Analyzes a single audio chunk to detect speech.

        Args:
            audio_chunk: A numpy array of float32 audio samples.

        Steps:
        1. Pass the audio_chunk to the Silero model.
        2. Get the probability score (0.0 to 1.0).
        3. Compare score > threshold.
        4. Return True if speech is detected, False otherwise.
        """
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
            speech_prob = self.model(audio_tensor, self.sample_rate).item()
        
        # Return True if probability exceeds threshold
        return speech_prob > self.threshold

    def reset(self):
        """
        Reset the model state (if using a stateful recurrent model).
        Useful between distinct conversation turns.
        """
        # Silero VAD v4 is stateless, so this is a no-op
        # But we keep the method for API consistency
        pass