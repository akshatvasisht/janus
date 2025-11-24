"""
API endpoints for RESTful HTTP requests.

Provides health check and voice verification endpoints for the Janus backend.
Handles file uploads and voice cloning verification.
"""

# Standard library imports
import os
from difflib import SequenceMatcher
from pathlib import Path

# Third-party imports
from fastapi import APIRouter, File, HTTPException, UploadFile

# Local imports
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
    backend_dir = Path(__file__).parent.parent
    temp_file_path = backend_dir / "temp_reference.wav"
    reference_file_path = backend_dir / "reference_audio.wav"
    
    try:
        with open(temp_file_path, "wb") as f:
            content = await audio_file.read()
            f.write(content)
        
        transcriber = Transcriber()
        transcript = transcriber.transcribe_file(str(temp_file_path))
        
        normalized_transcript = transcript.lower().strip()
        normalized_phrase = VERIFICATION_PHRASE.lower().strip()
        
        similarity = SequenceMatcher(None, normalized_transcript, normalized_phrase).ratio()
        
        if similarity >= SIMILARITY_THRESHOLD:
            with open(reference_file_path, "wb") as f:
                f.write(content)
            
            return {"status": "verified"}
        else:
            return {
                "status": "failed",
                "transcript": transcript
            }
    
    except Exception as e:
        return {
            "status": "failed",
            "transcript": str(e) if "transcript" not in locals() else transcript
        }
    
    finally:
        if temp_file_path.exists():
            try:
                os.remove(temp_file_path)
            except Exception as e:
                print(f"Warning: Could not remove temp file {temp_file_path}: {e}")

