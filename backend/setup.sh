#!/bin/bash

set -e

# Resolve paths relative to this script (backend/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export SCRIPT_DIR

# Hugging Face Hub uses symlinks by default for cache snapshots. In some
# environments (notably certain container/sandbox/WSL setups), symlinks can fail
# and leave snapshot directories empty. Export this for all shell tooling.
export HF_HUB_DISABLE_SYMLINKS="${HF_HUB_DISABLE_SYMLINKS:-1}"

echo "--- [1/4] Installing System Dependencies (Requires Sudo) ---"
# Update apt and install the C headers required for compilation
sudo apt update
sudo apt install -y git sox python3-dev python3-venv portaudio19-dev libaubio-dev libavcodec-dev libavformat-dev libavutil-dev libswresample-dev libsndfile1-dev pkg-config

echo "--- [2/4] Creating Python Virtual Environment ---"
# Remove old venv if it exists to ensure a clean state
rm -rf venv
python3 -m venv venv

# Ensure the env var is set whenever the venv is activated (idempotent)
if ! grep -q "HF_HUB_DISABLE_SYMLINKS" "venv/bin/activate"; then
  echo "" >> "venv/bin/activate"
  echo "# Ensure HF Hub downloads do not rely on symlinks." >> "venv/bin/activate"
  echo "export HF_HUB_DISABLE_SYMLINKS=1" >> "venv/bin/activate"
fi

source venv/bin/activate

echo "--- [3/4] Installing Python Libraries ---"
# Upgrade pip first to avoid wheel errors
pip install --upgrade pip
pip install -r "${SCRIPT_DIR}/requirements.txt"

echo "--- [4/4] Ensuring Default Reference Audio Asset Exists ---"
# Qwen3-TTS voice cloning requires a reference clip. We generate a small 3s 440Hz
# placeholder so local tests and startup don't fail on a missing asset.
python3 - <<'PY'
from pathlib import Path
import os
import numpy as np
import soundfile as sf

backend_dir = Path(os.environ["SCRIPT_DIR"]).resolve()
assets_dir = backend_dir / "assets"
assets_dir.mkdir(parents=True, exist_ok=True)

out_path = assets_dir / "enrollment.wav"
if not out_path.exists():
    sr = 44100
    duration_s = 3.0
    t = np.linspace(0.0, duration_s, int(sr * duration_s), endpoint=False)
    wave = (0.2 * np.sin(2.0 * np.pi * 440.0 * t)).astype(np.float32)
    sf.write(str(out_path), wave, sr, subtype="PCM_16")
    print(f"Generated placeholder reference audio at: {out_path}")
else:
    print(f"Reference audio already exists at: {out_path}")
PY

echo "--- Setup Complete! ---"
echo "Next (run from project root, one level above backend/):"
echo "  cd .."
echo "  source backend/venv/bin/activate"
echo "  pytest backend/tests/ -q"
echo "Optional slow test (loads Qwen3-TTS on CPU):"
echo "  CUDA_VISIBLE_DEVICES=\"\" ENABLE_QWEN3_TTS_TESTS=1 pytest backend/tests/test_model_loading.py::test_model_loading_and_inference -v"