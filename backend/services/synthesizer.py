"""
Module: Synthesizer Service
Purpose: The 'Brain' of the receiver. It converts the received 'JanusPacket' 
         (Text + Metadata) into actual Audio Bytes.
         It handles:
         1. Generative AI (Fish Audio) for Semantic Voice.
         2. Logic for 'Dynamic Prompting' (Mapping Pitch/Energy -> Emotion Tags).
         3. Fallback generation for Text-Only mode.
         4. Sine wave generation for Morse Code (Stretch Goal).
"""

# Audio format constants
SAMPLE_RATE = 44100  # Hz
MORSE_FREQUENCY = 800  # Hz for Morse code beeps

# Import Fish Audio SDK (new API)
from fishaudio import FishAudio
from fishaudio.types import ReferenceAudio

# Import Numpy (for Morse Code math)
import numpy as np

# Import Enum (JanusMode)
from ..common.protocol import JanusMode

# Import os for path operations and hot-reload
import os
from pathlib import Path

class Synthesizer:
    def __init__(self, api_key, reference_audio_path=None):
        """
        Initialize the Synthesizer.
        1. Setup Fish Audio Client with API Key.
        2. Load the 'Reference Audio' file into memory (bytes).
           - This is the "Voice ID" we are cloning.
           - If no file provided, use a default system ID.
        3. Define Morse Code Dictionary (A=.-, B=-..., etc).
        """
        # Initialize Fish Audio SDK client (new API)
        self.client = FishAudio(api_key=api_key)
        
        # FIX: Initialize the attribute explicitly
        self.reference_audio_bytes = None
        self._reference_audio_mtime = None
        self._reference_audio_path = None
        
        # Determine reference audio path (always store target path, even if file doesn't exist yet)
        # Prefer environment variable, otherwise use default path in backend directory
        if reference_audio_path:
            audio_path = reference_audio_path
        else:
            # Always use default path in backend directory (even if file doesn't exist yet)
            backend_dir = Path(__file__).parent.parent
            default_path = backend_dir / "reference_audio.wav"
            audio_path = str(default_path)
        
        # Always set the target path and try to load reference audio
        # This allows hot-reload to work even if file doesn't exist at startup
        self._reference_audio_path = audio_path
        self._load_reference_audio(audio_path)
        
        # Define Morse Code Dictionary (A=.-, B=-..., etc)
        self.morse_code_dict = {
            'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.',
            'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..',
            'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.',
            'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
            'Y': '-.--', 'Z': '--..',
            '0': '-----', '1': '.----', '2': '..---', '3': '...--', '4': '....-',
            '5': '.....', '6': '-....', '7': '--...', '8': '---..', '9': '----.',
            ' ': ' '  # Space between words
        }
    
    def _load_reference_audio(self, audio_path):
        """
        Load reference audio file and store its modification time for hot-reload.
        
        Args:
            audio_path: Path to the reference audio file
        """
        try:
            if os.path.exists(audio_path):
                with open(audio_path, 'rb') as f:
                    self.reference_audio_bytes = f.read()
                self._reference_audio_mtime = os.path.getmtime(audio_path)
                # Note: _reference_audio_path is already set in __init__, don't overwrite it
            else:
                # File doesn't exist yet, but keep the path for future hot-reload checks
                self.reference_audio_bytes = None
                self._reference_audio_mtime = None
                # Keep _reference_audio_path set so hot-reload can detect when file appears
        except Exception as e:
            print(f"Warning: Could not load reference audio from {audio_path}: {e}")
            self.reference_audio_bytes = None
            self._reference_audio_mtime = None
            # Keep _reference_audio_path set even on error for future retries
    
    def _check_and_reload_reference_audio(self):
        """
        Check if reference audio file has changed and reload if necessary.
        This enables hot-reload without server restart.
        Also detects if file appears for the first time (wasn't present at startup).
        """
        if self._reference_audio_path:
            if os.path.exists(self._reference_audio_path):
                # File exists - check if it's new or has been modified
                current_mtime = os.path.getmtime(self._reference_audio_path)
                if self._reference_audio_mtime is None or self._reference_audio_mtime != current_mtime:
                    # File is new or has changed, reload it
                    self._load_reference_audio(self._reference_audio_path)
            # If file doesn't exist yet, do nothing (will be checked again on next call)

    def synthesize(self, packet):
        """
        Main entry point. Routing logic based on Packet Mode.
        
        Args:
            packet (JanusPacket): The deserialized data.
            
        Returns:
            bytes: Raw PCM audio data ready for PyAudio.
        """
        if packet.mode == JanusMode.MORSE_CODE:
            return self._generate_morse_audio(packet.text)
        elif packet.mode == JanusMode.TEXT_ONLY:
            return self._generate_fast_tts(packet.text, packet.override_emotion)
        elif packet.mode == JanusMode.SEMANTIC_VOICE:
            return self._generate_semantic_audio(packet)
        else:
            raise ValueError(f"Unknown packet mode: {packet.mode}")

    def _generate_semantic_audio(self, packet):
        """
        The Core Feature: Generative AI Voice.
        """
        # Check for hot-reload of reference audio
        self._check_and_reload_reference_audio()
        
        # 1. CONSTRUCT PROMPT
        #    Determine the "Emotion Tag" to prepend to the text.
        if packet.override_emotion and packet.override_emotion != "Auto":
            # Logic A (Manual Override):
            # Use parentheses format for Fish Audio tones
            prompt = f"({packet.override_emotion}) {packet.text}"
        else:
            # Logic B (Auto/Prosody Map):
            prosody = packet.prosody or {}
            pitch = prosody.get('pitch', 'Normal')
            energy = prosody.get('energy', 'Normal')
            
            # Map combination to emotion tags (using Fish Audio's available tones)
            if pitch == 'High' and energy == 'Loud':
                emotion_tag = "excited"  # High pitch + loud = excited
            elif pitch == 'High' and energy == 'Normal':
                emotion_tag = "joyful"  # High pitch + normal = joyful
            elif pitch == 'High' and energy in ('Quiet', 'Low'):
                emotion_tag = "whispering"  # High pitch + quiet = whispering
            elif pitch == 'Low' and energy == 'Loud':
                emotion_tag = "shouting"  # Low pitch + loud = shouting
            elif pitch == 'Low' and energy == 'Low':
                emotion_tag = "sad"  # Low pitch + low energy = sad
            elif pitch == 'Low' and energy == 'Normal':
                emotion_tag = "relaxed"  # Low pitch + normal = relaxed
            elif energy == 'Loud':
                emotion_tag = "shouting"  # Any pitch + loud = shouting
            elif energy in ('Quiet', 'Low'):
                emotion_tag = "whispering"  # Any pitch + quiet = whispering
            else:
                emotion_tag = "relaxed"  # Default to relaxed
            
            prompt = f"({emotion_tag}) {packet.text}"

        # 2. CALL FISH AUDIO API
        try:
            # Create references list if we have reference audio bytes (cloned voice)
            references = None
            reference_id = None
            
            if self.reference_audio_bytes:
                # Use cloned voice with references parameter
                references = [ReferenceAudio(
                    audio=self.reference_audio_bytes,
                    text=""  # Reference transcript not available, using empty string
                )]
            else:
                # Fall back to generic voice with default reference_id
                reference_id = "5196af35f6ff4a0dbf541793fc9f2157"
            
            # Call API directly (new API - no TTSRequest object needed)
            # Note: "pcm" format may not be supported, using "wav" which contains PCM data
            print(prompt)
            
            # Build API call parameters
            api_params = {
                "text": prompt,
                "format": "wav",  # Changed from "pcm" - wav contains PCM data
                "latency": "balanced"
            }
            
            # Use references if available, otherwise use reference_id
            if references:
                api_params["references"] = references
            else:
                api_params["reference_id"] = reference_id
            
            audio_bytes = self.client.tts.convert(**api_params)
            
            # New API returns complete audio bytes directly (not an iterator)
            return audio_bytes
            
        except Exception as e:
            # Fallback to fast TTS on API error
            print(f"Synthesis error: {e}")
            return self._generate_fast_tts(packet.text, packet.override_emotion)

    def _generate_fast_tts(self, text, emotion=None):
        """
        Fallback mode. Saves API credits/latency.
        Could use a cheaper Fish Audio model or a local system TTS.
        Uses cloned voice if available, otherwise falls back to generic voice.
        
        Args:
            text: Text to synthesize
            emotion: Optional emotion override (e.g., "joyful", "panicked")
        """
        # Check for hot-reload of reference audio
        self._check_and_reload_reference_audio()
        
        # Construct prompt with emotion tag if provided
        if emotion and emotion != "Auto":
            prompt = f"({emotion}) {text}"
        else:
            prompt = text
        
        try:
            # Build API call parameters
            api_params = {
                "text": prompt,
                "format": "wav",  # Changed from "pcm" - wav contains PCM data
                "latency": "balanced"
            }
            
            # Use cloned voice if available, otherwise use generic voice
            if self.reference_audio_bytes:
                # Use cloned voice with references parameter
                api_params["references"] = [ReferenceAudio(
                    audio=self.reference_audio_bytes,
                    text=""  # Reference transcript not available, using empty string
                )]
            else:
                # Fall back to generic voice (no reference)
                api_params["references"] = None
            
            # Call API directly (new API - no TTSRequest object needed)
            audio_bytes = self.client.tts.convert(**api_params)
            
            # New API returns complete audio bytes directly (not an iterator)
            return audio_bytes
        except Exception as e:
            # Return empty audio bytes on error
            print(f"Fast TTS error: {e}")
            return b''

    def _generate_morse_audio(self, text):
        """
        Stretch Goal: Turn text into sine waves.
        
        Logic:
        1. Iterate chars in text.
        2. Look up Morse pattern (e.g., ".-").
        3. For '.': Generate 0.1s sine wave (800Hz).
        4. For '-': Generate 0.3s sine wave (800Hz).
        5. Add silence between beeps.
        6. Concatenate all numpy arrays.
        7. Convert to bytes and return.
        """
        audio_segments = []
        
        # Convert text to uppercase for morse code lookup
        text_upper = text.upper()
        
        for char in text_upper:
            if char in self.morse_code_dict:
                pattern = self.morse_code_dict[char]
                
                # Handle space (word separator)
                if pattern == ' ':
                    # Add longer silence between words (0.7s)
                    silence_samples = int(0.7 * SAMPLE_RATE)
                    audio_segments.append(np.zeros(silence_samples, dtype=np.int16))
                    continue
                
                # Generate audio for each dot/dash in the pattern
                for i, symbol in enumerate(pattern):
                    if symbol == '.':
                        # Dot: 0.1s tone
                        duration = 0.1
                    elif symbol == '-':
                        # Dash: 0.3s tone
                        duration = 0.3
                    else:
                        continue
                    
                    # Generate sine wave
                    samples = int(duration * SAMPLE_RATE)
                    t = np.linspace(0, duration, samples, False)
                    wave = np.sin(2 * np.pi * MORSE_FREQUENCY * t)
                    
                    # Convert to int16 and scale
                    wave_int16 = (wave * 32767 * 0.5).astype(np.int16)
                    audio_segments.append(wave_int16)
                    
                    # Add silence between symbols (0.1s) except after last symbol
                    if i < len(pattern) - 1:
                        silence_samples = int(0.1 * SAMPLE_RATE)
                        audio_segments.append(np.zeros(silence_samples, dtype=np.int16))
                
                # Add silence between letters (0.3s) except after last character
                if char != text_upper[-1]:
                    silence_samples = int(0.3 * SAMPLE_RATE)
                    audio_segments.append(np.zeros(silence_samples, dtype=np.int16))
        
        # Concatenate all segments
        if audio_segments:
            audio_array = np.concatenate(audio_segments)
        else:
            audio_array = np.array([], dtype=np.int16)
        
        # Convert to bytes
        return audio_array.tobytes()