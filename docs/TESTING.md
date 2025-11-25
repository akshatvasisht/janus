# Testing Guidelines

This document describes the testing approach, standards, and procedures for the Janus project.

## Automated Tests

### Running Tests

Run all tests from the project root:

```bash
pytest backend/tests/
```

Run specific test files:

```bash
pytest backend/tests/test_api_flow.py
pytest backend/tests/test_engine.py
pytest backend/tests/test_input_processing.py
```

Run tests with verbose output:

```bash
pytest backend/tests/ -v
```

Run tests with coverage:

```bash
pytest backend/tests/ --cov=backend --cov-report=html
```

### Test Structure

Tests are organized in `backend/tests/` with the following structure:

- `test_api_flow.py`: Tests for REST API endpoints and WebSocket communication
- `test_engine.py`: Tests for Smart Ear engine loop and receiver loop
- `test_input_processing.py`: Tests for audio processing pipeline (VAD, transcription, prosody)
- `test_synthesis.py`: Tests for voice synthesis functionality
- `test_transport_layer.py`: Tests for packet serialization and network transmission
- `test_voice_cloning.py`: Tests for voice cloning and reference audio handling

### Test Naming Conventions

Following STYLE.md standards:

- **Test files**: Must be prefixed with `test_` (e.g., `test_api_flow.py`)
- **Test functions**: Must be prefixed with `test_` (e.g., `def test_health_check():`)

### Mocking Requirements

Automated tests must not rely on:
- Live hardware (microphones, speakers)
- External APIs (Fish Audio SDK)
- Network connections (except mocked)

Use `unittest.mock` or `pytest-mock` to isolate external dependencies:

```python
from unittest.mock import Mock, patch

@patch('backend.services.synthesizer.Synthesizer')
def test_synthesis_with_mock(mock_synthesizer):
    # Test implementation
    pass
```

### Pytest Fixtures

Use pytest fixtures for setup/teardown rather than global variables:

```python
import pytest
from backend.common import engine_state

@pytest.fixture
def reset_engine_state():
    """Reset engine state before each test."""
    engine_state.reset_queues()
    engine_state.control_state.mode = JanusMode.SEMANTIC
    yield
    engine_state.reset_queues()
```

## Manual Tests

### Hardware Checks

The `backend/tests/hardware_check.py` script provides manual hardware verification:

**Purpose:** Tests actual PyAudio hardware without mocking. Records real audio and analyzes levels to verify microphone and audio driver functionality.

**Usage:**

```bash
cd backend
python tests/hardware_check.py
```

**What it does:**
1. Initializes PyAudio and lists available input devices
2. Records 1 second of audio from the microphone
3. Saves audio to `test_output.wav`
4. Analyzes audio levels (RMS, max amplitude)
5. Tests `AudioService` initialization and chunk reading
6. Provides warnings if audio levels are too low or silent

**Expected Output:**
- Lists available input devices
- Records audio and saves to WAV file
- Analyzes audio levels and provides feedback
- Tests AudioService functionality

**Troubleshooting:**
- If audio is silent: Check microphone connection, OS mute settings, volume levels
- If AudioService fails: Verify system audio libraries are installed
- If no devices listed: Check audio driver installation

### Manual Packet Sender

The `backend/tests/manual_sender.py` script allows manual testing of packet transmission:

**Purpose:** Sends test packets to a running receiver for manual integration testing. Useful for verifying network connectivity and packet reception.

**Usage:**

```bash
cd backend
# Set environment variables if needed
export TARGET_IP=127.0.0.1
export TARGET_PORT=5005
export USE_TCP=false  # or true for TCP

python tests/manual_sender.py
```

**What it does:**
1. Creates a test `JanusPacket` with sample text
2. Serializes packet using MessagePack
3. Sends packet via UDP or TCP (based on `USE_TCP`)
4. Prints confirmation and packet size

**Configuration:**
- `TARGET_IP`: Target IP address (default: `127.0.0.1`)
- `TARGET_PORT`: Target port (default: `5005`)
- `USE_TCP`: Set to `"true"` for TCP mode (default: `false`)

