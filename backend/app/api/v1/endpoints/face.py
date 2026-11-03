from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from typing import Optional
from ....schemas.face import FaceResult, ModalityStatus

router = APIRouter()

@router.post("/verify", response_model=FaceResult)
async def verify_face(
    claimed_subject_id: Optional[str] = Form(None),
    face_image: UploadFile = File(...)
):
    # Standalone face verification stub
    return FaceResult(
        status=ModalityStatus.AVAILABLE,
        face_detected=True,
        identity_similarity=0.88,
        liveness_score=0.96,
        deepfake_score=0.98,
        reason_codes=["FACE_IDENTITY_MATCH"]
    )

@router.post("/pad")
async def evaluate_pad(face_image: UploadFile = File(...)):
    # Standalone Presentation Attack Detection
    return {
        "liveness_probability": 0.96,
        "is_genuine": True,
        "attack_type_detected": None
    }

@router.post("/deepfake")
async def evaluate_deepfake(face_image: UploadFile = File(...)):
    # Standalone deepfake / facial manipulation detection
    return {
        "authenticity_probability": 0.98,
        "manipulation_detected": False,
        "artifact_confidence": 0.02
    }

