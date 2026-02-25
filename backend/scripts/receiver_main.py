"""
Module: Main Receiver Logic
Purpose: Orchestrates the listening loop, packet deserialization, synthesis, and playback.
         Listens for incoming JanusPackets, synthesizes audio, and plays it through the audio service.
"""

import logging
import os
import queue
import socket
import struct
import threading

from dotenv import load_dotenv

from backend.common.protocol import JanusMode, JanusPacket
from backend.services.audio_io import AudioService
from backend.services.synthesizer import Synthesizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def recv_exact(sock: socket.socket, n: int) -> bytes | None:
    """
    Helper function to receive exactly n bytes from a socket.
    Handles fragmented reads that can occur with TCP.
    
    Args:
        sock: The socket to read from.
        n: Number of bytes to read.
        
    Returns:
        bytes | None: Exactly n bytes, or None if connection closed
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
    
    Continuously pulls audio bytes from queue and plays them.
    Prevents blocking the main receiver loop.
    
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
                audio_service.write_chunk(audio_bytes)
            
            playback_queue.task_done()
            
        except Exception as e:
            logger.error(f"Playback error: {e}")
            playback_queue.task_done()


def receiver_loop(stop_event: threading.Event | None = None) -> None:
    """
    Main receiver loop entry point.
    
    Listens for incoming packets, deserializes JanusPackets, synthesizes audio,
    and plays it through the audio service. Supports both TCP and UDP protocols.
    Configuration is loaded from environment variables.
    
    Args:
        stop_event: Optional threading event to signal shutdown. If None, creates
                   an internal event and waits for KeyboardInterrupt. If provided,
                   exits when the event is set.
    
    Returns:
        None
    
    Raises:
        ValueError: If FISH_AUDIO_API_KEY environment variable is not set.
    """
    load_dotenv()
    
    receiver_port = int(os.getenv("RECEIVER_PORT", "5005"))
    reference_audio_path = os.getenv("REFERENCE_AUDIO_PATH", None)
    use_tcp = os.getenv("USE_TCP", "").lower() == "true"
    
    audio_service = AudioService()
    synthesizer = Synthesizer(reference_audio_path=reference_audio_path)
    
    listen_sock = None
    if use_tcp:
        listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_sock.bind(('0.0.0.0', receiver_port))
        listen_sock.listen(1)
        logger.info(f"Listening for Transmissions on TCP port {receiver_port}...")
        sock, addr = listen_sock.accept()
        logger.info(f"Connection established from {addr}")
    else:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', receiver_port))
        logger.info(f"Listening for Transmissions on UDP port {receiver_port}...")
    
    playback_queue = queue.Queue(maxsize=100)
    
    # Use provided stop_event or create internal one
    if stop_event is None:
        stop_event = threading.Event()
        use_keyboard_interrupt = True
    else:
        use_keyboard_interrupt = False
    
    playback_thread = threading.Thread(
        target=playback_worker,
        args=(audio_service, playback_queue, stop_event),
        daemon=True
    )
    playback_thread.start()

    try:
        while True:
            # Exit if stop_event is set (test mode)
            if not use_keyboard_interrupt and stop_event.is_set():
                break
                
            try:
                if use_tcp:
                    length_bytes = recv_exact(sock, 4)
                    if length_bytes is None:
                        logger.info("Connection closed by sender")
                        break
                    
                    payload_length = struct.unpack('>I', length_bytes)[0]
                    data = recv_exact(sock, payload_length)
                    if data is None:
                        logger.info("Connection closed while reading packet")
                        break
                else:
                    # Set timeout for UDP to allow periodic stop_event checking
                    sock.settimeout(0.5)
                    try:
                        data, addr = sock.recvfrom(4096)
                    except socket.timeout:
                        continue

                try:
                    packet = JanusPacket.deserialize(data)
                except Exception as e:
                    logger.error(f"Corrupt packet received: {e}")
                    continue

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
                
                mode_names = {
                    JanusMode.SEMANTIC_VOICE: "Semantic Voice",
                    JanusMode.TEXT_ONLY: "Text Only",
                    JanusMode.MORSE_CODE: "Morse Code"
                }
                mode_name = mode_names.get(packet.mode, "Unknown")
                
                logger.info(f"[RECEIVED] [{mode_name}] '{packet.text}'")
                logger.debug(f"   Meta: Energy={packet.prosody.get('energy', 'N/A')}, "
                      f"Pitch={packet.prosody.get('pitch', 'N/A')} -> Prompt: [{emotion_tag}]")

                try:
                    result = synthesizer.synthesize(packet, stream=True)
                    from typing import Generator
                    if isinstance(result, Generator):
                        for audio_chunk in result:
                            if audio_chunk:
                                try:
                                    playback_queue.put(audio_chunk, timeout=0.1)
                                except queue.Full:
                                    logger.warning("Playback queue full, skipping chunk")
                    else:
                        if result:
                            try:
                                playback_queue.put(result, timeout=0.1)
                            except queue.Full:
                                logger.warning("Playback queue full, skipping audio")
                except Exception as e:
                    logger.error(f"Synthesis error: {e}")
                    continue

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Receiver Error: {e}")
                continue
    
    finally:
        logger.info("Shutting down...")
        stop_event.set()
        playback_thread.join(timeout=2)
        
        if sock:
            sock.close()
        if listen_sock:
            listen_sock.close()
        
        audio_service.close()
        
        logger.info("Shutdown complete.")


if __name__ == "__main__":
    receiver_loop()