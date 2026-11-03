"""Application runtime for the existing ArcFace/SCRFD recognition engine."""

import hashlib
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..db.models.subject import Subject
from ..db.models.template import BiometricTemplate
from ..face.recognition.arcface_engine import ArcFaceEngine, EmbeddingResult
from ..face.recognition.exceptions import FaceRecognitionError, ModelUnavailableError
from ..search.faiss_store import FAISSStore
try:
    from backend.realtime.config import RealtimeConfig
    from backend.realtime.identity_gallery import IdentityGallery
    from backend.realtime.realtime_recognition import RealtimeRecognizer
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    from realtime.config import RealtimeConfig
    from realtime.identity_gallery import IdentityGallery
    from realtime.realtime_recognition import RealtimeRecognizer


@dataclass
class FaceRuntimeStatus:
    initialized: bool = False
    error: Optional[str] = None
    model_name: str = "arcface_buffalo_l"
    providers: tuple[str, ...] = ()
    template_count: int = 0
    subject_count: int = 0
    skipped_template_count: int = 0
    hydration_error: Optional[str] = None
    hydrated: bool = False


class FaceRuntime:
    """Owns one reusable ArcFace engine and one in-process gallery."""

    def __init__(self) -> None:
        self.engine = ArcFaceEngine(
            model_pack=settings.FACE_MODEL_PACK,
            det_size=(settings.FACE_DET_SIZE, settings.FACE_DET_SIZE),
        )
        self.gallery = FAISSStore(dimension=settings.VECTOR_DIMENSION)
        self.realtime_gallery = IdentityGallery(threshold=settings.FACE_MATCH_THRESHOLD)
        self.realtime: Optional[RealtimeRecognizer] = None
        self.status = FaceRuntimeStatus(
            model_name=f"arcface_{settings.FACE_MODEL_PACK}"
        )

    @property
    def threshold(self) -> float:
        return settings.FACE_MATCH_THRESHOLD

    def initialize(self) -> FaceRuntimeStatus:
        try:
            self.engine.load_model()
            self.status.initialized = True
            self.status.error = None
            self.status.providers = tuple(self.engine.active_providers)
            self.realtime = RealtimeRecognizer(
                self.engine,
                self.realtime_gallery,
                RealtimeConfig(),
            )
        except Exception as exc:
            self.status.initialized = False
            self.status.error = str(exc)
        return self.status

    async def hydrate(self, session: AsyncSession) -> None:
        """Rebuild the searchable gallery from database-backed templates."""
        if not self.status.initialized:
            return
        self.gallery = FAISSStore(dimension=settings.VECTOR_DIMENSION)
        self.realtime_gallery.clear()
        self.status.skipped_template_count = 0
        self.status.hydration_error = None
        result = await session.execute(
            select(BiometricTemplate, Subject.pseudonymous_id)
            .join(Subject, BiometricTemplate.subject_id == Subject.id)
            .where(
                Subject.is_active == True,
                BiometricTemplate.modality == "FACE",
            )
        )
        count = 0
        subjects: set[str] = set()
        for template, subject_id in result.all():
            try:
                if template.embedding is None:
                    raise FaceRecognitionError("Template embedding is missing")
                if template.embedding_dimension != settings.VECTOR_DIMENSION:
                    raise FaceRecognitionError("Template embedding dimension metadata is invalid")
                vector = np.frombuffer(template.embedding, dtype=np.float32)
                vector = self._validate_embedding(vector)
                self.gallery.add_vector(vector, subject_id)
                self.realtime_gallery.enroll(subject_id, subject_id, vector)
                subjects.add(subject_id)
                count += 1
            except (FaceRecognitionError, ValueError):
                self.status.skipped_template_count += 1
        self.status.template_count = count
        self.status.subject_count = len(subjects)
        self.status.hydrated = True

    def process_live_frame(self, image_bytes: bytes) -> list[dict]:
        self._require_ready()
        if self.realtime is None:
            raise ModelUnavailableError("Realtime recognition service is unavailable")
        image = self.engine.load_image_from_bytes(image_bytes)
        results = self.realtime.process_frame(image)
        return [
            {
                "track_id": result.track_id,
                "bounding_box": result.bounding_box,
                "identity": result.match.identity_id if result.match.is_match else None,
                "identity_state": result.identity_state,
                "similarity": (
                    max(0.0, result.match.similarity)
                    if result.match.similarity is not None
                    else None
                ),
                "detection_score": result.detection_score,
                "processing_time_ms": result.total_processing_latency_ms,
                "provider": result.arcface_provider,
            }
            for result in results
        ]

    @staticmethod
    def _validate_embedding(embedding: np.ndarray) -> np.ndarray:
        vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
        if vector.shape != (settings.VECTOR_DIMENSION,):
            raise FaceRecognitionError("Invalid persisted face embedding dimension")
        if not np.all(np.isfinite(vector)):
            raise FaceRecognitionError("Persisted face embedding is non-finite")
        norm = float(np.linalg.norm(vector))
        if norm <= np.finfo(np.float32).eps:
            raise FaceRecognitionError("Persisted face embedding has zero norm")
        return vector / norm

    def _require_ready(self) -> None:
        if not self.status.initialized:
            raise ModelUnavailableError(
                self.status.error or "Face recognition model is unavailable"
            )

    def extract(self, image_bytes: bytes) -> tuple[np.ndarray, EmbeddingResult]:
        self._require_ready()
        image = self.engine.load_image_from_bytes(image_bytes)
        result = self.engine.extract_embedding(image, allow_multiple=False)
        return self._validate_embedding(result.embedding), result

    def search(self, embedding: np.ndarray) -> tuple[Optional[str], Optional[float]]:
        results = self.gallery.search(self._validate_embedding(embedding), top_k=1)
        if not results:
            return None, None
        subject_id, similarity = results[0]
        return subject_id, max(-1.0, min(1.0, float(similarity)))

    async def enroll(
        self,
        session: AsyncSession,
        subject_id: str,
        consent_confirmed: bool,
        image_bytes: bytes,
    ) -> tuple[Subject, EmbeddingResult, bool]:
        if not consent_confirmed:
            from ..core.exceptions import ConsentRequiredError
            raise ConsentRequiredError()
        subject_id = subject_id.strip()
        if not subject_id or len(subject_id) > 64:
            raise ValueError("subject_id must contain 1 to 64 non-whitespace characters")
        embedding, result = self.extract(image_bytes)
        subject_result = await session.execute(
            select(Subject).where(Subject.pseudonymous_id == subject_id)
        )
        subject = subject_result.scalars().first()
        if subject is None:
            subject = Subject(
                pseudonymous_id=subject_id,
                consent_granted=True,
            )
            session.add(subject)
            await session.flush()
        elif not subject.is_active:
            raise FaceRecognitionError("Subject enrollment is inactive")
        elif not subject.consent_granted:
            subject.consent_granted = True
            subject.consent_timestamp = datetime.utcnow()

        digest = hashlib.sha256(embedding.tobytes()).hexdigest()
        duplicate_result = await session.execute(
            select(BiometricTemplate).where(
                BiometricTemplate.subject_id == subject.id,
                BiometricTemplate.modality == "FACE",
                BiometricTemplate.template_hash == digest,
            )
        )
        if duplicate_result.scalars().first() is not None:
            return subject, result, False

        template = BiometricTemplate(
            subject_id=subject.id,
            modality="FACE",
            model_name=result.model_name,
            model_version=settings.FACE_MODEL_PACK,
            vector_store_index=None,
            template_hash=digest,
            embedding=embedding.astype(np.float32).tobytes(),
            embedding_dimension=settings.VECTOR_DIMENSION,
        )
        session.add(template)
        await session.commit()
        index_id = self.gallery.add_vector(embedding, subject_id)
        template.vector_store_index = index_id
        await session.commit()
        self.status.template_count += 1
        self.status.subject_count = max(self.status.subject_count, 1)
        return subject, result, True


face_runtime = FaceRuntime()
