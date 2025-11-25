# Janus API Documentation

This document describes the WebSocket and REST API endpoints for the Janus backend.

## WebSocket API

### Connection

**Endpoint:** `ws://localhost:8000/ws/janus`

The WebSocket connection provides bidirectional communication between the frontend and backend. The backend sends transcript and packet summary events, while the frontend sends control messages to update engine state.

### Message Types

#### ControlMessage (Frontend → Backend)

Sent from the frontend to update the engine control state. Any field set to `null` or omitted indicates "no change" to that field.

**Type:** `"control"`

**Fields:**
- `type` (string, required): Always `"control"`
- `is_streaming` (boolean, optional): Enable/disable streaming mode (VAD-based processing)
- `is_recording` (boolean, optional): Enable/disable recording mode (hold-to-record)
- `mode` (string, optional): Transmission mode (`"semantic"`, `"text_only"`, or `"morse"`)
- `emotion_override` (string, optional): Emotion override (`"auto"`, `"relaxed"`, or `"panicked"`)

**Example:**
```json
{
  "type": "control",
  "is_recording": true,
  "mode": "semantic",
  "emotion_override": "auto"
}
```

#### TranscriptMessage (Backend → Frontend)

Sent from the backend when a speech segment is transcribed.

**Type:** `"transcript"`

**Fields:**
- `type` (string, required): Always `"transcript"`
- `text` (string, required): Transcribed text content
- `start_ms` (integer, optional): Start timestamp in milliseconds
- `end_ms` (integer, optional): End timestamp in milliseconds
- `avg_pitch_hz` (float, optional): Average pitch in Hz (F0)
- `avg_energy` (float, optional): Average energy level

**Example:**
```json
{
  "type": "transcript",
  "text": "Hello, this is a test message",
  "start_ms": 1000,
  "end_ms": 3500,
  "avg_pitch_hz": 180.5,
  "avg_energy": 0.75
}
```

#### PacketSummaryMessage (Backend → Frontend)

Sent from the backend when a packet is transmitted, providing metadata for bandwidth visualization.

**Type:** `"packet_summary"`

**Fields:**
- `type` (string, required): Always `"packet_summary"`
- `bytes` (integer, required): Packet size in bytes
- `mode` (string, required): Transmission mode (`"semantic"`, `"text_only"`, or `"morse"`)
- `created_at_ms` (integer, required): Packet creation timestamp in milliseconds

**Example:**
```json
{
  "type": "packet_summary",
  "bytes": 142,
  "mode": "semantic",
  "created_at_ms": 1699123456789
}
```

### Enums

#### JanusMode

Transmission modes for Janus packets:

- `"semantic"`: Full semantic transmission (text + prosody data)
- `"text_only"`: Text-only transmission (no prosody)
- `"morse"`: Morse code transmission

#### EmotionOverride

Emotion override options:

- `"auto"`: Use prosody-extracted emotion (default)
- `"relaxed"`: Force relaxed emotion
- `"panicked"`: Force panicked emotion

### Connection Lifecycle

1. **Connection**: Frontend establishes WebSocket connection to `/ws/janus`
2. **Control Updates**: Frontend sends `ControlMessage` to update engine state
3. **Event Streaming**: Backend continuously sends `TranscriptMessage` and `PacketSummaryMessage` events
4. **Disconnection**: Either side can close the connection; backend handles cleanup gracefully

### Error Handling

- Invalid message format: Backend logs error and continues processing
- WebSocket disconnection: Backend cancels tasks and cleans up resources
- Connection errors: Frontend should implement reconnection logic

## REST API

### Health Check

**Endpoint:** `GET /api/health`

Returns the health status of the backend server.

**Response:**
```json
{
  "status": "ok"
}
```

**Status Codes:**
- `200`: Server is healthy

### Voice Verification

**Endpoint:** `POST /api/voice/verify`

Verifies and saves reference audio for voice cloning. Accepts an audio file, transcribes it, and verifies it matches the verification phrase ("The quick brown fox jumps over the lazy dog.").

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: Audio file (supports WAV, WebM, etc.)

**Response (Success):**
```json
{
  "status": "verified"
}
```

**Response (Failure):**
```json
{
  "status": "failed",
  "transcript": "actual transcribed text"
}
```

**Status Codes:**
- `200`: Request processed (check `status` field for verification result)

**Verification:**
- The audio file is transcribed using faster-whisper
- Transcript is compared to verification phrase using sequence matching
- Similarity threshold: 80% (0.8)
- If verified, audio is saved as `backend/reference_audio.wav`

## Protocol Details

### WebSocket Message Format

All WebSocket messages are JSON strings. The backend uses Pydantic models for validation, ensuring type safety and proper serialization.

### Message Flow

1. Frontend connects and sends initial control state
2. Backend processes audio based on control state
3. Backend sends transcript events as speech is detected and transcribed
4. Backend sends packet summary events when packets are transmitted
5. Frontend updates control state as user interacts with UI
6. Backend responds to control updates by changing engine behavior

### State Management

Control state is managed in `backend/common/engine_state.py`:
- `ControlState` object holds current mode, flags, and emotion override
- Updated atomically when `ControlMessage` is received
- Read by `smart_ear_loop` to determine processing behavior

Event queues (`transcript_queue`, `packet_queue`) are used to decouple engine processing from WebSocket communication:
- Engine pushes events to queues
- WebSocket manager drains queues and forwards to frontend
- Async queues ensure non-blocking operation

