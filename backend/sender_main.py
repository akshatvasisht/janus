"""
Module: Main Sender Logic (The 'Ear' Controller)
Purpose: Orchestrates the Audio, VAD, Transcription, and Prosody services.
         Implements the 'Hybrid Trigger' logic (Toggle vs. Hold).
         Uses Producer-Consumer pattern to prevent PyAudio buffer overflow.
"""

import queue
import threading
import numpy as np
import time
import os

from services.audio_io import AudioService
from services.vad import VoiceActivityDetector
from services.transcriber import Transcriber
from services.prosody import ProsodyExtractor
from common.protocol import JanusPacket, JanusMode
from services.link_simulator import LinkSimulator

def audio_producer(audio_service, audio_queue, stop_event):
    """
    Thread A (Producer - "The Ear"): Continuously reads audio chunks and puts them in queue.
    Never stops reading to prevent PyAudio buffer overflow.
    """
    while not stop_event.is_set():
        try:
            chunk = audio_service.read_chunk()
            # Put chunk in queue (non-blocking with timeout to check stop_event)
            try:
                audio_queue.put(chunk, timeout=0.1)
            except queue.Full:
                # Queue is full, skip this chunk (prevents memory buildup)
                pass
        except Exception as e:
            print(f"Error in audio producer: {e}")
            # Continue reading even on error to prevent buffer overflow


def audio_consumer(audio_service, vad_model, transcriber, prosody_tool, link_simulator, audio_queue, stop_event):
    """
    Thread B (Consumer - "The Brain"): Processes audio chunks with hybrid trigger logic.
    """
    # Initialize state flags (Controlled by UI via WebSocket later)
    is_streaming_mode = True  # Toggle Mode (Green Button)
    is_recording_hold = False  # Hold Mode (Red Button)
    audio_buffer = []  # List to accumulate audio chunks
    silence_counter = 0  # Counter for silence chunks
    SILENCE_THRESHOLD_CHUNKS = 16  # 500ms ≈ 16 chunks at 512 samples/chunk (32ms per chunk)
    
    # Transmission mode and override emotion (defaults, can be toggled by UI later)
    transmission_mode = JanusMode.SEMANTIC_VOICE
    override_emotion = "Auto"
    
    previous_hold_state = False
    
    while not stop_event.is_set():
        try:
            # Get chunk from queue (blocking with timeout to check stop_event)
            try:
                chunk = audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            
            # B. CHECK TRIGGER LOGIC
            trigger_processing = False
            
            # CASE 1: HOLD MODE (Priority Override)
            if is_recording_hold:
                # Append chunk to audio_buffer
                audio_buffer.append(chunk)
                previous_hold_state = True
                # Continue to next iteration (don't process yet)
                audio_queue.task_done()
                continue
            
            # Check if hold was just released
            if previous_hold_state and not is_recording_hold:
                # Hold was released, trigger processing
                trigger_processing = True
                previous_hold_state = False
            
            # CASE 2: STREAMING MODE (VAD Controlled)
            elif is_streaming_mode:
                # Check VAD
                is_speech = vad_model.is_speech(chunk)
                
                if is_speech:
                    # Speech detected: append chunk and reset silence counter
                    audio_buffer.append(chunk)
                    silence_counter = 0
                else:
                    # Silence detected: increment counter
                    silence_counter += 1
                    # If we have audio in buffer, keep appending during silence
                    # (allows for natural pauses in speech)
                    if len(audio_buffer) > 0:
                        audio_buffer.append(chunk)
                    
                    # Check if silence threshold exceeded
                    if silence_counter > SILENCE_THRESHOLD_CHUNKS:
                        # We have a complete phrase
                        trigger_processing = True
            
            # CASE 3: IDLE
            else:
                # Discard chunk (do nothing)
                audio_queue.task_done()
                continue
            
            # C. PROCESSING (Triggered when Hold is released OR VAD Silence threshold met)
            if trigger_processing and len(audio_buffer) > 0:
                # 1. Combine audio_buffer into single array
                combined_audio = np.concatenate(audio_buffer)
                
                # 2. Transcribe
                try:
                    text = transcriber.transcribe_buffer(combined_audio)
                except Exception as e:
                    print(f"Transcription error: {e}")
                    text = ""
                
                # 3. Extract prosody
                try:
                    meta = prosody_tool.analyze_buffer(combined_audio)
                except Exception as e:
                    print(f"Prosody extraction error: {e}")
                    meta = {'energy': 'Normal', 'pitch': 'Normal'}
                
                # 4. Clear audio_buffer
                audio_buffer = []
                silence_counter = 0
                
                # Clear queue after processing to prevent backlog
                # Drain any remaining chunks in queue to prevent buildup
                while not audio_queue.empty():
                    try:
                        audio_queue.get_nowait()
                        audio_queue.task_done()
                    except queue.Empty:
                        break
                
                # 5. Print/Log results
                if text.strip():  # Only print if we got text
                    print(f"Captured: '{text}' | Tone: {meta}")
                
                # 6. Phase 3: Packet Creation and Transmission
                if text.strip():  # Only send if we have valid text
                    try:
                        # Create Janus Packet
                        packet = JanusPacket(
                            text=text,
                            mode=transmission_mode,
                            prosody=meta,
                            override_emotion=override_emotion
                        )
                        
                        # Serialize packet to binary
                        serialized_bytes = packet.serialize()
                        
                        # Transmit via link simulator (blocks for 300bps simulation)
                        link_simulator.transmit(serialized_bytes)
                    except Exception as e:
                        print(f"Packet transmission error: {e}")
            
            audio_queue.task_done()
            
        except Exception as e:
            print(f"Error in audio consumer: {e}")
            audio_queue.task_done()


