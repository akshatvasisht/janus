#!/usr/bin/env python3
"""
Verify Qwen3-TTS audio parameters (model sample rate vs output sample rate).

Uses a lightweight path by default: loads only the model config (no weights)
to read sampling_rate. Optionally runs full verification by loading the
ModelManager and inferring model_sample_rate at runtime.

generate() in model_manager.py resamples output with librosa.resample when
native_sr != target_sr so that playback matches AudioService (44.1 kHz).
"""

from __future__ import annotations

import argparse
import json
import sys

# Default model ID; must match ModelManager default.
DEFAULT_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
DEFAULT_OUTPUT_SR = 44_100


def _config_from_hub(model_id: str) -> dict:
    """Load config.json from Hugging Face Hub without loading model weights."""
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        raise ImportError(
            "huggingface_hub is required for lightweight verification. "
            "Install with: pip install huggingface_hub"
        ) from None
    repo_id = model_id
    filename = "config.json"
    path = hf_hub_download(repo_id=repo_id, filename=filename)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_config_sample_rate(model_id: str) -> int | None:
    """
    Read the model's native sample rate from its config on the Hub.

    Args:
        model_id: Hugging Face model ID (e.g. Qwen/Qwen3-TTS-12Hz-0.6B-Base).

    Returns:
        Sample rate in Hz from config, or None if not found.
    """
    config = _config_from_hub(model_id)
    for key in ("sampling_rate", "sample_rate", "audio_sample_rate"):
        val = config.get(key)
        if isinstance(val, int) and val > 0:
            return val
    return None


def run_lightweight(model_id: str, output_sr: int) -> None:
    """Print config-derived sample rate and target output rate (no model load)."""
    print(f"Model ID: {model_id}")
    print(f"Target output sample rate (AudioService): {output_sr} Hz")
    try:
        sr = get_config_sample_rate(model_id)
        if sr is not None:
            print(f"Config sampling_rate (from Hub): {sr} Hz")
            if sr != output_sr:
                print(
                    "  -> generate() resamples model output to output_sample_rate "
                    "via librosa.resample (model_manager.py)."
                )
        else:
            print("Config sampling_rate: not found in config.json; runtime uses _infer_model_sample_rate().")
    except Exception as e:
        print(f"Lightweight config read failed: {e}")
        sys.exit(1)


def run_full(model_id: str, output_sr: int) -> None:
    """Load ModelManager and print inferred model_sample_rate and output_sample_rate."""
    # Avoid importing ModelManager at module level so lightweight path has no heavy deps.
    from backend.services.model_manager import ModelManager

    # Reset singleton so we get a fresh manager with the desired params.
    ModelManager._instance = None
    ModelManager._initialized = False
    manager = ModelManager(model_id=model_id, output_sample_rate=output_sr)
    print(f"Model ID: {model_id}")
    print(f"Target output sample rate (AudioService): {manager.output_sample_rate} Hz")
    print(f"Inferred model native sample rate: {manager.model_sample_rate} Hz")
    if manager.model_sample_rate != manager.output_sample_rate:
        print(
            "  -> generate() resamples model output to output_sample_rate "
            "via librosa.resample (model_manager.py)."
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify Qwen3-TTS audio sample rate vs output (playback) rate."
    )
    parser.add_argument(
        "--model-id",
        default=DEFAULT_MODEL_ID,
        help="Hugging Face model ID (default: %(default)s).",
    )
    parser.add_argument(
        "--output-sr",
        type=int,
        default=DEFAULT_OUTPUT_SR,
        help="Target playback sample rate in Hz (default: %(default)s).",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Load full ModelManager and infer model_sample_rate at runtime (slow).",
    )
    args = parser.parse_args()

    if args.full:
        run_full(args.model_id, args.output_sr)
    else:
        run_lightweight(args.model_id, args.output_sr)


if __name__ == "__main__":
    main()
