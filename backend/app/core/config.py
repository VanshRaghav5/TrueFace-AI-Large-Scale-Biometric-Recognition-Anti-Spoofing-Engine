from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PROJECT_NAME: str = "TrueFace AI-X"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "temporary-secret-key-for-development-change-in-prod"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "trueface_db"
    DATABASE_URL: Optional[str] = None

    VECTOR_STORE_TYPE: str = "faiss"
    FAISS_INDEX_PATH: str = "backend/app/search/indices/face_gallery.index"
    IDENTITY_MAPPING_PATH: str = "backend/app/search/indices/identity_mapping.json"
    VECTOR_DIMENSION: int = 512
    FACE_MODEL_PACK: str = "buffalo_l"
    FACE_DET_SIZE: int = 640
    FACE_LIVENESS_MODEL_PATH: str = "models/liveness/anti-spoof-mn3.onnx"
    FACE_DEEPFAKE_MODEL_PATH: str = "models/deepfake/manipulation_model.onnx"

    FACE_MATCH_THRESHOLD: float = 0.75
    VOICE_MATCH_THRESHOLD: float = 0.70
    FACE_LIVENESS_MIN_CONFIDENCE: float = 0.80
    VOICE_LIVENESS_MIN_CONFIDENCE: float = 0.80
    FUSION_WEIGHT_FACE: float = 0.60
    FUSION_WEIGHT_VOICE: float = 0.40

    LOG_LEVEL: str = "INFO"
    ENABLE_AUDIT_LOGGING: bool = True
    MASK_EMBEDDINGS_IN_LOGS: bool = True

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if not self.POSTGRES_PASSWORD:
            raise RuntimeError(
                "Database is not configured. Set DATABASE_URL or POSTGRES_PASSWORD."
            )
        return (
            "postgresql+asyncpg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
