from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import Optional
from ....schemas.voice import VoiceResult, ModalityStatus

router = APIRouter()

@router.post("/verify", response_model=VoiceResult)
async def verify_voice(
    claimed_subject_id: Optional[str] = Form(None),
    voice_sample: UploadFile = File(...)
):
    # Standalone speaker verification stub
    return VoiceResult(
        status=ModalityStatus.AVAILABLE,
        speech_detected=True,
        identity_similarity=0.85,
        antispoof_score=0.93,
        reason_codes=["VOICE_IDENTITY_MATCH"]
    )

@router.post("/antispoof")
async def evaluate_antispoof(voice_sample: UploadFile = File(...)):
    # Standalone synthetic speech / replay detection
    return {
        "genuine_probability": 0.93,
        "is_synthetic_speech": False,
        "spoof_artifact_score": 0.07
    }

