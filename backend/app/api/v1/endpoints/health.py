from fastapi import APIRouter
from ....core.config import settings
from pathlib import Path
from sqlalchemy import text
from ....db.database import get_session_factory
from ....services.face_runtime import face_runtime
from ....voice.voice_runtime import voice_runtime

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
            "face_pad": {
                "status": "ready" if face_runtime.status.pad_initialized else "unavailable",
                "model_name": face_runtime.status.pad_model_name,
                "provider": face_runtime.status.pad_provider,
                "error": face_runtime.status.pad_error,
            },
            "face_deepfake": "configured" if deepfake_path.is_file() else "unavailable",
            "voice": {
                "status": "ready" if voice_runtime.status.initialized else "unavailable",
                "recognizer": "ready" if voice_runtime.status.initialized else "unavailable",
                "antispoof": "ready" if voice_runtime.status.antispoof_initialized else "fallback",
                "vad": "ready",
                "model_name": voice_runtime.status.model_name,
                "model_version": voice_runtime.status.model_version,
                "embedding_dimension": voice_runtime.status.dimension,
                "model_source": voice_runtime.status.model_source,
                "error": voice_runtime.status.error,
                "antispoof_model_name": voice_runtime.status.antispoof_model_name,
                "antispoof_error": voice_runtime.status.antispoof_error,
            },
            "voice_recognizer": "ready" if voice_runtime.status.initialized else "unavailable",
            "voice_antispoof": "ready" if voice_runtime.status.antispoof_initialized else "fallback",
            "voice_vad": "ready",
        }
    }
