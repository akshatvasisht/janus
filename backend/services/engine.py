import asyncio
import logging
import os
import queue
import socket
import struct
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import numpy as np

from ..api.types import JanusMode, PacketSummaryMessage, TranscriptMessage
from ..common import engine_state
from ..common.protocol import JanusMode as ProtocolJanusMode, JanusPacket
from .audio_io import AudioService
from .link_simulator import LinkSimulator
from .prosody import ProsodyExtractor
from .synthesizer import Synthesizer
from .transcriber import Transcriber
from .vad import VoiceActivityDetector

if TYPE_CHECKING:
    from types import ModuleType

logger = logging.getLogger(__name__)


def recv_exact(sock: socket.socket, n: int) -> bytes | None:
    """
    Helper function to receive exactly n bytes from a socket.
    
    Handles fragmented reads that can occur with TCP by repeatedly reading
    until the requested number of bytes is received.
    
    Args:
        sock: The socket to read from.
        n: Number of bytes to read.
        
    Returns:
        bytes | None: Exactly n bytes, or None if connection is closed
            before all bytes are received.
    """
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None  # Connection closed
        data += packet
    return data


def playback_worker(
    audio_service: AudioService,
    playback_queue: queue.Queue[bytes],
    stop_event: threading.Event,
) -> None:
    """
    Playback thread worker function.
    
    Continuously pulls audio bytes from queue and plays them. Prevents blocking
    the main receiver loop by running in a separate thread.
    
    Args:
        audio_service: AudioService instance for playback.
        playback_queue: Queue containing audio bytes to play.
        stop_event: Threading event to signal shutdown. Worker exits when
            this event is set.
    
    Returns:
        None
    """
    while not stop_event.is_set():
        try:
            try:
                audio_bytes = playback_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            
            if audio_bytes:
                from ..common import engine_state as _engine_state  # local import to avoid cycles
                audio_bytes = apply_ducking_if_needed(audio_bytes, _engine_state.control_state)
                audio_service.write_chunk(audio_bytes)
            
            playback_queue.task_done()
            
        except Exception as e:
            logger.error(f"Playback error: {e}")
            playback_queue.task_done()


def apply_ducking_if_needed(audio_bytes: bytes, state: "engine_state.ControlState") -> bytes:
    """
    Apply audio ducking based on shared control state.

    When ducking is enabled and the local user is currently talking, scale the
    playback PCM samples by the configured ducking_level. Otherwise, return the
    audio bytes unchanged.

    Args:
        audio_bytes: Raw PCM audio data (int16).
        state: Shared ControlState containing ducking configuration.

    Returns:
        bytes: Possibly gain-reduced PCM audio.
    """
    try:
        if not getattr(state, "ducking_enabled", True):
            return audio_bytes

        if not getattr(state, "is_talking", False):
            return audio_bytes

        level = float(getattr(state, "ducking_level", 0.25))
        # Clamp to [0.0, 1.0]
        if level <= 0.0:
            level = 0.0
        elif level >= 1.0:
            return audio_bytes

        if not audio_bytes:
            return audio_bytes

        samples = np.frombuffer(audio_bytes, dtype=np.int16)
        if samples.size == 0:
            return audio_bytes

        scaled = np.clip(samples.astype(np.float32) * level, -32768, 32767).astype(np.int16)
        return scaled.tobytes()
    except Exception as e:
        logger.error(f"Error applying ducking: {e}")
        return audio_bytes


