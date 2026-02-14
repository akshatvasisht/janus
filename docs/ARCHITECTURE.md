# Janus Architecture Documentation

This document provides detailed architectural documentation, design decisions, and a glossary of terms for the Janus semantic audio codec system, which operates at 300 bits per second (bps) through semantic compression.

---

## Glossary of Terms

- **Semantic Codec:** The core concept of Janus - transmitting semantic meaning (text + metadata) rather than raw audio waveforms, enabling communication over extremely constrained bandwidth.

- **Smart Ear:** The unified audio processing engine (`engine.py`) that manages continuous audio capture, VAD gating, transcription, prosody extraction, and packet transmission.

- **Control State:** Shared state object (`engine_state.ControlState`) that holds current mode, streaming/recording flags, and emotion override settings. Updated by WebSocket control messages and read by the Smart Ear engine.

- **Janus Packet:** The binary packet structure (`JanusPacket`) containing text, mode, prosody data, and optional emotion override. Serialized using MessagePack for efficient transmission.

- **Link Simulator:** Module (`link_simulator.py`) that simulates constrained network connections (e.g., 300bps) by throttling packet transmission rates.

- **Engine Loop:** The main processing loop (`smart_ear_loop`) that continuously reads control state, captures audio, processes it through the pipeline, and transmits packets.

- **Receiver Loop:** Background thread (`receiver_loop`) that listens for incoming Janus packets, deserializes them, synthesizes audio, and queues it for playback.

- **Prosody:** The rhythm, stress, and intonation of speech (pitch, volume, speed). Extracted from audio to preserve emotional context.

---

## Repository Structure

```
MadHacks/
├── backend/                        # Python 3.10+ (FastAPI)
│   ├── api/
│   │   ├── endpoints.py            # REST endpoints (/api/health, /api/voice/verify)
│   │   ├── socket_manager.py       # WebSocket handler (ws://localhost:8000/ws/janus)
│   │   └── types.py                # Pydantic models for WebSocket messages
│   ├── common/
│   │   ├── engine_state.py         # Shared control state and event queues
│   │   └── protocol.py             # JanusPacket definition and MessagePack serialization
│   ├── services/
│   │   ├── audio_io.py             # Microphone capture & speaker output (PyAudio)
│   │   ├── engine.py               # Smart Ear engine loop and receiver loop
│   │   ├── vad.py                  # Silero-VAD logic
│   │   ├── transcriber.py          # Faster-Whisper (Int8 quantized)
│   │   ├── prosody.py              # Aubio (Pitch/Energy extraction)
│   │   ├── synthesizer.py          # Qwen3-TTS via ModelManager (local inference)
│   │   ├── model_manager.py        # Qwen3-TTS model loading and generation
│   │   ├── text_processing.py      # SentenceBuffer and text tokenization
│   │   └── link_simulator.py       # Network throttling (300bps simulation)
│   ├── assets/                     # Reference audio (created by setup.sh)
│   │   └── enrollment.wav          # Default voice-clone reference (3s placeholder)
│   ├── scripts/                    # CLI utility scripts
│   │   ├── sender_main.py          # CLI tool for direct network testing (standalone)
│   │   └── receiver_main.py        # CLI tool for direct network testing (standalone)
│   ├── tests/                      # Test suite
│   │   ├── conftest.py             # Pytest fixtures
│   │   ├── test_api_flow.py
│   │   ├── test_e2e_local.py       # End-to-end local pipeline tests
│   │   ├── test_engine.py
│   │   ├── test_input_processing.py
│   │   ├── test_model_loading.py   # Qwen3-TTS ModelManager load/inference
│   │   ├── test_synthesis.py
│   │   ├── test_text_processing.py
│   │   ├── test_transport_layer.py
│   │   ├── test_voice_cloning.py
│   │   ├── hardware_check.py       # Manual hardware verification
│   │   └── manual_sender.py        # Manual packet sender tool
│   ├── server.py                   # Unified backend entry point (FastAPI app)
│   ├── setup.sh                    # Automated setup script
│   └── requirements.txt            # Python dependencies
│
├── frontend/                       # Next.js 14 (React)
│   ├── app/
│   │   ├── page.tsx                # Main user interface (PTT controls)
│   │   ├── layout.tsx              # Root layout
│   │   ├── globals.css             # Global styles
│   │   └── telemetry/
│   │       └── page.tsx            # Bandwidth visualization and packet log
│   ├── components/
│   │   ├── PushToTalk.tsx          # Main interaction button (hold-to-record)
│   │   ├── ModeToggle.tsx          # Transmission mode selector
│   │   ├── EmotionSelector.tsx     # Emotion override selector
│   │   ├── ControlPanel.tsx        # Control panel container
│   │   ├── ConversationPanel.tsx   # Transcript display
│   │   ├── HeaderBar.tsx           # Status header
│   │   ├── QuickStats.tsx          # Packet statistics display
│   │   ├── VoiceCloner.tsx         # Voice reference upload interface
│   │   ├── NetworkLog.tsx          # Packet log for telemetry
│   │   ├── SectionHeader.tsx       # Section headers
│   │   ├── TelemetryGraph.tsx      # Real-time packet/bandwidth chart
│   │   └── ui/                     # Shared UI primitives (e.g. card, button)
│   ├── hooks/
│   │   ├── useJanusSocket.ts       # Main socket hook (mode conversion)
│   │   └── useJanusWebSocket.ts    # WebSocket connection management
│   ├── providers/                  # React context providers
│   ├── lib/                        # Utilities (e.g. cn)
│   ├── types/
│   │   └── janus.ts                # TypeScript type definitions
│   └── assets/                     # Static assets (e.g. logo)
│
├── docs/                           # Documentation directory
│   ├── API.md                      # API documentation
│   ├── ARCHITECTURE.md             # This file
│   ├── SETUP.md                    # Setup instructions
│   ├── TESTING.md                  # Testing guidelines
│   └── STYLE.md                    # Coding standards
├── README.md                       # Project overview
└── LICENSE
```


