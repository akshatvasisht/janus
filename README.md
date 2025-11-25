# Janus - Real-Time Semantic Audio Codec

Janus is a real-time semantic audio codec system designed to optimize bandwidth by transmitting semantic meaning rather than raw audio waveforms. Instead of sending compressed audio data, Janus converts speech to text, extracts prosodic metadata (pitch and energy), and reconstructs the voice on the receiver side using generative text-to-speech synthesis.

## Overview

Janus operates on the principle that semantic information (text + emotional metadata) can be transmitted over extremely constrained network connections (as low as 300bps), then reconstructed into natural-sounding speech using modern generative TTS models. This approach enables high-quality voice communication over bandwidth-limited links where traditional audio codecs would fail.

## Architecture

Janus consists of three main components:

- **Frontend**: Next.js 14 React application providing the user interface for push-to-talk interaction, mode selection, and real-time transcript visualization
- **Backend**: FastAPI server orchestrating the audio processing pipeline, managing WebSocket connections, and coordinating the Smart Ear engine
- **Services Layer**: Specialized modules handling audio I/O, voice activity detection, speech-to-text transcription, prosody extraction, and voice synthesis

The system uses a unified backend architecture (`server.py`) that manages both audio capture and playback through WebSocket connections to the frontend, enabling real-time bidirectional communication.

## Quick Start

1. **Setup**: Follow the instructions in [SETUP.md](SETUP.md) to install dependencies and configure the environment
2. **Run Backend**: Start the FastAPI server with `uvicorn backend.server:app --reload`
3. **Run Frontend**: Start the Next.js development server with `cd frontend && npm run dev`
4. **Access**: Open `http://localhost:3000` in your browser

For detailed setup instructions, see [SETUP.md](SETUP.md).

## Project Structure

```
MadHacks/
├── backend/                    # Python FastAPI backend
│   ├── api/                    # REST endpoints and WebSocket handlers
│   ├── common/                 # Shared protocol and state management
│   ├── services/               # Audio processing services
│   │   ├── audio_io.py         # Microphone capture and speaker output
│   │   ├── engine.py           # Smart Ear engine loop
│   │   ├── vad.py              # Voice activity detection
│   │   ├── transcriber.py      # Speech-to-text
│   │   ├── prosody.py          # Prosody extraction
│   │   ├── synthesizer.py      # Voice synthesis
│   │   └── link_simulator.py   # Network simulation
│   ├── server.py               # Unified backend entry point
│   └── tests/                  # Test suite
├── frontend/                   # Next.js React frontend
│   ├── app/                    # Next.js app router pages
│   ├── components/             # React UI components
│   ├── hooks/                  # Custom React hooks
│   └── types/                  # TypeScript type definitions
├── requirements.txt            # Python dependencies
└── SETUP.md                    # Setup instructions
```

## Documentation

- **[SETUP.md](SETUP.md)**: Environment setup and installation instructions
- **[docs/projectdocs.md](docs/projectdocs.md)**: Detailed architecture documentation and glossary
- **[docs/API.md](docs/API.md)**: WebSocket and REST API documentation
- **[docs/TESTING.md](docs/TESTING.md)**: Testing guidelines and procedures
- **[docs/STYLE.md](docs/STYLE.md)**: Coding standards and style guide

## Usage

The Janus interface provides two interaction modes:

- **Hold-to-Record**: Press and hold the push-to-talk button to capture audio, then release to send
- **Stream Mode**: Toggle streaming to continuously process audio based on voice activity detection

Users can select transmission modes:
- **Semantic Voice**: Transmits text + prosody data for full voice reconstruction
- **Text Only**: Transmits only text, using default receiver voice (bandwidth optimized)
- **Morse Code**: Emergency communication using audio tone generation (800 Hz)

## Key Technologies

- **Frontend**: Next.js 14, React, Tailwind CSS, Recharts
- **Backend**: FastAPI, Python 3.10+
- **Audio Processing**: PyAudio, faster-whisper, silero-vad, aubio
- **Voice Synthesis**: Fish Audio SDK
- **Protocol**: MessagePack for efficient serialization
- **Communication**: WebSockets for real-time updates

## License

See LICENSE file for details.
