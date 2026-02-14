# Environment Setup Instructions

## Prerequisites

### System Dependencies (WSL/Ubuntu)

The automated setup script (`backend/setup.sh`) installs all required system dependencies, including:
- Python development headers
- PortAudio library for PyAudio
- Aubio library for prosody extraction
- FFmpeg libraries for audio processing
- Sound file libraries
- Build configuration tools

## Setup

### Automated Setup (Recommended)

Run the automated setup script from the project root:

   ```bash
cd backend
bash setup.sh
   ```

This script will:
1. Install all required system dependencies
2. Create a Python virtual environment
3. Install all Python dependencies from `requirements.txt`

After setup completes, activate the virtual environment:

   ```bash
   source backend/venv/bin/activate
   ```

**Note:** The setup script installs CPU-only PyTorch to avoid downloading 2.5GB CUDA packages. This provides wider hardware compatibility and is sufficient for the Janus system.

### Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install Node.js dependencies**:
   ```bash
   npm install
   ```

## Running the Project

### Backend Server

Start the FastAPI backend server:

```bash
uvicorn backend.server:app --reload
```

The server will start on `http://localhost:8000`. The `--reload` flag enables automatic reloading during development.

### Frontend Development Server

In a separate terminal, start the Next.js development server:

   ```bash
cd frontend
   npm run dev
   ```

The frontend will be available at `http://localhost:3000`.

### Accessing the Application

Open `http://localhost:3000` in your browser to access the Janus interface.

## Environment Variables

Create a `.env` file in the project root with the following variables:

### Required

- **`FISH_AUDIO_API_KEY`**: API key for Fish Audio SDK voice synthesis service. Obtain from your Fish Audio account.

### Optional

- **`RECEIVER_PORT`**: Port for listening to incoming packet transmissions (default: `5005`)
- **`USE_TCP`**: Set to `"true"` to use TCP instead of UDP (default: `false`). Automatically enabled when `TARGET_IP` contains "ngrok"
- **`TARGET_IP`**: Target IP address for outgoing packet transmission (default: `127.0.0.1`). Set to ngrok URL for cross-network connections
- **`TARGET_PORT`**: Target port for outgoing packet transmission (default: `5005`)
- **`REFERENCE_AUDIO_PATH`**: Path to reference audio file for voice cloning (optional)

## Network Configuration (Connecting Machines for Full-Duplex Communication)

The Janus unified backend provides full-duplex audio communication, meaning both machines can simultaneously send and receive audio. Each machine runs the same backend server and can access the web interface to interact with the system.

**Primary Communication Method:** The web interface communicates with the local backend via WebSocket (`ws://localhost:8000/ws/janus`) for real-time control and transcript updates. This is the main interface for user interaction.

**Network Testing (Optional):** The `TARGET_IP` and `TARGET_PORT` environment variables configure the link simulator for testing packet transmission between machines over constrained network connections. This is optional and primarily used for demonstration and testing purposes.

### Local Network Connection

To configure network testing between two machines on the same local network:

**On Machine A:**
- Set `RECEIVER_PORT=5005` in `.env` (this machine will receive packets from Machine B)
- Set `TARGET_IP` to Machine B's local IP address (e.g., `192.168.1.101`)
- Set `TARGET_PORT=5005` (to send packets to Machine B)
- Start the backend: `uvicorn backend.server:app --reload`
- Access web interface: `http://localhost:3000`

**On Machine B:**
- Set `RECEIVER_PORT=5005` in `.env` (this machine will receive packets from Machine A)
- Set `TARGET_IP` to Machine A's local IP address (e.g., `192.168.1.100`)
- Set `TARGET_PORT=5005` (to send packets to Machine A)
- Start the backend: `uvicorn backend.server:app --reload`
- Access web interface: `http://localhost:3000`

Both machines operate as equal peers, each running the full unified backend with simultaneous send and receive capabilities.

### Cross-Network Connection (ngrok)

To connect machines across different networks (e.g., over the internet), use ngrok for TCP tunneling:

**On Machine A:**
1. Install ngrok: `https://ngrok.com/download`
2. Start the backend server
3. Create TCP tunnel: `ngrok tcp 5005`
4. Note the ngrok URL (e.g., `tcp://0.tcp.ngrok.io:12345`)
5. Share this URL with Machine B

**On Machine B:**
1. Set `TARGET_IP=0.tcp.ngrok.io` (Machine A's ngrok host)
2. Set `TARGET_PORT=12345` (Machine A's ngrok port)
3. Start the backend server
4. Create your own ngrok tunnel: `ngrok tcp 5005`
5. Share your ngrok URL with Machine A

**On Machine A (configure to reach Machine B):**
- Update `.env` with Machine B's ngrok URL and port

Both machines can now send and receive audio packets across the internet. The system automatically enables TCP mode when "ngrok" is detected in `TARGET_IP`.

## Notes

- The virtual environment is located at `backend/venv/` and is already in `.gitignore`
- PyAudio requires system-level audio libraries installed before pip installation
- **IMPORTANT**: The setup script installs CPU-only PyTorch to avoid downloading 2.5GB CUDA packages
- faster-whisper will download model files on first use (stored in cache)
- Silero VAD will download model files on first use (stored in cache)
- Fish Audio SDK requires a valid API key with sufficient credits
- The backend server must be running before starting the frontend for WebSocket connections

## Audio Utilities

The `backend/scripts/` directory contains helper utilities for hardware and model verification:

- **`list_audio_devices.py`**: Lists all available PyAudio input and output devices. Use this to find the correct device index if you have multiple audio interfaces.
- **`verify_audio_params.py`**: Verifies that the model's native sample rate matches the output playback rate. Use `--full` to load the model manager for a complete check.
- **`sender_main.py`**: Test script for sending audio packets (requires a running backend receiver).

## Troubleshooting

### Audio Issues

- **No microphone detected**: Ensure microphone is connected and not muted in OS settings
- **PyAudio errors**: Verify system audio libraries are installed (`portaudio19-dev`)
- **Permission errors**: On Linux, ensure user has access to audio devices (may require adding user to `audio` group)

### Network Issues

- **Connection refused**: Verify the target machine's backend is running and the port is correct
- **ngrok connection fails**: Ensure ngrok tunnel is active and URL is correct
- **Packets not received**: Check firewall settings; network traffic may be blocked

### Python Environment Issues

- **Import errors**: Ensure virtual environment is activated (`source backend/venv/bin/activate`)
- **Package not found**: Re-run the automated setup script (`bash backend/setup.sh`)
- **PyTorch CUDA errors**: This is expected with CPU-only installation; ensure you're not importing CUDA-specific modules

### Frontend Issues

- **WebSocket connection fails**: Ensure backend server is running on port 8000
- **Build errors**: Clear `node_modules` and reinstall: `rm -rf node_modules && npm install`
