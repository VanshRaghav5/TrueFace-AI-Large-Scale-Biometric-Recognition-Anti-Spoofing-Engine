from fastapi import APIRouter
from ....core.config import settings
from pathlib import Path
from sqlalchemy import text
from ....db.database import get_session_factory
from ....services.face_runtime import face_runtime

router = APIRouter()

@router.get("/health", summary="System Health & Model Readiness")
async def get_health():
    pad_path = Path(settings.FACE_LIVENESS_MODEL_PATH)
    deepfake_path = Path(settings.FACE_DEEPFAKE_MODEL_PATH)
    database_ready = False
    migration_ready = False
    enrolled_count = None
    migration_error = None
    try:
        async with get_session_factory()() as session:
            await session.execute(text("SELECT 1"))
            database_ready = True
            version_result = await session.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            )
            migration_revision = version_result.scalar_one_or_none()
            migration_ready = migration_revision == "20261103_0001"
            from ....db.repositories.subject_repository import SubjectRepository
            enrolled_count = await SubjectRepository(session).count_active()
    except Exception as exc:
        database_ready = False
        migration_error = type(exc).__name__
        migration_revision = None
    face_ready = face_runtime.status.initialized
    return {
        "status": "healthy" if face_ready and database_ready else "degraded",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "vector_store": settings.VECTOR_STORE_TYPE,
        "models": {
            "face_detector": "ready" if face_ready else "unavailable",
            "face_recognizer": "ready" if face_ready else "unavailable",
            "face_model": {
                "status": "ready" if face_ready else "unavailable",
                "model_name": face_runtime.status.model_name,
                "providers": list(face_runtime.status.providers),
                "error": face_runtime.status.error,
            },
            "database": {
                "status": "ready" if database_ready else "unavailable",
                "enrolled_identity_count": enrolled_count,
                "migration_status": "ready" if migration_ready else "unavailable",
                "migration_revision": migration_revision,
                "error_type": migration_error,
                "gallery_hydrated": face_runtime.status.hydrated,
                "template_count": face_runtime.status.template_count,
                "skipped_template_count": face_runtime.status.skipped_template_count,
                "hydration_error": face_runtime.status.hydration_error,
            },
            "face_pad": "configured" if pad_path.is_file() else "unavailable",
            "face_deepfake": "configured" if deepfake_path.is_file() else "unavailable",
            "voice_vad": "unavailable",
            "voice_recognizer": "unavailable",
            "voice_antispoof": "unavailable"
        }
    }
