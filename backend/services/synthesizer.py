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

# Standard library imports
import os
from pathlib import Path

# Third-party imports
import numpy as np
from fishaudio import FishAudio
from fishaudio.types import ReferenceAudio

# Local imports
from ..common.protocol import JanusMode, JanusPacket

# Audio format constants
SAMPLE_RATE = 44100  # Hz
MORSE_FREQUENCY = 800  # Hz for Morse code beeps

class Synthesizer:
    def __init__(self, api_key: str, reference_audio_path: str | None = None):
        """
        Initialize the Synthesizer.
        
        Sets up the Fish Audio SDK client with the provided API key and loads
        reference audio for voice cloning. If no reference audio path is provided,
        uses a default path in the backend directory. Supports hot-reload of
        reference audio files without restarting the service.
        
        Args:
            api_key: Fish Audio API key for authentication.
            reference_audio_path: Optional path to reference audio file for
                voice cloning. If None, uses default path 'backend/reference_audio.wav'.
                The reference audio serves as the "Voice ID" for cloning.
        
        Returns:
            None
        """
        self.client = FishAudio(api_key=api_key)
        
        self.reference_audio_bytes = None
        self._reference_audio_mtime = None
        self._reference_audio_path = None
        
        if reference_audio_path:
            audio_path = reference_audio_path
        else:
            backend_dir = Path(__file__).parent.parent
            default_path = backend_dir / "reference_audio.wav"
            audio_path = str(default_path)
        
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
    
    def _load_reference_audio(self, audio_path: str) -> None:
        """
        Load reference audio file and store its modification time for hot-reload.
        
        Args:
            audio_path: Path to the reference audio file.
        
        Returns:
            None
        """
        try:
            if os.path.exists(audio_path):
                with open(audio_path, 'rb') as f:
                    self.reference_audio_bytes = f.read()
                self._reference_audio_mtime = os.path.getmtime(audio_path)
            else:
                self.reference_audio_bytes = None
                self._reference_audio_mtime = None
        except Exception as e:
            print(f"Warning: Could not load reference audio from {audio_path}: {e}")
            self.reference_audio_bytes = None
            self._reference_audio_mtime = None
    
    def _check_and_reload_reference_audio(self) -> None:
        """
        Check if reference audio file has changed and reload if necessary.
        
        This enables hot-reload without server restart. Also detects if file
        appears for the first time (wasn't present at startup).
        
        Returns:
            None
        """
        if self._reference_audio_path:
            if os.path.exists(self._reference_audio_path):
                current_mtime = os.path.getmtime(self._reference_audio_path)
                if self._reference_audio_mtime is None or self._reference_audio_mtime != current_mtime:
                    self._load_reference_audio(self._reference_audio_path)

    def synthesize(self, packet: JanusPacket) -> bytes:
        """
        Main entry point. Routing logic based on Packet Mode.
        
        Routes synthesis to the appropriate method based on packet mode:
        - MORSE_CODE: Generates sine wave tones
        - TEXT_ONLY: Uses fast TTS with optional emotion override
        - SEMANTIC_VOICE: Uses generative AI with dynamic emotion prompting
        
        Args:
            packet: The deserialized JanusPacket containing text, mode, and metadata.
            
        Returns:
            bytes: Raw PCM audio data ready for PyAudio playback.
        
        Raises:
            ValueError: If packet mode is unknown or unsupported.
        """
        if packet.mode == JanusMode.MORSE_CODE:
            return self._generate_morse_audio(packet.text)
        elif packet.mode == JanusMode.TEXT_ONLY:
            return self._generate_fast_tts(packet.text, packet.override_emotion)
        elif packet.mode == JanusMode.SEMANTIC_VOICE:
            return self._generate_semantic_audio(packet)
        else:
            raise ValueError(f"Unknown packet mode: {packet.mode}")

    def _generate_semantic_audio(self, packet: JanusPacket) -> bytes:
        """
        Generates semantic voice audio using generative AI.
        
        Uses Fish Audio SDK to synthesize speech with emotion tags derived from
        prosody analysis or manual override. Supports voice cloning via reference
        audio when available.
        
        Args:
            packet: JanusPacket containing text, prosody metadata, and optional
                emotion override.
        
        Returns:
            bytes: Raw PCM audio data (WAV format) ready for PyAudio playback.
                Falls back to fast TTS if API call fails.
        """
        self._check_and_reload_reference_audio()
        
        if packet.override_emotion and packet.override_emotion != "Auto":
            prompt = f"({packet.override_emotion}) {packet.text}"
        else:
            prosody = packet.prosody or {}
            pitch = prosody.get('pitch', 'Normal')
            energy = prosody.get('energy', 'Normal')
            
            if pitch == 'High' and energy == 'Loud':
                emotion_tag = "excited"
            elif pitch == 'High' and energy == 'Normal':
                emotion_tag = "joyful"
            elif pitch == 'High' and energy in ('Quiet', 'Low'):
                emotion_tag = "whispering"
            elif pitch == 'Low' and energy == 'Loud':
                emotion_tag = "shouting"
            elif pitch == 'Low' and energy == 'Low':
                emotion_tag = "sad"
            elif pitch == 'Low' and energy == 'Normal':
                emotion_tag = "relaxed"
            elif energy == 'Loud':
                emotion_tag = "shouting"
            elif energy in ('Quiet', 'Low'):
                emotion_tag = "whispering"
            else:
                emotion_tag = "relaxed"
            
            prompt = f"({emotion_tag}) {packet.text}"

        try:
            references = None
            reference_id = None
            
            if self.reference_audio_bytes:
                references = [ReferenceAudio(
                    audio=self.reference_audio_bytes,
                    text=""
                )]
            else:
                reference_id = "5196af35f6ff4a0dbf541793fc9f2157"
            
            print(prompt)
            
            api_params = {
                "text": prompt,
                "format": "wav",
                "latency": "balanced"
            }
            
            if references:
                api_params["references"] = references
            else:
                api_params["reference_id"] = reference_id
            
            audio_bytes = self.client.tts.convert(**api_params)
            return audio_bytes
            
        except Exception as e:
            print(f"Synthesis error: {e}")
            return self._generate_fast_tts(packet.text, packet.override_emotion)

    def _generate_fast_tts(self, text: str, emotion: str | None = None) -> bytes:
        """
        Fallback TTS mode for reduced API cost and latency.
        
        Uses Fish Audio SDK with balanced latency settings. Supports cloned voice
        if reference audio is available, otherwise falls back to generic voice.
        Can be used as a fallback when semantic voice synthesis fails.
        
        Args:
            text: Text string to synthesize.
            emotion: Optional emotion override tag (e.g., "joyful", "panicked").
                If None or "Auto", emotion tag is omitted from the prompt.
        
        Returns:
            bytes: Raw PCM audio data (WAV format) ready for PyAudio playback.
                Returns empty bytes if synthesis fails.
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
                "format": "wav",
                "latency": "balanced"
            }
            
            if self.reference_audio_bytes:
                api_params["references"] = [ReferenceAudio(
                    audio=self.reference_audio_bytes,
                    text=""
                )]
            else:
                api_params["references"] = None
            
            audio_bytes = self.client.tts.convert(**api_params)
            return audio_bytes
        except Exception as e:
            # Return empty audio bytes on error
            print(f"Fast TTS error: {e}")
            return b''

    def _generate_morse_audio(self, text: str) -> bytes:
        """
        Generates Morse code audio from text using sine wave tones.
        
        Converts text characters to Morse code patterns and generates corresponding
        audio tones. Dots (.) produce 0.1s tones, dashes (-) produce 0.3s tones,
        both at 800Hz. Appropriate silence is inserted between symbols, letters,
        and words.
        
        Args:
            text: Text string to convert to Morse code audio.
        
        Returns:
            bytes: Raw PCM audio data (int16 format) ready for PyAudio playback.
                Returns empty bytes if text is empty or contains no valid characters.
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