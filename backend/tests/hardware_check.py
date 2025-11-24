"""
Hardware Reality Check Script
Purpose: Tests actual PyAudio hardware without mocking.
Records 1 second of real audio and saves to test_output.wav.
If the file is silence/static, indicates OS audio driver issues.
"""

# Standard library imports
import os
import sys
import wave

# Third-party imports
import numpy as np
import pyaudio

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Local imports
from services.audio_io import AudioService


def record_audio_test(duration=1.0, output_file='test_output.wav'):
    """
    Record real audio from microphone and save to WAV file.
    
    Args:
        duration: Recording duration in seconds
        output_file: Output WAV file path
    """
    print(f"Hardware Reality Check: Recording {duration} second(s) of audio...")
    print("Make sure your microphone is connected and not muted!")
    
    # Audio configuration
    SAMPLE_RATE = 16000
    CHUNK_SIZE = 512
    CHANNELS = 1
    FORMAT = pyaudio.paInt16
    
    # Initialize PyAudio
    try:
        p = pyaudio.PyAudio()
        print(f"✓ PyAudio initialized successfully")
        print(f"  Sample Rate: {SAMPLE_RATE} Hz")
        print(f"  Channels: {CHANNELS} (Mono)")
        print(f"  Format: 16-bit integer")
    except Exception as e:
        print(f"✗ Failed to initialize PyAudio: {e}")
        return False
    
    # List available input devices
    print("\nAvailable input devices:")
    try:
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"  [{i}] {info['name']} - {info['maxInputChannels']} input channel(s)")
    except Exception as e:
        print(f"  Warning: Could not list devices: {e}")
    
    # Open input stream
    try:
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE
        )
        print(f"\n✓ Input stream opened successfully")
    except Exception as e:
        print(f"✗ Failed to open input stream: {e}")
        print("  This usually means:")
        print("    - No microphone is connected")
        print("    - Microphone is muted in OS settings")
        print("    - Audio driver is not working")
        p.terminate()
        return False
    
    # Record audio
    print(f"\nRecording... (speak into your microphone)")
    frames = []
    num_chunks = int(SAMPLE_RATE / CHUNK_SIZE * duration)
    
    try:
        for i in range(num_chunks):
            data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            frames.append(data)
            if (i + 1) % 10 == 0:
                print(f"  Progress: {int((i + 1) / num_chunks * 100)}%")
    except Exception as e:
        print(f"✗ Error during recording: {e}")
        stream.stop_stream()
        stream.close()
        p.terminate()
        return False
    
    print("✓ Recording complete")
    
    # Stop and close stream
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # Save to WAV file
    try:
        wf = wave.open(output_file, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        print(f"\n✓ Audio saved to: {output_file}")
    except Exception as e:
        print(f"✗ Failed to save WAV file: {e}")
        return False
    
    # Analyze the recorded audio
    try:
        # Convert frames to numpy array
        audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
        audio_float = audio_data.astype(np.float32) / 32768.0
        
        # Calculate RMS (energy)
        rms = np.sqrt(np.mean(audio_float ** 2))
        
        # Calculate max amplitude
        max_amp = np.max(np.abs(audio_float))
        
        print(f"\nAudio Analysis:")
        print(f"  RMS (Energy): {rms:.4f}")
        print(f"  Max Amplitude: {max_amp:.4f}")
        
        # Check if audio is likely silence
        if rms < 0.01:
            print(f"\n⚠ WARNING: Audio appears to be silence (RMS < 0.01)")
            print(f"  Possible issues:")
            print(f"    - Microphone is muted")
            print(f"    - Microphone volume is too low")
            print(f"    - Wrong microphone selected")
            print(f"    - Audio driver problem")
            return False
        elif max_amp < 0.1:
            print(f"\n⚠ WARNING: Audio levels are very low (Max < 0.1)")
            print(f"  Consider increasing microphone volume")
        else:
            print(f"\n✓ Audio levels look good!")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to analyze audio: {e}")
        return False


def test_audio_service():
    """Test AudioService with real hardware."""
    print("\n" + "="*60)
    print("Testing AudioService with real hardware...")
    print("="*60)
    
    try:
        audio_service = AudioService()
        print("✓ AudioService initialized")
        
        # Try reading a few chunks
        print("\nReading audio chunks...")
        for i in range(5):
            chunk = audio_service.read_chunk()
            print(f"  Chunk {i+1}: shape={chunk.shape}, dtype={chunk.dtype}, "
                  f"min={chunk.min():.4f}, max={chunk.max():.4f}")
        
        audio_service.close()
        print("\n✓ AudioService test complete")
        return True
        
    except Exception as e:
        print(f"\n✗ AudioService test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("="*60)
    print("Hardware Reality Check - Audio Input Test")
    print("="*60)
    print("\nThis script tests your actual audio hardware without mocking.")
    print("It will:")
    print("  1. Record 1 second of audio from your microphone")
    print("  2. Save it to test_output.wav")
    print("  3. Analyze the audio levels")
    print("  4. Test AudioService initialization")
    print()
    
    # Test 1: Record audio
    success1 = record_audio_test(duration=1.0, output_file='test_output.wav')
    
    # Test 2: Test AudioService
    success2 = test_audio_service()
    
    # Summary
    print("\n" + "="*60)
    print("Summary:")
    print("="*60)
    if success1 and success2:
        print("✓ All hardware checks passed!")
        print("  Your audio setup is working correctly.")
    else:
        print("✗ Some hardware checks failed.")
        print("  Please check:")
        print("    - Microphone is connected and not muted")
        print("    - Audio drivers are installed")
        print("    - Correct microphone is selected in OS settings")
        print("    - Microphone volume is adequate")
    
    print(f"\nOutput file: {os.path.abspath('test_output.wav')}")
    print("  Play this file to verify audio was recorded correctly.")

