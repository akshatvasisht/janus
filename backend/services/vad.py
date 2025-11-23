"""
Module: Voice Activity Detection (VAD) Service
Purpose: Acts as the 'Gatekeeper'. Uses Silero-VAD to analyze audio chunks
         and determine if they contain human speech or just background noise.
"""

import torch
import numpy as np

class VoiceActivityDetector:
    def __init__(self, threshold=0.5, sample_rate=44100):
        """
        Initialize the VAD Model.
        1. Load the pre-trained 'silero-vad' model from torch.hub or local cache.
        2. Set the sensitivity threshold (e.g., 0.5). Values above this are 'Speech', below are 'Silence'.
        3. Set the sample rate (default 44100 Hz). VAD will downsample to 16k internally if needed.
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

    def is_speech(self, audio_chunk):
        """
        Analyzes a single audio chunk to detect speech.

        Args:
            audio_chunk: A numpy array of float32 audio samples.

        Steps:
        1. Downsample audio if sample rate is 44100 Hz (Silero VAD requires 16k or 8k).
        2. Pass the audio_chunk to the Silero model.
        3. Get the probability score (0.0 to 1.0).
        4. Compare score > threshold.
        5. Return True if speech is detected, False otherwise.
        """
        # Downsample 44100 -> ~14700 (close enough for VAD) by taking every 3rd sample
        # This is a fast hack for the hackathon to avoid heavy resampling libraries.
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

    def reset(self):
        """
        Reset the model state (if using a stateful recurrent model).
        Useful between distinct conversation turns.
        """
        # Silero VAD v4 is stateless, so this is a no-op
        # But we keep the method for API consistency
        pass