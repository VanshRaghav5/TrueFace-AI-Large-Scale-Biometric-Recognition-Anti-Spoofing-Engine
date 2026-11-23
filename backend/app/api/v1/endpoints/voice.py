from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ....schemas.voice import VoiceResult, ModalityStatus
from ....voice.voice_runtime import voice_runtime
from ....db.database import get_db

router = APIRouter()

@router.post("/verify", response_model=VoiceResult)
async def verify_voice(
    claimed_subject_id: Optional[str] = Form(None),
    voice_sample: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
):
    try:
        content = await voice_sample.read()
        return await voice_runtime.verify(content, claimed_subject_id=claimed_subject_id, session=session)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Voice verification failed: {str(exc)}",
        )

@router.post("/antispoof")
async def evaluate_antispoof(voice_sample: UploadFile = File(...)):
    try:
        content = await voice_sample.read()
        return await voice_runtime.evaluate_antispoof(content)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Voice anti-spoof evaluation failed: {str(exc)}",
        )
