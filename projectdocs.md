# Implementation

### **Glossary of Terms**

- **VAD (Voice Activity Detection):** A software module (using `silero-vad`) that detects when a person is speaking versus silence. It acts as a gatekeeper to ensure we only process audio when necessary.
- **STT (Speech-to-Text):** The process of converting spoken audio into text strings. We will use `faster-whisper` (a highly optimized local model) for this.
- **TTS (Text-to-Speech):** The process of generating audio from text. We will use the **Fish Audio SDK** to "hallucinate" the voice back into existence.
- **Prosody:** The rhythm, stress, and intonation of speech (pitch, volume, speed).
- **Aubio:** A lightweight library used to extract pitch (F0) and energy from audio in real-time.
- **MessagePack (MsgPack):** A binary serialization format (like JSON, but much smaller/faster) used to package our data for transmission.
- **Audio Ducking:** A technique where the volume of one audio stream is automatically lowered when another stream starts playing (used for allowing interruptions).
- **F0 (Fundamental Frequency):** The primary frequency of the voice, perceived as "pitch."

---

### Repo Map

/project-janus
├── /backend # Python 3.10+ (FastAPI)
│ ├── /services

│ │ ├── audio_io.py # Mic capture & Speaker output
│ │ ├── [vad.py](http://vad.py/) # Silero-VAD logic
│ │ ├── [transcriber.py](http://transcriber.py/) # Faster-Whisper (Int8)
│ │ ├── [prosody.py](http://prosody.py/) # Aubio (Pitch/Energy)
│ │ ├── [synthesizer.py](http://synthesizer.py/) # Fish Audio SDK
│ │ └── link_simulator.py # Handles the 300bps throttle.
│ ├── /common

│ │ └── [protocol.py](http://protocol.py/) # MessagePack serialization
│ ├── /api

│ │ ├── [endpoints.py](http://endpoints.py/) # REST routes
│ │ └── socket_manager.py # WebSocket: Pushes data to BOTH /app and /telemetry
│ ├── sender_main.py

│ └── receiver_main.py

│
├── /frontend # Next.js 14 (React)
│ ├── /app

│ │ ├── page.tsx # The Clean "User" Interface (PTT Button)
│ │ ├── /telemetry # NEW: The "Demo" Interface (Graphs/Logs)
│ │ │ └── page.tsx

│ │ └── layout.tsx

│ ├── /components

│ │ ├── PushToTalk.tsx # The main interaction button
│ │ ├── ModeToggle.tsx # Text-Only / Semantic Voice toggle
│ │ ├── TelemetryGraph.tsx # Recharts component (used only in /telemetry)
│ │ └── NetworkLog.tsx # Scrolling terminal of packet sizes
│ └── /hooks

│ └── useJanusSocket.ts # Connects UI to Python backend
│
├── requirements.txt

└── package.json

---

### Tech Stack

| **Category**           | **Technology**            | **Purpose**                                             | **Why?**                                                                                 |
| ---------------------- | ------------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| **Frontend Framework** | **React (via Next.js)**   | The "Smart Interface" (Dashboard, Buttons, Visualizer). | Strong conventions (App Router) help Cursor/Antigravity generate code with fewer errors. |
| **Styling**            | **Tailwind CSS**          | Styling the UI (Dark mode, critical alerts).            | Rapid prototyping without writing custom CSS files.                                      |
| **Visualization**      | **Recharts**              | Rendering the real-time "Bandwidth vs Cost" graph.      | Simple, composable React chart library.                                                  |
| **Backend API**        | **FastAPI**               | Connecting React to the Python core via WebSockets.     | Async support is critical for real-time streaming updates.                               |
| **Speech-to-Text**     | **faster-whisper**        | The "Ear" (Converts speech to text locally).            | Optimized version of Whisper; runs fast on CPU (good on laptops).                        |
| **Voice Detection**    | **silero-vad**            | The "Gatekeeper" (Detects speech vs silence).           | Extremely lightweight and low-latency compared to WebRTC VAD.                            |
| **Prosody Analysis**   | **aubio**                 | Extracting Pitch (F0) and Energy.                       | Real-time C-library optimized for audio feature extraction.                              |
| **Generative TTS**     | **Fish Audio SDK**        | The "Throat" (Reconstructs voice from text + metadata). | The core novelty; handles the "Hallucination" of the voice.                              |
| **Audio I/O**          | **PyAudio**               | Capturing raw mic data & playing output audio.          | Lower latency and more reliable than browser-based audio for Python processing.          |
| **Protocol**           | **MessagePack**           | Serializing the data payload (The "Packet").       | Binary format that is significantly smaller and faster than JSON.                        |
| **Network Logic**      | **Python `socket`**       | Simulating the 300bps connection.                       | Native library allows manual control of the "Sleep" throttle.                            |
| **Communication**      | **Socket.io** (or raw WS) | Sending status updates from Python to React.            | Low latency communication to update the UI charts in real-time.                          |

---

### **Phase 1: Foundation & Environment**

- **Initialize Repository:** Set up the shared Git repository with the structure defined in the Repo Map.
- **Environment Configuration:** Create a Python virtual environment (`venv`) and install core dependencies: `faster-whisper`, `pyaudio`, `aubio`, `fish-audio-sdk`, `msgpack`, `silero-vad`, and a UI library.
- **API Credentialing:** Secure Fish Audio API keys and verify credit balance.
- **Reference Audio Recording:** Record a clean 10-second audio sample of a team member's voice for cloning.

### **Phase 2: The "Smart Ear" (Input Processing)**

- **Implement Audio Capture Loop:** Create a script using `PyAudio` to continuously read microphone input.
- **Implement "Hybrid Trigger" Logic:** Refine the capture loop to accept two state flags:
  - `is_streaming` (Toggle): If True, pass audio to VAD. If VAD detects speech, process it.
  - `is_recording` (Hold): If True, bypass VAD and buffer _all_ audio until the flag becomes False, then process immediately.
- **Build Local Transcription:** Implement `faster-whisper` (int8 quantization) to process the chunks triggered by the logic above.
- **Develop Prosody Extraction:** Create the `aubio` module to extract Pitch and Energy.

### **Phase 3: The "Protocol" (Transport Layer)**

- **Define Adaptive Payload:** Design the packet structure to include a "Mode" header:
  - `Mode 0`: Full Semantic (Text + Prosody Data).
  - `Mode 1`: Text Only (No Prosody, use default receiver voice).

  - `Override`: An optional field for "Forced Emotion" (e.g., user selects "Relaxed" manually).
  - _(Stretch Goal) Mode 2: Morse Code (Text converted to beeps)._
- **Implement Serialization:** Use `msgpack` to compress the payload.
- **Build Network Simulation:** Create the TCP/UDP socket with the **"Application-Layer Throttle"** (the sleep function discussed previously) to simulate 300bps.

### **Phase 4: The "Mouthpiece" (Receiver-Side Synthesis)**

- **Implement Deserialization:** Logic to unpack `msgpack` data.
- **Integrate Fish Audio SDK:**
  - **Dynamic Prompting:** If the payload contains "Forced Emotion" (from the UI selector), use that tag. If not, use the extracted Prosody data from `aubio`.
- **Fallback Logic:**
  - If `Mode 1` (Text Only) is received, skip the cloning prompt and read raw text using a default system voice or generic Fish Audio model to save API latency/cost.
  - _(Stretch Goal) If Mode 2 (Morse) is received, bypass Fish Audio and trigger a local sine-wave generator to play the message as beeps._
- **Audio Playback:** Implement a low-latency player using `PyAudio`.

### **Phase 5: FastAPI Control Surface (API Layer)**

- **Set Up API Skeleton:** Create the FastAPI structure in backend:
  `appy` registers routes,
  `endpoints.py` provides `/api/health`,
  `types.py` defines enums + message models,
  `engine_state.py` holds shared flags + queues,
  `socket_manager.py` implements WebSocket handling.
- **Define Message Schema:** Create the three message types:
  - **ControlMessage** (UI → backend)
  - **TranscriptMessage** (backend → UI)
  - **PacketSummaryMessage** (backend → UI)
  Include enums:
  - `JanusMode` (semantic / text-only / morse)
  - `EmotionOverride` (auto / relaxed / panicked)
- **Shared State & Queues:**
  In `engine_state.py`, implement:
  - `control_state` — current flags (`mode`, `is_streaming`, `is_recording`, `emotion_override`)
  - `transcript_queue` — engine pushes STT results
  - `packet_queue` — engine pushes packet summaries
- **WebSocket Glue:**
  In `socket_manager.py`:
  - **Receive loop:** read ControlMessages and update `control_state`
  - **Send loop:** forward transcript + packet events from queues to the frontend
  Frontend connects at: `ws://localhost:8000/ws`.
- **Engine Integration Points:**
  The audio engine:
  - **Reads** state from `control_state`
  - **Pushes** events into `transcript_queue` and `packet_queue`

### **Phase 6: The "Janus" Interface (UI/UX)**

- **Build the "Smart Button":** Implement a UI button with dual-event handling:
  - _Event A (Mouse Down):_ Sets `is_recording = True`.
  - _Event B (Mouse Up):_ Sets `is_recording = False` (triggers send).
  - _Event C (Short Click/Tap):_ Toggles `is_streaming = True/False`.
  - _Visual Feedback:_ Button turns **Red** when holding, **Green** when toggled to stream.
- **Implement Mode Selector:** Add a dropdown or radio button set for:
  - _Standard (Semantic Voice)_
  - _Text Only (Bandwidth Saver)_
  - _Emotion Overrides:_ [Auto, Forced Relaxed, Forced Panicked]
  - _(Stretch Goal) Morse Code (Emergency)_
- **Develop Bandwidth Visualizer:** Create the live comparison (telemetry) chart (Standard VoIP Cost vs. Janus Cost) that updates every time a packet is sent.

### **Phase 7: Integration & Tuning**

- **End-to-End Testing:** Verify that "Holding" the button captures a long sentence and sends it as one block, while "Toggling" successfully sends sentence-by-sentence based on VAD.
- **Latency Tuning:** Adjust the VAD silence threshold for the "Streaming" mode to ensure it feels natural.
- **Narrative Polish:** Finalize the demo script.
  - _Scene 1:_ "Streaming Mode" for general chatter.
  - _Scene 2:_ "Hold Mode" for a critical, long report.
  - _Scene 3:_ "Mode Switch" to Text-Only to show adaptability.
  - _(Stretch Goal) Scene 4: "Emergency" - Switch to Morse code if time permits implementation._