def receiver_loop(
    audio_service: AudioService,
    stop_event: threading.Event,
    event_loop: asyncio.AbstractEventLoop,
) -> None:
    """
    Receiver loop for full-duplex audio.
    
    Listens for TCP connections, receives JanusPackets, synthesizes audio, and plays it.
    Runs in a separate thread to avoid blocking the main event loop.
    
    Args:
        audio_service: Shared AudioService instance for playback.
        stop_event: Threading event to signal shutdown. Loop exits when set.
        event_loop: asyncio event loop for emitting events to frontend.
    
    Returns:
        None
    """
    api_key = os.getenv("FISH_AUDIO_API_KEY")
    if not api_key:
        logger.error("FISH_AUDIO_API_KEY environment variable not set")
        return
    
    receiver_port = int(os.getenv("RECEIVER_PORT", "5005"))
    reference_audio_path = os.getenv("REFERENCE_AUDIO_PATH", None)
    
    try:
        synthesizer = Synthesizer(api_key=api_key, reference_audio_path=reference_audio_path)
    except Exception as e:
        logger.error(f"Failed to initialize Synthesizer: {e}")
        return
    
    listen_sock = None
    sock = None
    try:
        listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_sock.bind(('0.0.0.0', receiver_port))
        listen_sock.listen(1)
        logger.info(f"Listening for Transmissions on TCP port {receiver_port}...")
        sock, addr = listen_sock.accept()
        logger.info(f"Connection established from {addr}")
        sock.settimeout(1.0)
    except Exception as e:
        logger.error(f"Failed to set up TCP listener: {e}")
        if listen_sock:
            listen_sock.close()
        return
    
    playback_queue = queue.Queue(maxsize=100)
    playback_stop_event = threading.Event()
    
    playback_thread = threading.Thread(
        target=playback_worker,
        args=(audio_service, playback_queue, playback_stop_event),
        daemon=True
    )
    playback_thread.start()

    try:
        while not stop_event.is_set():
            try:
                try:
                    length_bytes = recv_exact(sock, 4)
                except socket.timeout:
                    continue
                
                if length_bytes is None:
                    logger.info("Connection closed by sender")
                    break
                
                payload_length = struct.unpack('>I', length_bytes)[0]
                
                try:
                    data = recv_exact(sock, payload_length)
                except socket.timeout:
                    continue
                
                if data is None:
                    logger.info("Connection closed while reading packet")
                    break
                try:
                    packet = JanusPacket.deserialize(data)
                except Exception as e:
                    logger.error(f"Corrupt packet received: {e}")
                    continue

                try:
                    transcript_queue = engine_state.get_transcript_queue()
                    packet_queue = engine_state.get_packet_queue()
                    
                    api_mode = map_protocol_mode_to_api_mode(packet.mode)
                    
                    prosody = packet.prosody or {}
                    avg_pitch_hz = prosody.get('avg_pitch_hz') if isinstance(prosody.get('avg_pitch_hz'), (int, float)) else None
                    avg_energy = prosody.get('avg_energy') if isinstance(prosody.get('avg_energy'), (int, float)) else None
                    
                    if packet.override_emotion != "Auto":
                        emotion_tag = packet.override_emotion
                    else:
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

                    asyncio.run_coroutine_threadsafe(
                        _emit_events(
                            text=packet.text,
                            avg_pitch_hz=avg_pitch_hz,
                            avg_energy=avg_energy,
                            mode=api_mode,
                            transcript_queue=transcript_queue,
                            packet_queue=packet_queue,
                            emotion=emotion_tag,
                        ),
                        event_loop
                    )
                except Exception as e:
                    logger.error(f"Failed to emit events to frontend: {e}")
                
                mode_names = {
                    ProtocolJanusMode.SEMANTIC_VOICE: "Semantic Voice",
                    ProtocolJanusMode.TEXT_ONLY: "Text Only",
                    ProtocolJanusMode.MORSE_CODE: "Morse Code"
                }
                mode_name = mode_names.get(packet.mode, "Unknown")
                
                logger.info(f"[RECEIVED] [{mode_name}] '{packet.text}'")
                logger.debug(f"   Meta: Energy={packet.prosody.get('energy', 'N/A')}, "
                      f"Pitch={packet.prosody.get('pitch', 'N/A')} -> Prompt: [{emotion_tag}]")

                try:
                    audio_bytes = synthesizer.synthesize(packet)
                except Exception as e:
                    logger.error(f"Synthesis error: {e}")
                    continue

                try:
                    playback_queue.put(audio_bytes, timeout=0.1)
                except queue.Full:
                    logger.warning("Warning: Playback queue full, skipping audio chunk")

            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Receiver socket error: {e}")
                break
    
    finally:
        logger.info("Shutting down receiver loop...")
        playback_stop_event.set()
        playback_thread.join(timeout=2)
        
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