## Technology Stack

| **Category**           | **Technology**            | **Purpose**                                             | **Rationale**                                                                                 |
| ---------------------- | ------------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| **Frontend Framework** | **React (via Next.js 14)** | User interface (Dashboard, Controls, Transcript Display) | App Router enables rapid development |
| **Styling**            | **Tailwind CSS**          | UI styling (Dark mode, responsive design)            | Rapid prototyping without custom CSS                                      |
| **Visualization**      | **Recharts**              | Real-time data visualization (planned for telemetry)      | Simple, composable React charts                                                  |
| **Backend API**        | **FastAPI**               | REST and WebSocket server                              | Async support for real-time streaming                               |
| **Speech-to-Text**     | **faster-whisper**        | Local speech transcription (Int8 quantized)            | Optimized Whisper runs efficiently on CPU                        |
| **Voice Detection**    | **silero-vad**            | Voice activity detection (gatekeeper)                   | Lightweight and low-latency                            |
| **Prosody Analysis**   | **aubio**                 | Pitch (F0) and energy extraction                        | Real-time audio feature extraction                              |
| **Generative TTS**     | **Qwen3-TTS (ModelManager)** | Voice synthesis from text + metadata (local inference) | Voice reconstruction from semantic data; model loaded via Hugging Face Hub |
| **Audio I/O**          | **PyAudio**               | Microphone capture and speaker playback                 | Lower latency than browser audio          |
| **Protocol**           | **MessagePack**           | Binary serialization of Janus packets                   | Smaller and faster than JSON                        |
| **Network Logic**      | **Python `socket`**       | TCP/UDP socket communication with throttling            | Manual control of transmission rate                            |
| **Communication**      | **WebSockets**            | Real-time bidirectional communication (FastAPI)          | Low latency UI updates                          |

---

## Unified Backend Architecture

The Janus backend uses a unified architecture centered around `server.py`, which provides a single FastAPI application that manages both audio capture and playback through WebSocket connections.

### Core Components

**Server (`server.py`):**
- FastAPI application with lifespan management
- Initializes shared `AudioService` for full-duplex audio
- Launches `smart_ear_loop` as async background task
- Starts `receiver_loop` in separate thread
- Manages graceful shutdown

**Smart Ear Engine (`services/engine.py`):**
- Main processing loop (`smart_ear_loop`) that:
  - Reads control state from `engine_state.control_state`
  - Captures audio chunks via `AudioService`
  - Applies VAD filtering when in streaming mode
  - Transcribes audio using faster-whisper
  - Extracts prosody metadata using aubio
  - Serializes and transmits Janus packets via `LinkSimulator`
  - Pushes transcript and packet events to queues for WebSocket forwarding

**Receiver Loop (`services/engine.py`):**
- Background thread (`receiver_loop`) that:
  - Listens for incoming TCP connections
  - Receives and deserializes Janus packets
  - Tokenizes packet text with `text_processing.iter_text_tokens` and synthesizes per-sentence via `SentenceBuffer` and `Synthesizer` (Qwen3-TTS via ModelManager), flushing at end-of-packet to avoid hanging text
  - Queues PCM audio bytes for playback worker thread
  - Plays audio through `AudioService`

**WebSocket Manager (`api/socket_manager.py`):**
- Handles WebSocket connections at `/ws/janus`
- Receives `ControlMessage` from frontend and updates `control_state`
- Forwards `TranscriptMessage` and `PacketSummaryMessage` from engine queues to frontend
- Manages connection lifecycle and error handling

**Engine State (`common/engine_state.py`):**
- `ControlState`: Shared state object with mode, streaming/recording flags, emotion override
- `transcript_queue`: Async queue for transcript events
- `packet_queue`: Async queue for packet summary events

