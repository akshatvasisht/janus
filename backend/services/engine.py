import asyncio
import queue
import threading
import time
import numpy as np
import logging
from concurrent.futures import ThreadPoolExecutor

from ..common import engine_state
from ..api.types import TranscriptMessage, PacketSummaryMessage, JanusMode

# Import services
# Note: adjusting relative imports based on file location (backend/services/engine.py)
from .audio_io import AudioService
from .vad import VoiceActivityDetector
from .transcriber import Transcriber
from .prosody import ProsodyExtractor

logger = logging.getLogger(__name__)


def audio_producer(audio_service, audio_queue, stop_event):
    """
    Thread A (Producer): Continuously reads audio chunks.
    """
    while not stop_event.is_set():
        try:
            chunk = audio_service.read_chunk()
            try:
                audio_queue.put(chunk, timeout=0.1)
            except queue.Full:
                pass
        except Exception as e:
            logger.error(f"Error in audio producer: {e}")
            time.sleep(0.1)


async def smart_ear_loop(
    control_state: engine_state.ControlState,
    transcript_queue: "asyncio.Queue[TranscriptMessage]",
    packet_queue: "asyncio.Queue[PacketSummaryMessage]",
):
    """
    Main Smart Ear engine loop (Async).
    """
    print("Initializing Smart Ear services...")

    # 1. Initialize Services (Heavy lifting, might take a moment)
    # We run these in executor if they take too long, but usually init is fine to block briefly on startup
    loop = asyncio.get_running_loop()

    try:
        # Instantiate services
        # We use a thread pool for heavy computation (transcription)
        executor = ThreadPoolExecutor(max_workers=2)

        # Initialize hardware/models
        audio_service = AudioService()
        vad_model = VoiceActivityDetector()
        transcriber = Transcriber()
        prosody_tool = ProsodyExtractor()

        print("Smart Ear services ready.")

    except Exception as e:
        print(f"Failed to initialize Smart Ear services: {e}")
        return

    # 2. Setup Producer Thread
    audio_queue = queue.Queue(maxsize=100)
    stop_event = threading.Event()

    producer_thread = threading.Thread(
        target=audio_producer,
        args=(audio_service, audio_queue, stop_event),
        daemon=True,
    )
    producer_thread.start()

    # 3. Consumer Loop (The "Brain" logic, ported to Async)

    audio_buffer = []
    silence_counter = 0
    SILENCE_THRESHOLD_CHUNKS = 16  # ~500ms
    previous_hold_state = False

    try:
        while True:
            # Non-blocking check of the queue
            try:
                # Get up to N chunks at a time to be efficient?
                # For now, process one by one but quickly.
                chunk = audio_queue.get_nowait()
            except queue.Empty:
                # Yield control if no audio
                await asyncio.sleep(0.01)
                continue

            # Logic ported from sender_main.py
            trigger_processing = False

            # Read Control State
            is_streaming_mode = control_state.is_streaming
            is_recording_hold = control_state.is_recording

            # CASE 1: HOLD MODE
            if is_recording_hold:
                audio_buffer.append(chunk)
                previous_hold_state = True
                # Don't process yet
                continue

            # Check release
            if previous_hold_state and not is_recording_hold:
                trigger_processing = True
                previous_hold_state = False

            # CASE 2: STREAMING
            elif is_streaming_mode:
                is_speech = vad_model.is_speech(chunk)
                if is_speech:
                    audio_buffer.append(chunk)
                    silence_counter = 0
                else:
                    silence_counter += 1
                    if len(audio_buffer) > 0:
                        audio_buffer.append(chunk)

                    if silence_counter > SILENCE_THRESHOLD_CHUNKS:
                        trigger_processing = True

            # CASE 3: IDLE
            else:
                # Discard
                pass

            # PROCESSING
            if trigger_processing and len(audio_buffer) > 0:
                # Combine buffer
                combined_audio = np.concatenate(audio_buffer)

                # Run Transcription & Prosody in Executor (Don't block loop!)

                # Define wrapper for transcription
                def process_audio_blocking(audio_data):
                    t_text = ""
                    t_meta = {}
                    try:
                        t_text = transcriber.transcribe_buffer(audio_data)
                    except Exception as e:
                        print(f"Transcribe error: {e}")

                    try:
                        t_meta = prosody_tool.analyze_buffer(audio_data)
                    except Exception as e:
                        print(f"Prosody error: {e}")
                        t_meta = {
                            "energy": "Normal",
                            "pitch": "Normal",
                        }  # Default fallback

                    return t_text, t_meta

                # Await the result from thread pool
                text, meta = await loop.run_in_executor(
                    executor, process_audio_blocking, combined_audio
                )

                # Clear buffer
                audio_buffer = []
                silence_counter = 0

                # Emit Events if we got text
                if text.strip():
                    print(f"Captured: '{text}' | Tone: {meta}")

                    # Construct messages
                    # Map 'energy'/'pitch' strings/values to float if needed,
                    # but for now existing prosody returns dict.
                    # Types.py expects floats for avg_pitch_hz/energy if available.
                    # Let's check what prosody.py actually returns.
                    # Assuming it returns readable strings or values.
                    # We'll try to parse or just leave None for now if incompatible.

                    await _emit_events(
                        text=text,
                        avg_pitch_hz=None,  # TODO: Extract actual float from meta if available
                        avg_energy=None,
                        mode=control_state.mode,
                        transcript_queue=transcript_queue,
                        packet_queue=packet_queue,
                    )

    except asyncio.CancelledError:
        print("Smart Ear loop cancelled. Cleaning up...")
    finally:
        stop_event.set()
        producer_thread.join(timeout=2)
        audio_service.close()
        executor.shutdown(wait=False)
        print("Smart Ear stopped.")


async def _emit_events(
    text: str,
    avg_pitch_hz: float | None,
    avg_energy: float | None,
    mode: JanusMode,
    transcript_queue: "asyncio.Queue[TranscriptMessage]",
    packet_queue: "asyncio.Queue[PacketSummaryMessage]",
):
    now_ms = int(time.time() * 1000)

    transcript_msg = TranscriptMessage(
        type="transcript",
        text=text,
        start_ms=None,
        end_ms=None,
        avg_pitch_hz=avg_pitch_hz,
        avg_energy=avg_energy,
    )
    await transcript_queue.put(transcript_msg)

    # Packet estimate
    approximate_bytes = len(text.encode("utf-8")) + 16

    packet_msg = PacketSummaryMessage(
        type="packet_summary",
        bytes=approximate_bytes,
        mode=mode,
        created_at_ms=now_ms,
    )
    await packet_queue.put(packet_msg)
