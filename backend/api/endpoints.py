"""
API endpoints for RESTful HTTP requests.

Provides health check and voice verification endpoints for the Janus backend.
Handles file uploads and voice cloning verification.
"""

import os
from difflib import SequenceMatcher
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..services.transcriber import Transcriber

router = APIRouter()

# Verification phrase for voice cloning
VERIFICATION_PHRASE = "The quick brown fox jumps over the lazy dog."
SIMILARITY_THRESHOLD = 0.8

@router.get("/health")
async def health_check() -> dict:
    """
    Basic health check route.
    
    Returns:
        dict: Status dictionary with "status" key set to "ok".
    """
    return {"status": "ok"}

@router.post("/voice/verify")
async def verify_voice(audio_file: UploadFile = File(...)) -> dict:
    """
    Verify and save voice reference audio.
    
    Accepts an audio file, transcribes it, and verifies it matches
    the verification phrase. If successful, saves as reference_audio.wav.
    
    Args:
        audio_file: Uploaded audio file (supports WAV, WebM, etc.)
    
    Returns:
        dict: {"status": "verified"} on success, {"status": "failed", "transcript": "..."} on failure
    """
    # Determine backend directory path
    backend_dir = Path(__file__).parent.parent
    temp_file_path = backend_dir / "temp_reference.wav"
    reference_file_path = backend_dir / "reference_audio.wav"
    
    try:
        # Save uploaded file to temporary location
        with open(temp_file_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)
        
        # Transcribe the audio file
        transcriber = Transcriber()
        transcript = transcriber.transcribe_file(str(temp_file_path))
        
        # Normalize for comparison (case-insensitive, strip punctuation)
        normalized_transcript = transcript.lower().strip()
        normalized_phrase = VERIFICATION_PHRASE.lower().strip()
        
        # Calculate similarity using SequenceMatcher
        similarity = SequenceMatcher(None, normalized_transcript, normalized_phrase).ratio()
        
        # Check if similarity meets threshold
        if similarity >= SIMILARITY_THRESHOLD:
            # Save to persistent reference file
            with open(reference_file_path, "wb") as f:
                f.write(content)
            
            return {"status": "verified"}
        else:
            return {
                "status": "failed",
                "transcript": transcript
            }
    
    except Exception as e:
        # Return error with transcript if available
        return {
            "status": "failed",
            "transcript": str(e) if "transcript" not in locals() else transcript
        }
    
    finally:
        # Always clean up temporary file
        if temp_file_path.exists():
            try:
                os.remove(temp_file_path)
            except Exception as e:
                # Log but don't fail the request
                print(f"Warning: Could not remove temp file {temp_file_path}: {e}")

