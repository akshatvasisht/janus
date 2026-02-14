# Project Style Guide & Coding Standards

This document serves as the authoritative source for coding standards, documentation styles, and architectural context for the **Janus** project. It is intended to be referenced by developers and AI assistants to ensure consistency, professionalism, and maintainability across the codebase.

## 1. General Principles

### 1.1 Professionalism
* **Tone:** All documentation and comments must be written in a professional, objective, and technical tone.
* **Language:** Avoid informal language, slang, or "hackathon" jargon (e.g., "hacked together," "dirty fix").
* **Constraint Descriptions:** Describe technical constraints rather than environmental ones.
    * *Incorrect:* "Running on my hackathon laptop."
    * *Correct:* "Defaulting to CPU inference for wider hardware compatibility."

### 1.2 Intent over Implementation
* **Why, Not What:** Comments should explain *why* a decision was made or *how* an interface is intended to be used. Do not narrate the code execution logic step-by-step, as the code itself should be self-explanatory.
* **No Meta-Commentary:** Do not leave "thinking traces," internal debates, or editing notes in the codebase.
    * *Forbidden:* `// I tried X but it failed, so I'm doing Y...`
    * *Allowed:* `// Uses Y to ensure thread safety during high-load.`

---

## 2. Frontend Guidelines (TypeScript / React / Next.js)

### 2.1 Code Style
* **Components:** Use functional components with strictly typed interfaces for props.
* **Strict Typing:** Avoid `any`. Define shared types in `frontend/types/janus.ts` to ensure consistency between frontend and backend.
* **Hooks:** Abstract complex logic into custom hooks (e.g., `useJanusSocket.ts`) to keep UI components focused on rendering.

### 2.2 Documentation Standards
* **JSDoc:** Use standard JSDoc format (`/** ... */`) for exported functions, hooks, and complex component props.
* **Prop Documentation:** Explicitly document specific behaviors of props if the name is not self-explanatory.
* **Clean Handlers:** Event handlers should contain logic or calls to handlers, not paragraphs of developer reasoning.

**Example:**
```typescript
/**
 * Interaction button for the Janus interface.
 * Handles both "Hold-to-Record" and "Tap-to-Stream" patterns via separate listeners
 * to avoid event conflict.
 */
export default function PushToTalk({
  isRecording,
  onHoldStart,
}: PushToTalkProps) {
  // ... implementation
}
```

## 3. Backend Guidelines (Python / FastAPI)

### 3.1 Docstrings
* **Format:** Use Google Style or NumPy Style docstrings.
* **Structure:** Clearly separate the description, arguments (Args), and return values (Returns).
* **Forbidden Format:** Do not use "Tutorial Style" numbered lists (e.g., "Steps: 1. Do this, 2. Do that") in docstrings. Implementation details belong in the function body or a separate design document.

**Bad Example:**

```python
def read_chunk(self):
    """
    Steps:
    1. Read bytes.
    2. Handle overflow.
    3. Return array.
    """
```

**Good Example:**

```python
def read_chunk(self) -> np.ndarray:
    """
    Reads a single chunk of audio from the input stream.

    Returns:
        np.ndarray: A float32 array of audio samples normalized between -1.0 and 1.0.
        Returns a zero-filled array if hardware is unavailable.

    Raises:
        IOError: If the input stream overflows (handled internally by logging).
    """
```

### 3.2 Coding Standards
* **Type Hinting:** Use Python type hints (`def func(a: int) -> str:`) for all function signatures to improve readability and IDE support.
* **Imports:** Organize imports into standard library, third-party, and local modules. Remove comments that merely state "Importing modules."

---

## 4. Architectural Context

### 4.1 System Overview
Janus is a real-time semantic audio codec system designed to optimize bandwidth by transmitting semantic meaning rather than raw audio waveforms.

### 4.2 Core Components

**Frontend:**

* **Stack:** Next.js 14 (React), Tailwind CSS, Recharts.
* **Role:** Provides the user interface for Push-to-Talk (PTT) interaction and visualizes real-time telemetry (bandwidth vs. cost).
* **Communication:** Connects to the backend via WebSockets (useJanusSocket).

**Backend:**

* **Stack:** Python 3.10+, FastAPI.
* **Role:** Orchestrates the audio processing pipeline and manages WebSocket connections.
* **Engine:** The smart_ear_loop (in engine.py) manages the continuous flow of audio data.

**Services Layer:**

* **audio_io:** Handles raw hardware interface (PyAudio) for microphone capture and speaker output.
* **vad:** Voice Activity Detection (Silero). Acts as a gatekeeper to filter silence.
* **transcriber:** Local Speech-to-Text using faster-whisper (Int8 quantized for CPU performance).
* **prosody:** Extracts emotional metadata (Pitch/Energy) using aubio.
* **synthesizer:** Reconstructs audio on the receiver side using Generative TTS (Fish Audio SDK).
* **link_simulator:** Simulates a constrained 300bps network connection for demonstration purposes.

### 4.3 Data Flow
* **Input:** Raw Microphone Audio → VAD → Audio Buffer.
* **Processing:** Audio Buffer → STT (Text Generation) + Prosody Analysis (Metadata Extraction).
* **Transport:** Text + Metadata → MsgPack Serialization → 300bps Link Simulation → Receiver.
* **Output:** Receiver → Synthesizer (Voice Reconstruction) → Speaker Playback.

---

## 5. File & Repository Standards
* **README.md:** Must serve as the primary entry point for the project. It should contain the Project Overview, Architecture Summary, and setup instructions. It must not be left empty.
* **docs/ARCHITECTURE.md:** Reserved for deep-dive architectural documentation, glossary, and specific design decisions. Located in the docs/ directory.
* **docs/:** Directory containing detailed documentation (API.md, ARCHITECTURE.md, SETUP.md, TESTING.md, STYLE.md).
* **backend/scripts/:** Directory containing CLI utility scripts for testing and development.
* **Code Comments:** Comments should focus on complex logic or "gotchas." Trivial logic (e.g., `i++ // increment i`) should not be commented.

---

## 6. Testing Standards
* **Framework:** Use pytest for all backend testing.
* **Naming Conventions:**
    * Test files must be prefixed with `test_` (e.g., `test_api_flow.py`).
    * Test functions must be prefixed with `test_` (e.g., `def test_health_check():`).
* **Mocking:** Use unittest.mock or pytest-mock to isolate external dependencies. Do not rely on live hardware (microphones) or external APIs (Fish Audio) during standard test runs.
* **Fixtures:** Use pytest fixtures for setup/teardown (e.g., resetting engine state) rather than global variables where possible.

---

## 7. Scripting & Ops Guidelines
* **Shell Scripts:** Ensure scripts (like setup.sh) are executable and include a "shebang" (`#!/bin/bash`).
* **Safety:** Prefer using `set -e` in shell scripts to ensure the script exits immediately if a command fails, preventing cascading errors during setup.
* **User Feedback:** Scripts should provide clear echo statements indicating the current step (e.g., `echo "--- [1/3] Installing System Dependencies ---"`).