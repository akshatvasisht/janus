import asyncio
import queue
import threading
import time
import numpy as np
import logging
import os
<<<<<<< HEAD
import socket
import struct
=======
>>>>>>> main
from concurrent.futures import ThreadPoolExecutor

from ..common import engine_state
from ..common.protocol import JanusPacket, JanusMode as ProtocolJanusMode
from ..api.types import TranscriptMessage, PacketSummaryMessage, JanusMode

# Import services
# Note: adjusting relative imports based on file location (backend/services/engine.py)
from .audio_io import AudioService
from .vad import VoiceActivityDetector
from .transcriber import Transcriber
from .prosody import ProsodyExtractor
from .link_simulator import LinkSimulator
<<<<<<< HEAD
from .synthesizer import Synthesizer
=======
>>>>>>> main

logger = logging.getLogger(__name__)


<<<<<<< HEAD
def recv_exact(sock, n):
    """
    Helper function to receive exactly n bytes from a socket.
    Handles fragmented reads that can occur with TCP.
    
    Args:
        sock: The socket to read from
        n: Number of bytes to read
        
    Returns:
        bytes: Exactly n bytes, or None if connection closed
    """
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None  # Connection closed
        data += packet
    return data


def playback_worker(audio_service, playback_queue, stop_event):
    """
    Playback thread worker function.
    Continuously pulls audio bytes from queue and plays them.
    Prevents blocking the main receiver loop.
    
    Args:
        audio_service: AudioService instance for playback
        playback_queue: Queue containing audio bytes to play
        stop_event: Threading event to signal shutdown
    """
    while not stop_event.is_set():
        try:
            # Get audio bytes from queue (blocking with timeout)
            try:
                audio_bytes = playback_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            
            # Play the audio chunk
            if audio_bytes:
                audio_service.write_chunk(audio_bytes)
            
            playback_queue.task_done()
            
        except Exception as e:
            print(f"Playback error: {e}")
            playback_queue.task_done()


def receiver_loop(audio_service, stop_event):
    """
    Receiver loop for full-duplex audio.
    Listens for TCP connections, receives JanusPackets, synthesizes audio, and plays it.
    
    Args:
        audio_service: Shared AudioService instance for playback
        stop_event: Threading event to signal shutdown
    """
    # 1. SETUP
    api_key = os.getenv("FISH_AUDIO_API_KEY")
    if not api_key:
        logger.error("FISH_AUDIO_API_KEY environment variable not set")
        return
    
    receiver_port = int(os.getenv("RECEIVER_PORT", "5005"))
    reference_audio_path = os.getenv("REFERENCE_AUDIO_PATH", None)
    
    # Initialize Synthesizer
    try:
        synthesizer = Synthesizer(api_key=api_key, reference_audio_path=reference_audio_path)
    except Exception as e:
        logger.error(f"Failed to initialize Synthesizer: {e}")
        return
    
    # 2. NETWORK SETUP (TCP only)
    listen_sock = None
    sock = None
    try:
        listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_sock.bind(('0.0.0.0', receiver_port))
        listen_sock.listen(1)
        logger.info(f"Listening for Transmissions on TCP port {receiver_port}...")
        
        # Accept connection
        sock, addr = listen_sock.accept()
        logger.info(f"Connection established from {addr}")
    except Exception as e:
        logger.error(f"Failed to set up TCP listener: {e}")
        if listen_sock:
            listen_sock.close()
        return
    
    # Create playback queue and thread
    playback_queue = queue.Queue(maxsize=100)
    playback_stop_event = threading.Event()
    
    playback_thread = threading.Thread(
        target=playback_worker,
        args=(audio_service, playback_queue, playback_stop_event),
        daemon=True
    )
    playback_thread.start()

    # 3. MAIN LOOP
    try:
        while not stop_event.is_set():
            try:
                # A. RECEIVE DATA (Strict TCP Framing)
                # Read 4-byte big-endian length prefix first
                length_bytes = recv_exact(sock, 4)
                if length_bytes is None:
                    logger.info("Connection closed by sender")
                    break
                
                payload_length = struct.unpack('>I', length_bytes)[0]
                
                # Read the full packet
                data = recv_exact(sock, payload_length)
                if data is None:
                    logger.info("Connection closed while reading packet")
                    break

                # B. DESERIALIZE
                try:
                    packet = JanusPacket.deserialize(data)
                except Exception as e:
                    logger.error(f"Corrupt packet received: {e}")
                    continue

                # C. VISUALIZE (The "Terminal Dashboard")
                # Determine emotion tag for display
                if packet.override_emotion != "Auto":
                    emotion_tag = packet.override_emotion
                else:
                    # Map prosody to emotion (same logic as synthesizer)
                    prosody = packet.prosody
                    pitch = prosody.get('pitch', 'Normal')
                    energy = prosody.get('energy', 'Normal')
                    
                    if pitch == 'High' and energy == 'Loud':
                        emotion_tag = 'Excited'
                    elif pitch == 'High' and energy == 'Normal':
                        emotion_tag = 'Joyful'
                    elif pitch == 'Low' and energy == 'Loud':
                        emotion_tag = 'Panicked'
                    elif pitch == 'Low' and energy in ('Quiet', 'Low'):
                        emotion_tag = 'Serious'
                    else:
                        emotion_tag = 'Neutral'
                
                # Mode name mapping
                mode_names = {
                    ProtocolJanusMode.SEMANTIC_VOICE: "Semantic Voice",
                    ProtocolJanusMode.TEXT_ONLY: "Text Only",
                    ProtocolJanusMode.MORSE_CODE: "Morse Code"
                }
                mode_name = mode_names.get(packet.mode, "Unknown")
                
                # Print visualization
                print(f"📥 RECEIVED: [{mode_name}] '{packet.text}'")
                print(f"   Meta: Energy={packet.prosody.get('energy', 'N/A')}, "
                      f"Pitch={packet.prosody.get('pitch', 'N/A')} -> Prompt: [{emotion_tag}]")

                # D. SYNTHESIZE (The "Brain")
                try:
                    audio_bytes = synthesizer.synthesize(packet)
                except Exception as e:
                    logger.error(f"Synthesis error: {e}")
                    continue

                # E. PLAYBACK (The "Mouth")
                # Push to playback queue (non-blocking)
                try:
                    playback_queue.put(audio_bytes, timeout=0.1)
                except queue.Full:
                    logger.warning("Warning: Playback queue full, skipping audio chunk")

            except Exception as e:
                logger.error(f"Receiver Error: {e}")
                continue
    
    finally:
        # Cleanup
        logger.info("Shutting down receiver loop...")
        playback_stop_event.set()
        
        # Wait for playback thread to finish
        playback_thread.join(timeout=2)
        
        # Close sockets
        if sock:
            try:
                sock.close()
            except Exception:
                pass
        if listen_sock:
            try:
                listen_sock.close()
            except Exception:
                pass
        
        logger.info("Receiver loop shutdown complete.")


