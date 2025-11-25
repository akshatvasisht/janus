#!/bin/bash

set -e

echo "--- [1/3] Installing System Dependencies (Requires Sudo) ---"
# Update apt and install the C headers required for compilation
sudo apt update
sudo apt install -y python3-dev portaudio19-dev libaubio-dev libavcodec-dev libavformat-dev libavutil-dev libswresample-dev libsndfile1-dev pkg-config

echo "--- [2/3] Creating Python Virtual Environment ---"
# Remove old venv if it exists to ensure a clean state
rm -rf venv
python3 -m venv venv
source venv/bin/activate

echo "--- [3/3] Installing Python Libraries ---"
# Upgrade pip first to avoid wheel errors
pip install --upgrade pip
# Resolve requirements.txt path relative to script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
pip install -r "${SCRIPT_DIR}/requirements.txt"

echo "--- Setup Complete! Run 'source venv/bin/activate' to start. ---"