**Use Cases:**
- Testing receiver loop functionality
- Verifying network connectivity between machines
- Debugging packet serialization/deserialization
- Testing TCP vs UDP transmission

### CLI Sender/Receiver Testing

The standalone CLI tools (`backend/scripts/sender_main.py` and `backend/scripts/receiver_main.py`) can be used for network testing.

**Important**: These scripts must be run as Python modules from the project root directory due to their import structure.

**Receiver (Terminal 1):**

```bash
export FISH_AUDIO_API_KEY=your_api_key
export RECEIVER_PORT=5005
python -m backend.scripts.receiver_main
```

**Sender (Terminal 2):**

```bash
export TARGET_IP=127.0.0.1
export TARGET_PORT=5005
python -m backend.scripts.sender_main
```

**What it tests:**
- Direct network communication without web interface
- Packet transmission and reception
- Audio synthesis and playback
- Network configuration (TCP/UDP, ports, IPs)
- End-to-end audio pipeline

**Use Cases:**
- Testing network connectivity across machines
- Verifying ngrok tunnel configuration
- Debugging network issues
- Testing without frontend dependencies

## Writing New Tests

### Test Structure

Follow this pattern for new tests:

```python
import pytest
from unittest.mock import Mock, patch
from backend.services.your_service import YourService

def test_your_feature():
    """Test description explaining what is being tested."""
    # Arrange: Set up test data and mocks
    mock_dependency = Mock()
    
    # Act: Execute the code under test
    result = your_function(mock_dependency)
    
    # Assert: Verify expected behavior
    assert result == expected_value
```

### Best Practices

1. **Isolation**: Each test should be independent and not rely on other tests
2. **Naming**: Use descriptive test names that explain what is being tested
3. **Mocking**: Mock external dependencies (APIs, hardware, network)
4. **Fixtures**: Use pytest fixtures for common setup/teardown
5. **Assertions**: Use specific assertions with clear error messages
6. **Coverage**: Aim for high test coverage of core functionality

### Example Test

```python
import pytest
from backend.api.types import ControlMessage, JanusMode
from backend.common import engine_state

@pytest.fixture
def reset_state():
    """Reset engine state before test."""
    engine_state.control_state.mode = JanusMode.SEMANTIC
    engine_state.control_state.is_streaming = False
    yield
    engine_state.reset_queues()

def test_control_message_updates_state(reset_state):
    """Verify ControlMessage updates engine state correctly."""
    msg = ControlMessage(
        type="control",
        mode=JanusMode.TEXT_ONLY,
        is_streaming=True
    )
    
    # Apply control message (simulating WebSocket handler)
    if msg.mode is not None:
        engine_state.control_state.mode = msg.mode
    if msg.is_streaming is not None:
        engine_state.control_state.is_streaming = msg.is_streaming
    
    assert engine_state.control_state.mode == JanusMode.TEXT_ONLY
    assert engine_state.control_state.is_streaming is True
```

## Test Standards (from STYLE.md)

- **Framework**: Use pytest for all backend testing
- **Naming**: Test files prefixed with `test_`, test functions prefixed with `test_`
- **Mocking**: Use `unittest.mock` or `pytest-mock` to isolate external dependencies
- **Fixtures**: Use pytest fixtures for setup/teardown rather than global variables
- **No Live Hardware**: Do not rely on live hardware or external APIs during standard test runs

## Continuous Integration

Tests should be run automatically in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    source backend/venv/bin/activate
    pytest backend/tests/ -v
```

## Troubleshooting Tests

### Common Issues

**Import errors:**
- Ensure virtual environment is activated
- Verify `backend` is in Python path
- Check that all dependencies are installed

**Mocking failures:**
- Verify import paths match actual module structure
- Use `patch` decorator with full module path
- Check that mocked objects are used correctly

**Test isolation failures:**
- Ensure fixtures reset state between tests
- Avoid global state mutations
- Use `reset_queues()` fixture for engine state

**Hardware-dependent tests:**
- Move hardware tests to manual test scripts
- Use mocking for automated tests
- Document hardware requirements for manual tests