def map_protocol_mode_to_api_mode(protocol_mode: ProtocolJanusMode) -> JanusMode:
    """
    Map Protocol JanusMode (int enum) back to API JanusMode (string enum).
    
    Args:
        protocol_mode: ProtocolJanusMode from common.protocol (int enum)
        
    Returns:
        JanusMode: JanusMode from api.types (string enum)
    """
    mapping = {
        ProtocolJanusMode.SEMANTIC_VOICE: JanusMode.SEMANTIC,
        ProtocolJanusMode.TEXT_ONLY: JanusMode.TEXT_ONLY,
        ProtocolJanusMode.MORSE_CODE: JanusMode.MORSE,
    }
    return mapping.get(protocol_mode, JanusMode.SEMANTIC)


def audio_producer(
    audio_service: AudioService,
    audio_queue: queue.Queue[np.ndarray],
    stop_event: threading.Event,
) -> None:
    """
    Audio producer thread worker function.
    
    Continuously reads audio chunks from the audio service and places them
    in the queue for processing. Runs until stop_event is set.
    
    Args:
        audio_service: AudioService instance for reading audio input.
        audio_queue: Queue for storing audio chunks (numpy arrays).
        stop_event: Threading event to signal shutdown. Producer exits when set.
    
    Returns:
        None
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
) -> None:
    """
    Main Smart Ear engine loop for real-time audio processing.
    
    Processes audio input using VAD, transcription, and prosody extraction.
    Responds to control state changes from the frontend and emits transcript
    and packet summary events. Runs asynchronously to avoid blocking the
    main event loop.
    
    Args:
        control_state: Shared control state updated by WebSocket messages.
        transcript_queue: Async queue for emitting transcript messages to frontend.
        packet_queue: Async queue for emitting packet summary messages to frontend.
        audio_service: Shared AudioService instance for audio input capture.
    
    Returns:
        None
    """
    logger.info("Initializing Smart Ear services...")

    loop = asyncio.get_running_loop()

    try:
        executor = ThreadPoolExecutor(max_workers=2)
        vad_model = VoiceActivityDetector()
        transcriber = Transcriber()
        prosody_tool = ProsodyExtractor()

        target_ip = os.getenv("TARGET_IP", "127.0.0.1")
        target_port = int(os.getenv("TARGET_PORT", "5005"))
        use_tcp = "ngrok" in target_ip.lower() or os.getenv("USE_TCP", "").lower() == "true"
        
        logger.info(f"Link Simulator: {target_ip}:{target_port} ({'TCP' if use_tcp else 'UDP'})")
        link_simulator = LinkSimulator(target_ip=target_ip, target_port=target_port, use_tcp=use_tcp)

        logger.info("Smart Ear services ready.")

    except Exception as e:
        logger.error(f"Failed to initialize Smart Ear services: {e}")
        return

    audio_queue = queue.Queue(maxsize=100)
    stop_event = threading.Event()

    producer_thread = threading.Thread(
        target=audio_producer,
        args=(audio_service, audio_queue, stop_event),
        daemon=True,
    )
    producer_thread.start()

    audio_buffer = []
    pre_roll_buffer = deque(maxlen=10)
    silence_counter = 0
    SILENCE_THRESHOLD_CHUNKS = 15  # ~500ms
    previous_hold_state = False

    try:
        while True:
            try:
                chunk = audio_queue.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.01)
                continue

            trigger_processing = False

            is_streaming_mode = control_state.is_streaming
            is_recording_hold = control_state.is_recording

            # Push-to-talk / recording-hold: user is actively talking
            if is_recording_hold:
                control_state.is_talking = True
                audio_buffer.append(chunk)
                previous_hold_state = True
                continue

            # Transition: PTT just released -> process buffered audio and stop talking
            if previous_hold_state and not is_recording_hold:
                logger.info("PTT Released - triggering processing.")
                trigger_processing = True
                previous_hold_state = False
                control_state.is_talking = False

            elif is_streaming_mode:
                # Bypass VAD gating for Morse and Text modes to avoid blocking non-semantic transmissions
                is_non_vad_mode = control_state.mode in [JanusMode.MORSE, JanusMode.TEXT_ONLY]
                is_speech = vad_model.is_speech(chunk) or is_non_vad_mode

                if is_speech:
                    if len(audio_buffer) == 0:
                        logger.info(f"Transmission started (mode={control_state.mode}, speech={not is_non_vad_mode})")
                        audio_buffer.extend(list(pre_roll_buffer))
                    
                    control_state.is_talking = True
                    audio_buffer.append(chunk)
                    silence_counter = 0
                else:
                    silence_counter += 1
                    if len(audio_buffer) > 0:
                        audio_buffer.append(chunk)
                    else:
                        pre_roll_buffer.append(chunk)

                    if silence_counter > SILENCE_THRESHOLD_CHUNKS:
                        trigger_processing = True
                        control_state.is_talking = False

            else:
                # Neither recording nor streaming -> ensure talking flag is cleared
                control_state.is_talking = False

            if trigger_processing and len(audio_buffer) > 0:
                combined_audio = np.concatenate(audio_buffer)
                audio_buffer = []
                silence_counter = 0

                if len(combined_audio) < 1536 * 6:
                    logger.info(f"Skipping short audio buffer ({len(combined_audio)} samples)")
                    continue

                duration_sec = len(combined_audio) / audio_service.SAMPLE_RATE
                logger.info(f"Processing audio buffer ({len(combined_audio)} samples, {duration_sec:.2f}s)...")
                def process_audio_blocking(audio_data):
                    t_text = ""
                    t_meta = {}
                    try:
                        t_text = transcriber.transcribe_buffer(audio_data)
                    except Exception as e:
                        logger.error(f"Transcribe error: {e}")

                    try:
                        t_meta = prosody_tool.analyze_buffer(audio_data)
                    except Exception as e:
                        logger.error(f"Prosody error: {e}")
                        t_meta = {
                            "energy": "Normal",
                            "pitch": "Normal",
                        }

                    return t_text, t_meta

                text, meta = await loop.run_in_executor(
                    executor, process_audio_blocking, combined_audio
                )

                audio_buffer = []
                silence_counter = 0

                if text.strip():
                    logger.info(f"Captured: '{text}' | Tone: {meta}")

                    def transmit_packet_blocking():
                        try:
                            protocol_mode = map_api_mode_to_protocol_mode(control_state.mode)
                            packet = JanusPacket(
                                text=text,
                                mode=protocol_mode,
                                prosody=meta,
                                override_emotion=control_state.emotion_override
                            )
                            link_simulator.transmit(packet.serialize())
                        except Exception as e:
                            logger.error(f"Transmission Error: {e}")

                    await loop.run_in_executor(executor, transmit_packet_blocking)

                    avg_pitch_hz = None
                    avg_energy = None
                    
                    await _emit_events(
                        text=text,
                        avg_pitch_hz=avg_pitch_hz,
                        avg_energy=avg_energy,
                        mode=control_state.mode,
                        transcript_queue=transcript_queue,
                        packet_queue=packet_queue,
                        emotion=str(control_state.emotion_override),
                    )

    except asyncio.CancelledError:
        logger.info("Smart Ear loop cancelled. Cleaning up...")
    finally:
        stop_event.set()
        producer_thread.join(timeout=2)
        if 'link_simulator' in locals():
            link_simulator.close()
        executor.shutdown(wait=False)
        logger.info("Smart Ear stopped.")


async def _emit_events(
    text: str,
    avg_pitch_hz: float | None,
    avg_energy: float | None,
    mode: JanusMode,
    transcript_queue: "asyncio.Queue[TranscriptMessage]",
    packet_queue: "asyncio.Queue[PacketSummaryMessage]",
    emotion: str | None = None,
    snippet_length: int = 60,
) -> None:
    """
    Emit transcript and packet summary events to frontend queues.
    
    Args:
        text: Transcribed text content.
        avg_pitch_hz: Average pitch in Hz, or None if not available.
        avg_energy: Average energy level, or None if not available.
        mode: JanusMode transmission mode.
        transcript_queue: Async queue for transcript messages.
        packet_queue: Async queue for packet summary messages.
    
    Returns:
        None
    """
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

    snippet = text[:snippet_length].strip()

    packet_msg = PacketSummaryMessage(
        type="packet_summary",
        bytes=approximate_bytes,
        mode=mode,
        created_at_ms=now_ms,
        emotion=emotion,
        snippet=snippet if snippet else None,
    )
    await packet_queue.put(packet_msg)
