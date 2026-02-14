"""
Integration tests for the Qwen3-TTS ModelManager.

These tests are intentionally minimal and can be expensive because they load
the full ~1GB model weights. By default they are skipped unless the
ENABLE_QWEN3_TTS_TESTS environment variable is set.
"""

from __future__ import annotations

import os

import pytest

from backend.services.model_manager import ModelManager


skip_slow_tts = pytest.mark.skipif(
    not os.getenv("ENABLE_QWEN3_TTS_TESTS"),
    reason="Qwen3-TTS tests are disabled by default. "
    "Set ENABLE_QWEN3_TTS_TESTS=1 to enable.",
)


def test_model_manager_singleton(monkeypatch) -> None:
    """
    Verify that ModelManager behaves as a singleton.

    This test does not require the heavy model weights to load twice; the
    second construction should return the same instance.
    """
    # Ensure this test stays lightweight (no model download / init).
    monkeypatch.setenv("JANUS_QWEN3_TTS_DRY_RUN", "1")

    # Reset singleton state to avoid test order coupling.
    ModelManager._instance = None
    ModelManager._initialized = False

    m1 = ModelManager()
    m2 = ModelManager()
    assert m1 is m2

    # Cleanup for any subsequent tests in the same process.
    ModelManager._instance = None
    ModelManager._initialized = False


@skip_slow_tts
def test_model_loading_and_inference() -> None:
    """
    Load the Qwen3-TTS model and run a basic inference.

    Verifies that:
    - The model loads without raising exceptions.
    - `generate()` returns non-empty int16 PCM bytes for simple text.
    """
    ModelManager._instance = None
    ModelManager._initialized = False

    manager = ModelManager()
    audio_bytes = manager.generate("Hello world from Janus.")

    assert isinstance(audio_bytes, (bytes, bytearray))
    # Require a minimal length to ensure we didn't just get an empty buffer.
    assert len(audio_bytes) > 1000