### Standalone CLI Tools

The repository also includes `scripts/sender_main.py` and `scripts/receiver_main.py` as standalone CLI tools for direct network testing without the web interface. These tools are useful for:
- Testing network connectivity between machines
- Verifying packet transmission and reception
- Debugging network configuration issues
- Manual integration testing

These tools operate independently of the unified backend and do not use WebSocket communication.

---

## Data Flow

### Complete Audio Pipeline

**Sender Side:**
1. **Audio Capture**: `AudioService` continuously reads microphone input chunks
2. **VAD Filtering**: When `is_streaming=True`, audio passes through VAD to detect speech segments
3. **Recording Mode**: When `is_recording=True`, all audio is buffered until flag is cleared
4. **Transcription**: Audio chunks are transcribed to text using faster-whisper
5. **Prosody Extraction**: Pitch (F0) and energy are extracted using aubio
6. **Packet Creation**: `JanusPacket` is created with text, mode, prosody, and emotion override
7. **Serialization**: Packet is serialized using MessagePack
8. **Transmission**: Serialized packet is sent via `LinkSimulator` (with throttling for simulation)

**Receiver Side:**
1. **Network Reception**: `receiver_loop` receives TCP connection and reads packet data
2. **Deserialization**: MessagePack data is deserialized into `JanusPacket`
3. **Text Tokenization**: Packet text is tokenized with `iter_text_tokens` and fed into `SentenceBuffer`
4. **Synthesis**: For each complete sentence (or flush at end-of-packet), Qwen3-TTS via ModelManager synthesizes PCM audio from text + prosody/reference
5. **Playback Queue**: Audio bytes are queued for playback worker
6. **Audio Output**: `AudioService` writes audio chunks to speaker

---

## Transmission Modes

Janus supports three transmission modes (defined in `JanusMode` enum):

1. **SEMANTIC_VOICE (Mode 0)**: Full semantic transmission
   - Includes text + prosody data (pitch, energy)
   - Enables full voice reconstruction with emotional context
   - Higher bandwidth requirement but preserves voice characteristics

2. **TEXT_ONLY (Mode 1)**: Text-only transmission
   - Includes only transcribed text
   - Uses default receiver voice (no prosody)
   - Minimal bandwidth requirement
   - Suitable for bandwidth-constrained scenarios

3. **MORSE_CODE (Mode 2)**: Morse code transmission
   - Converts text to Morse code patterns and generates sine wave audio locally
   - Uses 800 Hz frequency for tone generation
   - Bypasses TTS synthesis

---

## Design Decisions

### Latency/Bitrate Trade-off

The 300 bps target bitrate requires semantic compression (~136 bps payload) instead of acoustic waveform reconstruction, resulting in a walkie-talkie interaction model with 2.8-3.0 second turnaround latency:

- Latency is driven by the need to buffer complete phrases for generative AI (Whisper ASR, Qwen3-TTS).
- Processing starts after 16 consecutive silence chunks (~500ms) to ensure semantic completeness.
- Faster-Whisper uses greedy decoding (beam_size=1) to reduce compute time with minimal accuracy loss.
- Bandwidth efficiency is prioritized over low latency for scenarios where traditional codecs are unsuitable.

### Unified Backend vs. Separate Sender/Receiver

The unified backend architecture (`server.py`) was chosen to:
- Simplify deployment (single process)
- Enable full-duplex communication (simultaneous capture and playback)
- Provide real-time WebSocket updates to frontend
- Centralize state management

The standalone CLI tools (`scripts/sender_main.py`, `scripts/receiver_main.py`) are retained for:
- Network testing and debugging
- Scenarios requiring separate sender/receiver processes
- Integration testing without web interface

### MessagePack Serialization

MessagePack was chosen over JSON for packet serialization because:
- Significantly smaller payload size (critical for 300bps simulation)
- Faster serialization/deserialization
- Binary format reduces parsing overhead
- Maintains compatibility with text-based metadata

### Sentence-Level Synthesis

Receiver synthesis uses `SentenceBuffer` and `iter_text_tokens` so that:
- Text is tokenized into sentence-boundary units and synthesized per-sentence
- End-of-packet flush ensures no text remains buffered when a packet is complete, avoiding “hanging” partial sentences
- The same logic is used in both the unified backend `receiver_loop` and the standalone `receiver_main.py` CLI

### CPU-Only PyTorch

The system defaults to CPU-only PyTorch installation to:
- Support wider hardware compatibility (no GPU required)
- Reduce installation size (avoids 2.5GB CUDA packages)
- Enable operation on standard laptops and development machines

### Int8 Quantization for faster-whisper

Int8 quantization is used for faster-whisper to:
- Reduce memory footprint
- Improve inference speed on CPU
- Maintain acceptable transcription accuracy
- Enable real-time processing on consumer hardware
