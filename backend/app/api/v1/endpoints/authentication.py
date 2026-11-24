from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ....schemas.authentication import AuthenticationResponse
from ....services.authentication_service_optimized import AuthenticationServiceOptimized
from ....services.audit_service import AuditService
from ....db.database import get_db
import asyncio

router = APIRouter()
auth_service = AuthenticationServiceOptimized()
audit_service = AuditService()

@router.post("/verify", response_model=AuthenticationResponse)
async def verify_biometrics(
    claimed_subject_id: Optional[str] = Form(None),
    face_image: Optional[UploadFile] = File(None),
    voice_sample: Optional[UploadFile] = File(None),
    security_pin: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_db),
):
    try:
        # Read uploaded files in parallel for faster I/O
        read_tasks = []
        if face_image:
            read_tasks.append(face_image.read())
        if voice_sample:
            read_tasks.append(voice_sample.read())
        
        if len(read_tasks) == 2:
            face_bytes, voice_bytes = await asyncio.gather(*read_tasks)
        elif len(read_tasks) == 1:
            if face_image:
                face_bytes = await read_tasks[0]
                voice_bytes = None
            else:
                voice_bytes = await read_tasks[0]
                face_bytes = None
        else:
            face_bytes, voice_bytes = None, None

        # Optimized verification with parallel processing
        result = await auth_service.verify(
            claimed_subject_id=claimed_subject_id,
            face_bytes=face_bytes,
            voice_bytes=voice_bytes,
            security_pin=security_pin,
            session=session,
        )

        # Asynchronously record audit event (don't wait for it)
        asyncio.create_task(audit_service.record_verification(result, session))
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Biometric processing failed: {str(e)}"
        )
