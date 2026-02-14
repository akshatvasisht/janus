"""Synthesizer service.

Converts a `JanusPacket` (text + optional metadata) into **raw int16 PCM bytes**,
compatible with `AudioService.write_chunk()`.

This is the local-only implementation using Qwen3-TTS via `ModelManager`.
"""

import logging
from pathlib import Path

import numpy as np

from ..common.protocol import JanusMode, JanusPacket
from .model_manager import ModelManager

logger = logging.getLogger(__name__)

# Audio format constants
SAMPLE_RATE = 44100  # Hz
MORSE_FREQUENCY = 800  # Hz for Morse code beeps


class Synthesizer:
    """
    Packet-to-audio synthesizer.

    - `SEMANTIC_VOICE`: local Qwen3-TTS with a lightweight instruction prefix (stub).
    - `TEXT_ONLY`: local Qwen3-TTS without prosody-driven instructions.
    - `MORSE_CODE`: local sine-wave beep synthesis.
    """

    def __init__(self, reference_audio_path: str | None = None) -> None:
        """
        Initialize the synthesizer with optional reference audio for voice cloning.

        Args:
            reference_audio_path: Path to enrollment WAV; if None, uses backend/assets/enrollment.wav.
        """
        if reference_audio_path:
            self.reference_audio_path = reference_audio_path
        else:
            backend_dir = Path(__file__).resolve().parent.parent
            self.reference_audio_path = str(backend_dir / "assets" / "enrollment.wav")

        # Singleton model manager (loads once, shared across Synthesizer instances).
        # Unit tests should patch ModelManager.generate (or set JANUS_QWEN3_TTS_DRY_RUN=1).
        self.model_manager = ModelManager(ref_audio_path=self.reference_audio_path)

        # Define Morse Code Dictionary (A=.-, B=-..., etc)
        self.morse_code_dict = {
            "A": ".-",
            "B": "-...",
            "C": "-.-.",
            "D": "-..",
            "E": ".",
            "F": "..-.",
            "G": "--.",
            "H": "....",
            "I": "..",
            "J": ".---",
            "K": "-.-",
            "L": ".-..",
            "M": "--",
            "N": "-.",
            "O": "---",
            "P": ".--.",
            "Q": "--.-",
            "R": ".-.",
            "S": "...",
            "T": "-",
            "U": "..-",
            "V": "...-",
            "W": ".--",
            "X": "-..-",
            "Y": "-.--",
            "Z": "--..",
            "0": "-----",
            "1": ".----",
            "2": "..---",
            "3": "...--",
            "4": "....-",
            "5": ".....",
            "6": "-....",
            "7": "--...",
            "8": "---..",
            "9": "----.",
            " ": " ",  # Space between words
        }

    def synthesize(self, packet: JanusPacket) -> bytes:
        """
        Generate PCM audio bytes for a packet.

        Args:
            packet: JanusPacket with text, mode, and optional prosody/override_emotion.

        Returns:
            Raw int16 PCM bytes at 44.1kHz, suitable for AudioService.write_chunk().
        """
        if packet.mode == JanusMode.MORSE_CODE:
            return self._generate_morse_audio(packet.text)

        if packet.mode == JanusMode.TEXT_ONLY:
            instruction = None
            if packet.override_emotion and packet.override_emotion != "Auto":
                instruction = f"[Instruction: {packet.override_emotion}] "
            return self._generate_local_tts(packet.text, instruction=instruction)

        if packet.mode == JanusMode.SEMANTIC_VOICE:
            instruction = self._instruction_from_packet(packet)
            return self._generate_local_tts(packet.text, instruction=instruction)

        raise ValueError(f"Unknown packet mode: {packet.mode}")

    def _instruction_from_packet(self, packet: JanusPacket) -> str | None:
        """
        Phase 3.2 stub prosody mapping. Qwen3-TTS supports instruct/voice_design,
        but the schema can vary; we use a plain-text prefix for now.
        """
        if packet.override_emotion and packet.override_emotion != "Auto":
            return f"[Instruction: {packet.override_emotion}] "

        prosody = packet.prosody or {}
        pitch = prosody.get("pitch", "Normal")
        energy = prosody.get("energy", "Normal")

        # Approximate PLAN.md heuristic using categorical tags:
        # - High pitch => excited
        # - Low/quiet energy => quiet
        if pitch == "High":
            return "[Instruction: Excited] "
        if energy in ("Quiet", "Low"):
            return "[Instruction: Quiet] "
        return None

    def _generate_local_tts(self, text: str, *, instruction: str | None) -> bytes:
        """
        Local Qwen3-TTS generation. Returns raw int16 PCM bytes at 44.1kHz.
        """
        prompt = (f"{instruction or ''}{text}").strip()
        if not prompt:
            return b""

        try:
            return self.model_manager.generate(prompt, ref_audio_path=self.reference_audio_path)
        except Exception as exc:
            logger.error("Local TTS synthesis error: %s", exc)
            return b""

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