from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "TrueFace AI-X"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "temporary-secret-key-for-development-change-in-prod"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/trueface_db"

    # Vector store
    VECTOR_STORE_TYPE: str = "faiss"
    FAISS_INDEX_PATH: str = "backend/app/search/indices/face_gallery.index"
    IDENTITY_MAPPING_PATH: str = "backend/app/search/indices/identity_mapping.json"
    VECTOR_DIMENSION: int = 512

    # Biometric thresholds (validation baseline defaults)
    FACE_MATCH_THRESHOLD: float = 0.75
    VOICE_MATCH_THRESHOLD: float = 0.70
    FACE_LIVENESS_MIN_CONFIDENCE: float = 0.80
    VOICE_LIVENESS_MIN_CONFIDENCE: float = 0.80
    FUSION_WEIGHT_FACE: float = 0.60
    FUSION_WEIGHT_VOICE: float = 0.40

    # Privacy and logs
    LOG_LEVEL: str = "INFO"
    ENABLE_AUDIT_LOGGING: bool = True
    MASK_EMBEDDINGS_IN_LOGS: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()

