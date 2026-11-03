from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import Optional
from ....schemas.authentication import AuthenticationResponse
from ....services.authentication_service import AuthenticationService
from ....services.audit_service import AuditService

router = APIRouter()
auth_service = AuthenticationService()
audit_service = AuditService()

@router.post("/verify", response_model=AuthenticationResponse)
async def verify_biometrics(
    claimed_subject_id: Optional[str] = Form(None),
    face_image: Optional[UploadFile] = File(None),
    voice_sample: Optional[UploadFile] = File(None)
):
    try:
        face_bytes = await face_image.read() if face_image else None
        voice_bytes = await voice_sample.read() if voice_sample else None

        result = await auth_service.verify(
            claimed_subject_id=claimed_subject_id,
            face_bytes=face_bytes,
            voice_bytes=voice_bytes
        )

        # Asynchronously record audit event
        await audit_service.record_verification(result)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Biometric processing failed: {str(e)}"
        )

