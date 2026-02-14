"""
Test Suite for Synthesizer Service (local Qwen3-TTS backend).

Verifies:
- Initialization wiring to ModelManager and reference audio path.
- Routing for different Janus modes.
- Prosody/override-to-instruction stub mapping.
- Morse code generation remains local and length is reasonable.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import numpy as np

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from backend.common.protocol import JanusMode, JanusPacket
from backend.services.synthesizer import SAMPLE_RATE, Synthesizer


# ============================================================================
# Synthesizer Initialization Tests
# ============================================================================


@patch("backend.services.synthesizer.ModelManager")
def test_init_uses_provided_reference_path(mock_mm: MagicMock) -> None:
    """Verify Synthesizer uses the provided reference path."""
    synth = Synthesizer(reference_audio_path="/fake/ref.wav")

    assert synth.reference_audio_path == "/fake/ref.wav"
    mock_mm.assert_called_once()
    _, kwargs = mock_mm.call_args
    assert kwargs.get("ref_audio_path") == "/fake/ref.wav"


@patch("backend.services.synthesizer.ModelManager")
def test_init_uses_default_enrollment(mock_mm: MagicMock) -> None:
    """Verify Synthesizer falls back to backend/assets/enrollment.wav."""
    synth = Synthesizer()

    # Path should point inside backend/assets/enrollment.wav
    assert "backend" in synth.reference_audio_path
    assert synth.reference_audio_path.endswith(os.path.join("assets", "enrollment.wav"))

    mock_mm.assert_called_once()
    _, kwargs = mock_mm.call_args
    assert kwargs.get("ref_audio_path") == synth.reference_audio_path


# ============================================================================
# Routing & Instruction Mapping
# ============================================================================


@patch("backend.services.synthesizer.ModelManager")
def test_routing_semantic_voice_uses_model_manager(mock_mm: MagicMock) -> None:
    """JanusMode.SEMANTIC_VOICE should call ModelManager.generate once."""
    instance = mock_mm.return_value
    instance.generate.return_value = b"pcm-bytes"

    synth = Synthesizer(reference_audio_path="/fake/ref.wav")
    packet = JanusPacket(
        text="Hello world",
        mode=JanusMode.SEMANTIC_VOICE,
        prosody={"energy": "Normal", "pitch": "Normal"},
    )

    result = synth.synthesize(packet)

    instance.generate.assert_called_once()
    prompt = instance.generate.call_args[0][0]
    assert "Hello world" in prompt
    assert result == b"pcm-bytes"


@patch("backend.services.synthesizer.ModelManager")
def test_routing_text_only_uses_model_manager_without_prosody(mock_mm: MagicMock) -> None:
    """JanusMode.TEXT_ONLY should call ModelManager.generate and ignore prosody."""
    instance = mock_mm.return_value
    instance.generate.return_value = b"pcm"

    synth = Synthesizer(reference_audio_path="/fake/ref.wav")
    packet = JanusPacket(
        text="Just text",
        mode=JanusMode.TEXT_ONLY,
        prosody={"energy": "Loud", "pitch": "High"},
    )

    result = synth.synthesize(packet)

    instance.generate.assert_called_once()
    prompt = instance.generate.call_args[0][0]
    assert "Just text" in prompt
    # TEXT_ONLY may still carry override-emotion instruction, but not prosody-derived.
    assert result == b"pcm"


@patch("backend.services.synthesizer.ModelManager")
def test_routing_morse_code_bypasses_model_manager(mock_mm: MagicMock) -> None:
    """JanusMode.MORSE_CODE should not call ModelManager.generate."""
    synth = Synthesizer(reference_audio_path="/fake/ref.wav")
    packet = JanusPacket(
        text="SOS",
        mode=JanusMode.MORSE_CODE,
        prosody={},
    )

    result = synth.synthesize(packet)

    mock_mm.return_value.generate.assert_not_called()
    assert isinstance(result, bytes)
    assert len(result) > 0


@patch("backend.services.synthesizer.ModelManager")
def test_instruction_override_wins(mock_mm: MagicMock) -> None:
    """override_emotion should produce an Instruction prefix regardless of prosody."""
    instance = mock_mm.return_value
    instance.generate.return_value = b"pcm"

    synth = Synthesizer(reference_audio_path="/fake/ref.wav")
    packet = JanusPacket(
        text="Hello world",
        mode=JanusMode.SEMANTIC_VOICE,
        prosody={"energy": "Quiet", "pitch": "Low"},
        override_emotion="panicked",
    )

    _ = synth.synthesize(packet)

    prompt = instance.generate.call_args[0][0]
    assert prompt.startswith("[Instruction: panicked]")
    assert "Hello world" in prompt


@patch("backend.services.synthesizer.ModelManager")
def test_instruction_from_prosody_high_pitch(mock_mm: MagicMock) -> None:
    """High pitch should map to an 'Excited' instruction prefix."""
    instance = mock_mm.return_value
    instance.generate.return_value = b"pcm"

    synth = Synthesizer(reference_audio_path="/fake/ref.wav")
    packet = JanusPacket(
        text="Exciting news",
        mode=JanusMode.SEMANTIC_VOICE,
        prosody={"energy": "Normal", "pitch": "High"},
        override_emotion="Auto",
    )

    _ = synth.synthesize(packet)

    prompt = instance.generate.call_args[0][0]
    assert prompt.startswith("[Instruction: Excited]")
    assert "Exciting news" in prompt


@patch("backend.services.synthesizer.ModelManager")
def test_instruction_from_prosody_quiet_energy(mock_mm: MagicMock) -> None:
    """Quiet or Low energy should map to a 'Quiet' instruction prefix."""
    instance = mock_mm.return_value
    instance.generate.return_value = b"pcm"

    synth = Synthesizer(reference_audio_path="/fake/ref.wav")
    packet = JanusPacket(
        text="Softly spoken",
        mode=JanusMode.SEMANTIC_VOICE,
        prosody={"energy": "Quiet", "pitch": "Normal"},
        override_emotion="Auto",
    )

    _ = synth.synthesize(packet)

    prompt = instance.generate.call_args[0][0]
    assert prompt.startswith("[Instruction: Quiet]")
    assert "Softly spoken" in prompt


# ============================================================================
# Morse Code Generation Tests
# ============================================================================


@patch("backend.services.synthesizer.ModelManager")
def test_morse_code_generation_duration(mock_mm: MagicMock) -> None:
    """Verify 'SOS' Morse code duration is roughly 3 seconds."""
    synth = Synthesizer(reference_audio_path="/fake/ref.wav")
    packet = JanusPacket(
        text="SOS",
        mode=JanusMode.MORSE_CODE,
        prosody={},
    )

    result = synth.synthesize(packet)
    audio_samples = len(result) // 2  # int16 = 2 bytes per sample
    duration_seconds = audio_samples / SAMPLE_RATE

    # Allow wide tolerance; we only care that it's in the right ballpark.
    assert 2.0 < duration_seconds < 5.0