def main_loop():
    """
    Main entry point: Sets up Producer-Consumer threads and manages lifecycle.
    """
    # 1. INSTANTIATE SERVICES
    print("Initializing services...")
    audio_service = AudioService()
    vad_model = VoiceActivityDetector()
    transcriber = Transcriber()
    prosody_tool = ProsodyExtractor()
    print("Services initialized.")
    
    # 2. CONFIGURE LINK SIMULATOR
    # Read from environment variables or use defaults
    target_ip = os.getenv("TARGET_IP", "127.0.0.1")
    target_port = int(os.getenv("TARGET_PORT", "5005"))
    
    # Auto-detect TCP mode if ngrok is detected in target IP
    use_tcp = "ngrok" in target_ip.lower() or os.getenv("USE_TCP", "").lower() == "true"
    
    print(f"Link Simulator: {target_ip}:{target_port} ({'TCP' if use_tcp else 'UDP'})")
    link_simulator = LinkSimulator(target_ip=target_ip, target_port=target_port, use_tcp=use_tcp)
    
    # Create thread-safe queue for audio chunks
    audio_queue = queue.Queue(maxsize=100)  # Limit queue size to prevent memory issues
    
    # Create stop event for graceful shutdown
    stop_event = threading.Event()
    
    # Start producer thread (The Ear)
    producer_thread = threading.Thread(
        target=audio_producer,
        args=(audio_service, audio_queue, stop_event),
        daemon=True
    )
    producer_thread.start()
    
    # Start consumer thread (The Brain)
    consumer_thread = threading.Thread(
        target=audio_consumer,
        args=(audio_service, vad_model, transcriber, prosody_tool, link_simulator, audio_queue, stop_event),
        daemon=True
    )
    consumer_thread.start()
    
    print("Audio processing started. Press Ctrl+C to stop.")
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        stop_event.set()
        
        # Wait for threads to finish
        producer_thread.join(timeout=2)
        consumer_thread.join(timeout=2)
        
        # Cleanup services
        audio_service.close()
        link_simulator.close()
        print("Shutdown complete.")


if __name__ == "__main__":
    main_loop()