"""
Module: Main Sender Logic (The 'Ear' Controller)
Purpose: Orchestrates the Audio, VAD, Transcription, and Prosody services.
         Implements the 'Hybrid Trigger' logic (Toggle vs. Hold).
         Uses Producer-Consumer pattern to prevent PyAudio buffer overflow.
"""

# Standard library imports
import os
import queue
import threading
import time

# Third-party imports
import numpy as np

# Local imports
from backend.common.protocol import JanusMode, JanusPacket
from backend.services.audio_io import AudioService
from backend.services.link_simulator import LinkSimulator
from backend.services.prosody import ProsodyExtractor
from backend.services.transcriber import Transcriber
from backend.services.vad import VoiceActivityDetector

def audio_producer(
    audio_service: AudioService,
    audio_queue: queue.Queue[np.ndarray],
    stop_event: threading.Event,
) -> None:
    """
    Thread A (Producer - "The Ear"): Continuously reads audio chunks and puts them in queue.
    
    Never stops reading to prevent PyAudio buffer overflow.
    
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
            print(f"Error in audio producer: {e}")


def audio_consumer(
    audio_service: AudioService,
    vad_model: VoiceActivityDetector,
    transcriber: Transcriber,
    prosody_tool: ProsodyExtractor,
    link_simulator: LinkSimulator,
    audio_queue: queue.Queue[np.ndarray],
    stop_event: threading.Event,
) -> None:
    """
    Thread B (Consumer - "The Brain"): Processes audio chunks with hybrid trigger logic.
    
    Args:
        audio_service: AudioService instance for reading audio input.
        vad_model: VoiceActivityDetector instance for speech detection.
        transcriber: Transcriber instance for speech-to-text conversion.
        prosody_tool: ProsodyExtractor instance for emotion metadata extraction.
        link_simulator: LinkSimulator instance for packet transmission.
        audio_queue: Queue containing audio chunks (numpy arrays) to process.
        stop_event: Threading event to signal shutdown. Consumer exits when set.
    
    Returns:
        None
    """
    is_streaming_mode = True
    is_recording_hold = False
    audio_buffer = []
    silence_counter = 0
    SILENCE_THRESHOLD_CHUNKS = 16
    
    transmission_mode = JanusMode.SEMANTIC_VOICE
    override_emotion = "Auto"
    
    previous_hold_state = False
    
    while not stop_event.is_set():
        try:
            try:
                chunk = audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            
            trigger_processing = False
            
            if is_recording_hold:
                audio_buffer.append(chunk)
                previous_hold_state = True
                audio_queue.task_done()
                continue
            
            if previous_hold_state and not is_recording_hold:
                trigger_processing = True
                previous_hold_state = False
            
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
            
            else:
                audio_queue.task_done()
                continue
            
            if trigger_processing and len(audio_buffer) > 0:
                combined_audio = np.concatenate(audio_buffer)
                
                try:
                    text = transcriber.transcribe_buffer(combined_audio)
                except Exception as e:
                    print(f"Transcription error: {e}")
                    text = ""
                
                try:
                    meta = prosody_tool.analyze_buffer(combined_audio)
                except Exception as e:
                    print(f"Prosody extraction error: {e}")
                    meta = {'energy': 'Normal', 'pitch': 'Normal'}
                
                audio_buffer = []
                silence_counter = 0
                
                while not audio_queue.empty():
                    try:
                        audio_queue.get_nowait()
                        audio_queue.task_done()
                    except queue.Empty:
                        break
                
                if text.strip():
                    print(f"Captured: '{text}' | Tone: {meta}")
                
                if text.strip():
                    try:
                        packet = JanusPacket(
                            text=text,
                            mode=transmission_mode,
                            prosody=meta,
                            override_emotion=override_emotion
                        )
                        serialized_bytes = packet.serialize()
                        link_simulator.transmit(serialized_bytes)
                    except Exception as e:
                        print(f"Packet transmission error: {e}")
            
            audio_queue.task_done()
            
        except Exception as e:
            print(f"Error in audio consumer: {e}")
            audio_queue.task_done()


def main_loop() -> None:
    """
    Main entry point for the sender application.
    
    Initializes audio processing services and sets up producer-consumer threads
    for continuous audio capture and processing. Manages application lifecycle
    and graceful shutdown on interrupt.
    
    Returns:
        None
    """
    print("Initializing services...")
    audio_service = AudioService()
    vad_model = VoiceActivityDetector()
    transcriber = Transcriber()
    prosody_tool = ProsodyExtractor()
    print("Services initialized.")
    
    target_ip = os.getenv("TARGET_IP", "127.0.0.1")
    target_port = int(os.getenv("TARGET_PORT", "5005"))
    use_tcp = "ngrok" in target_ip.lower() or os.getenv("USE_TCP", "").lower() == "true"
    
    print(f"Link Simulator: {target_ip}:{target_port} ({'TCP' if use_tcp else 'UDP'})")
    link_simulator = LinkSimulator(target_ip=target_ip, target_port=target_port, use_tcp=use_tcp)
    
    audio_queue = queue.Queue(maxsize=100)
    stop_event = threading.Event()
    
    producer_thread = threading.Thread(
        target=audio_producer,
        args=(audio_service, audio_queue, stop_event),
        daemon=True
    )
    producer_thread.start()
    
    consumer_thread = threading.Thread(
        target=audio_consumer,
        args=(audio_service, vad_model, transcriber, prosody_tool, link_simulator, audio_queue, stop_event),
        daemon=True
    )
    consumer_thread.start()
    
    print("Audio processing started. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        stop_event.set()
        producer_thread.join(timeout=2)
        consumer_thread.join(timeout=2)
        audio_service.close()
        link_simulator.close()
        print("Shutdown complete.")


if __name__ == "__main__":
    main_loop()