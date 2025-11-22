# Environment Setup Instructions

## Prerequisites

### System Dependencies (WSL/Ubuntu)

1. **Python venv module** (required for virtual environment):
   ```bash
   sudo apt install python3.12-venv
   ```

2. **PortAudio** (required for PyAudio):
   ```bash
   sudo apt install portaudio19-dev
   ```

## Python Backend Setup

1. **Create virtual environment** (if not already created):
   ```bash
   python3 -m venv backend/venv
   ```

2. **Activate virtual environment**:
   ```bash
   source backend/venv/bin/activate
   ```

3. **Install CPU-only PyTorch first** (to avoid 2.5GB CUDA download):
   ```bash
   pip install torch --index-url https://download.pytorch.org/whl/cpu
   ```

4. **Install remaining Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install Node.js dependencies**:
   ```bash
   npm install
   ```

3. **Run development server**:
   ```bash
   npm run dev
   ```

## Environment Variables

Create a `.env` file in the project root with:
```
FISH_AUDIO_API_KEY=your_api_key_here
```

## Notes

- The virtual environment is located at `backend/venv/` and is already in `.gitignore`
- PyAudio requires system-level audio libraries installed before pip installation
- **IMPORTANT**: Install CPU-only PyTorch before other dependencies to avoid downloading 2.5GB CUDA packages
- faster-whisper will download model files on first use
- Silero VAD will download model files on first use
- Fish Audio SDK may have specific installation requirements

