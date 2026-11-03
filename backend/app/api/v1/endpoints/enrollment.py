from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import Optional
from ....schemas.enrollment import EnrollmentResponse
from ....services.enrollment_service import EnrollmentService
from ....core.exceptions import ConsentRequiredError

router = APIRouter()
enrollment_service = EnrollmentService()

@router.post("/enrollment", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_subject(
    subject_id: str = Form(...),
    consent_confirmed: bool = Form(...),
    face_image: Optional[UploadFile] = File(None),
    voice_sample: Optional[UploadFile] = File(None)
):
    try:
        face_bytes = await face_image.read() if face_image else None
        voice_bytes = await voice_sample.read() if voice_sample else None

        result = await enrollment_service.enroll_subject(
            subject_id=subject_id,
            consent_confirmed=consent_confirmed,
            face_bytes=face_bytes,
            voice_bytes=voice_bytes
        )
        return result
    except ConsentRequiredError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

