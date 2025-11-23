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
SAMPLE_RATE = 16000  # Hz
MORSE_FREQUENCY = 800  # Hz for Morse code beeps

# Import Fish Audio SDK
from fish_audio_sdk import Session, TTSRequest, ReferenceAudio

# Import Numpy (for Morse Code math)
import numpy as np

# Import Enum (JanusMode)
from common.protocol import JanusMode

class Synthesizer:
    def __init__(self, api_key, reference_audio_path=None):
        """
        Initialize the Synthesizer.
        1. Setup Fish Audio Session with API Key.
        2. Load the 'Reference Audio' file into memory (bytes).
           - This is the "Voice ID" we are cloning.
           - If no file provided, use a default system ID.
        3. Define Morse Code Dictionary (A=.-, B=-..., etc).
        """
        # Initialize Fish Audio SDK session
        self.session = Session(api_key)
        
        # FIX: Initialize the attribute explicitly
        self.reference_audio_bytes = None
        
        # Load reference audio if provided (only if successful)
        if reference_audio_path:
            try:
                with open(reference_audio_path, 'rb') as f:
                    self.reference_audio_bytes = f.read()
            except Exception as e:
                print(f"Warning: Could not load reference audio from {reference_audio_path}: {e}")
        
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
            return self._generate_fast_tts(packet.text)
        elif packet.mode == JanusMode.SEMANTIC_VOICE:
            return self._generate_semantic_audio(packet)
        else:
            raise ValueError(f"Unknown packet mode: {packet.mode}")

    def _generate_semantic_audio(self, packet):
        """
        The Core Feature: Generative AI Voice.
        """
        # 1. CONSTRUCT PROMPT
        #    Determine the "Emotion Tag" to prepend to the text.
        if packet.override_emotion and packet.override_emotion != "Auto":
            # Logic A (Manual Override):
            prompt = f"[{packet.override_emotion}] {packet.text}"
        else:
            # Logic B (Auto/Prosody Map):
            prosody = packet.prosody or {}
            pitch = prosody.get('pitch', 'Normal')
            energy = prosody.get('energy', 'Normal')
            
            # Map combination to emotion tags
            if pitch == 'High' and energy == 'Loud':
                emotion_tag = "Excited"
            elif pitch == 'High' and energy == 'Normal':
                emotion_tag = "Happy"
            elif pitch == 'Low' and energy == 'Low':
                emotion_tag = "Serious"
            elif pitch == 'Low' and energy == 'Normal':
                emotion_tag = "Calm"
            else:
                emotion_tag = "Neutral"
            
            prompt = f"[{emotion_tag}] {packet.text}"

        # 2. CALL FISH AUDIO API
        try:
            # Create ReferenceAudio if we have reference bytes
            reference = None
            if self.reference_audio_bytes:
                reference = ReferenceAudio(self.reference_audio_bytes)
            
            # Create TTSRequest
            request = TTSRequest(
                text=prompt,
                reference=reference,
                format="pcm",
                latency="balanced"
            )
            
            # Call API and collect result
            result = self.session.synthesize(request)
            
            # Handle iterator or bytes response
            if hasattr(result, '__iter__') and not isinstance(result, bytes):
                # Collect bytes from iterator
                audio_bytes = b''.join(result)
            else:
                audio_bytes = result
            
            return audio_bytes
            
        except Exception as e:
            # Fallback to fast TTS on API error
            return self._generate_fast_tts(packet.text)

    def _generate_fast_tts(self, text):
        """
        Fallback mode. Saves API credits/latency.
        Could use a cheaper Fish Audio model or a local system TTS.
        For the Hackathon, calling Fish Audio without a Reference ID (Generic Voice) is fine.
        """
        try:
            # Create TTSRequest without reference (generic voice)
            request = TTSRequest(
                text=text,
                reference=None,
                format="pcm",
                latency="balanced"
            )
            
            # Call API and collect result
            result = self.session.synthesize(request)
            
            # Handle iterator or bytes response
            if hasattr(result, '__iter__') and not isinstance(result, bytes):
                # Collect bytes from iterator
                audio_bytes = b''.join(result)
            else:
                audio_bytes = result
            
            return audio_bytes
        except Exception as e:
            # Return empty audio bytes on error
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