import time
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import Optional
from ....schemas.face import FaceResult, ModalityStatus
from ....services.face_runtime import face_runtime
from ....face.recognition.exceptions import (
    FaceNotDetectedError, MultipleFacesDetectedError, InvalidImageError,
    ModelUnavailableError, FaceRecognitionError,
)

router = APIRouter()

@router.post("/verify", response_model=FaceResult)
async def verify_face(
    claimed_subject_id: Optional[str] = Form(None),
    face_image: UploadFile = File(...)
):
    started = time.perf_counter()
    try:
        image_bytes = await face_image.read()
        embedding, extraction = face_runtime.extract(image_bytes)
        subject_id, similarity = face_runtime.search(embedding)
        matched = (
            subject_id is not None
            and similarity is not None
            and similarity >= face_runtime_threshold()
        )
        if claimed_subject_id and subject_id != claimed_subject_id:
            matched = False
            subject_id = None
        pad = None
        pad_reason_codes = ["FACE_PAD_UNAVAILABLE"]
        if face_runtime.status.pad_initialized:
            pad = face_runtime.evaluate_pad(image_bytes)
            pad_reason_codes = ["FACE_PAD_THRESHOLD_UNCALIBRATED"]
        return FaceResult(
            status=ModalityStatus.AVAILABLE,
            face_detected=True,
            bounding_box=extraction.bounding_box,
            identity=subject_id if matched else None,
            recognition_state="known" if matched else "unknown",
            identity_similarity=(
                max(0.0, float(similarity)) if similarity is not None else None
            ),
            model_name=extraction.model_name,
            providers=face_runtime.status.providers,
            processing_time_ms=round((time.perf_counter() - started) * 1000, 2),
            liveness_score=pad["real_score"] if pad else None,
            pad_spoof_score=pad["spoof_score"] if pad else None,
            pad_state=pad["pad_state"] if pad else "unavailable",
            pad_provider=pad["provider"] if pad else None,
            reason_codes=(
                ["FACE_IDENTITY_MATCH" if matched else "FACE_IDENTITY_UNKNOWN"]
                + pad_reason_codes
            ),
        )
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except (InvalidImageError, FaceNotDetectedError, MultipleFacesDetectedError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except FaceRecognitionError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


def face_runtime_threshold() -> float:
    from ....core.config import settings
    return settings.FACE_MATCH_THRESHOLD

@router.post("/pad")
async def evaluate_pad(face_image: UploadFile = File(...)):
    try:
        return face_runtime.evaluate_pad(await face_image.read())
    except ModelUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except (InvalidImageError, FaceRecognitionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )


@router.post("/live")
async def process_live_frame(frame: UploadFile = File(...)):
    try:
        return {
            "status": ModalityStatus.AVAILABLE,
            "faces": face_runtime.process_live_frame(await frame.read()),
            "provider": face_runtime.status.providers,
        }
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except (InvalidImageError, FaceRecognitionError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

@router.post("/deepfake")
async def evaluate_deepfake(face_image: UploadFile = File(...)):
    return {
        "status": ModalityStatus.MODEL_UNAVAILABLE,
        "authenticity_probability": None,
        "manipulation_detected": None,
        "reason_codes": ["FACE_DEEPFAKE_MODEL_UNAVAILABLE"],
    }
