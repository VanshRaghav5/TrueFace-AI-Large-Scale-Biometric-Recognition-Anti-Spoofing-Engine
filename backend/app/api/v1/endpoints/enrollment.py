from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from typing import Optional
from ....schemas.enrollment import EnrollmentResponse
from ....services.enrollment_service import EnrollmentService
from ....core.exceptions import ConsentRequiredError
from ....core.exceptions import ModelUnavailableError
from ....db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
enrollment_service = EnrollmentService()

@router.post("/enrollment", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_subject(
    subject_id: str = Form(...),
    consent_confirmed: bool = Form(...),
    face_image: Optional[UploadFile] = File(None),
    voice_sample: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_db),
):
    try:
        face_bytes = await face_image.read() if face_image else None
        voice_bytes = await voice_sample.read() if voice_sample else None

        result = await enrollment_service.enroll_subject(
            subject_id=subject_id,
            consent_confirmed=consent_confirmed,
            session=session,
            face_bytes=face_bytes,
            voice_bytes=voice_bytes
        )
        return result
    except ConsentRequiredError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ModelUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/enrollment")
async def list_enrollments(session: AsyncSession = Depends(get_db)):
    return {"items": await enrollment_service.list_subjects(session)}


@router.delete("/enrollment/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_enrollment(
    subject_id: str,
    session: AsyncSession = Depends(get_db),
):
    deleted = await enrollment_service.delete_subject(session, subject_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
