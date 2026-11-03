from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import Optional
from ....schemas.voice import VoiceResult, ModalityStatus

router = APIRouter()

@router.post("/verify", response_model=VoiceResult)
async def verify_voice(
    claimed_subject_id: Optional[str] = Form(None),
    voice_sample: UploadFile = File(...)
):
    return VoiceResult(
        status=ModalityStatus.MODEL_UNAVAILABLE,
        speech_detected=False,
        reason_codes=["VOICE_MODEL_UNAVAILABLE"],
    )

@router.post("/antispoof")
async def evaluate_antispoof(voice_sample: UploadFile = File(...)):
    return {
        "status": ModalityStatus.MODEL_UNAVAILABLE,
        "genuine_probability": None,
        "is_synthetic_speech": None,
        "reason_codes": ["VOICE_ANTISPOOF_MODEL_UNAVAILABLE"],
    }
