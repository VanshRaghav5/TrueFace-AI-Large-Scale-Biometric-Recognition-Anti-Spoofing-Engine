from fastapi import APIRouter
from ....core.config import settings

router = APIRouter()

@router.get("/health", summary="System Health & Model Readiness")
async def get_health():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "vector_store": settings.VECTOR_STORE_TYPE,
        "models": {
            "face_detector": "ready",
            "face_recognizer": "ready",
            "face_pad": "ready",
            "face_deepfake": "ready",
            "voice_vad": "ready",
            "voice_recognizer": "ready",
            "voice_antispoof": "ready"
        }
    }