=======
>>>>>>> main
def map_api_mode_to_protocol_mode(api_mode: JanusMode) -> ProtocolJanusMode:
    """
    Map API JanusMode (string enum) to Protocol JanusMode (int enum).
    
    Args:
        api_mode: JanusMode from api.types (string enum)
        
    Returns:
        ProtocolJanusMode: JanusMode from common.protocol (int enum)
    """
    mapping = {
        JanusMode.SEMANTIC: ProtocolJanusMode.SEMANTIC_VOICE,
        JanusMode.TEXT_ONLY: ProtocolJanusMode.TEXT_ONLY,
        JanusMode.MORSE: ProtocolJanusMode.MORSE_CODE,
    }
    return mapping.get(api_mode, ProtocolJanusMode.SEMANTIC_VOICE)


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
    audio_service: AudioService,
):
    """
    Main Smart Ear engine loop (Async).
    
    Args:
        control_state: Control state for the engine
        transcript_queue: Queue for transcript messages
        packet_queue: Queue for packet summary messages
        audio_service: Shared AudioService instance for audio input
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
        # audio_service is now passed as parameter
        vad_model = VoiceActivityDetector()
        transcriber = Transcriber()
        prosody_tool = ProsodyExtractor()

        # Configure Link Simulator
        # Read from environment variables or use defaults
        target_ip = os.getenv("TARGET_IP", "127.0.0.1")
        target_port = int(os.getenv("TARGET_PORT", "5005"))
        
        # Auto-detect TCP mode if ngrok is detected in target IP
        use_tcp = "ngrok" in target_ip.lower() or os.getenv("USE_TCP", "").lower() == "true"
        
        print(f"Link Simulator: {target_ip}:{target_port} ({'TCP' if use_tcp else 'UDP'})")
        link_simulator = LinkSimulator(target_ip=target_ip, target_port=target_port, use_tcp=use_tcp)

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

                    # Define transmission wrapper
                    def transmit_packet_blocking():
                        try:
                            # Map API mode (string enum) to Protocol mode (int enum)
                            protocol_mode = map_api_mode_to_protocol_mode(control_state.mode)
                            packet = JanusPacket(
                                text=text,
                                mode=protocol_mode,  # Uses UI selection (Morse/Text/Semantic)
                                prosody=meta,
                                override_emotion=control_state.emotion_override
                            )
                            link_simulator.transmit(packet.serialize())
                        except Exception as e:
                            print(f"Transmission Error: {e}")

                    # Await transmission (Simulation Throttle)
                    # This keeps the WS alive but blocks the next audio chunk processing
                    await loop.run_in_executor(executor, transmit_packet_blocking)

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
<<<<<<< HEAD
        # audio_service.close() is now handled by server.py
=======
        audio_service.close()
>>>>>>> main
        if 'link_simulator' in locals():
            link_simulator.close()
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
