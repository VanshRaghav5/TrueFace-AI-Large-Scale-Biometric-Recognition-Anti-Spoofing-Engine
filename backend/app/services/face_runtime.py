"""Application runtime for the existing ArcFace/SCRFD recognition engine."""

import hashlib
import time
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..db.models.subject import Subject
from ..db.models.template import BiometricTemplate
from ..face.recognition.arcface_engine import ArcFaceEngine, EmbeddingResult
from ..face.recognition.exceptions import FaceRecognitionError, ModelUnavailableError
from ..face.liveness import (
    AntiSpoofMn3Config,
    AntiSpoofMn3Engine,
    MiniFASNetConfig,
    MiniFASNetEnsemble,
)
from ..face.deepfake import (
    DeepfakeDetectorConfig,
    DeepfakeDetectorEngine,
)
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
    pad_initialized: bool = False
    pad_error: Optional[str] = None
    pad_model_name: str = "minifasnet_ensemble"
    pad_provider: Optional[str] = None
    deepfake_initialized: bool = False
    deepfake_error: Optional[str] = None
    deepfake_model_name: str = "deepfakebench_mesonet"
    deepfake_provider: Optional[str] = None


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
        self.pad: Optional[Union[MiniFASNetEnsemble, AntiSpoofMn3Engine]] = None
        self.deepfake: Optional[DeepfakeDetectorEngine] = None
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
            self._initialize_pad()
            self._initialize_deepfake()
            self.realtime = RealtimeRecognizer(
                self.engine,
                self.realtime_gallery,
                RealtimeConfig(),
                pad_adapter=self.pad,
                pad_threshold=settings.FACE_LIVENESS_MIN_CONFIDENCE if self.pad else None,
            )
        except Exception as exc:
            self.status.initialized = False
            self.status.error = str(exc)
        return self.status

    @staticmethod
    def _model_path(configured_path: str) -> Path:
        path = Path(configured_path)
        if path.is_absolute():
            return path
        return Path(__file__).resolve().parents[3] / path

    def _initialize_pad(self) -> None:
        # Check for Silent-Face-Anti-Spoofing MiniFASNet models first
        v2_path = self._model_path(settings.FACE_LIVENESS_V2_PATH)
        v1se_path = self._model_path(settings.FACE_LIVENESS_V1SE_PATH)
        if v2_path.is_file() and v1se_path.is_file():
            try:
                ensemble = MiniFASNetEnsemble(
                    MiniFASNetConfig(v2_path=v2_path, v1se_path=v1se_path)
                )
                ensemble.load_model()
                self.pad = ensemble
                self.status.pad_initialized = True
                self.status.pad_error = None
                self.status.pad_model_name = ensemble.config.model_name
                self.status.pad_provider = ensemble.execution_provider
                return
            except Exception as exc:
                self.pad = None
                self.status.pad_initialized = False
                self.status.pad_error = f"Failed to load MiniFASNet ensemble: {exc}"
                self.status.pad_provider = None
                return

        # Fallback to single-model anti-spoof-mn3
        model_path = self._model_path(settings.FACE_LIVENESS_MODEL_PATH)
        if not model_path.is_file():
            self.pad = None
            self.status.pad_initialized = False
            self.status.pad_error = None
            self.status.pad_provider = None
            return
        try:
            pad = AntiSpoofMn3Engine(
                AntiSpoofMn3Config(model_path=model_path)
            )
            pad.load_model()
            self.pad = pad
            self.status.pad_initialized = True
            self.status.pad_error = None
            self.status.pad_model_name = "anti-spoof-mn3"
            self.status.pad_provider = pad.execution_provider
        except Exception as exc:
            self.pad = None
            self.status.pad_initialized = False
            self.status.pad_error = str(exc)
            self.status.pad_provider = None

    def _initialize_deepfake(self) -> None:
        model_path = self._model_path(settings.FACE_DEEPFAKE_MODEL_PATH)
        if not model_path.is_file():
            self.deepfake = None
            self.status.deepfake_initialized = False
            self.status.deepfake_error = None
            self.status.deepfake_provider = None
            return
        try:
            deepfake = DeepfakeDetectorEngine(
                DeepfakeDetectorConfig(
                    model_path=model_path,
                    min_authenticity_threshold=settings.FACE_DEEPFAKE_MIN_AUTHENTICITY,
                )
            )
            deepfake.load_model()
            self.deepfake = deepfake
            self.status.deepfake_initialized = True
            self.status.deepfake_error = None
            self.status.deepfake_model_name = deepfake.config.model_name
            self.status.deepfake_provider = deepfake.execution_provider
        except Exception as exc:
            self.deepfake = None
            self.status.deepfake_initialized = False
            self.status.deepfake_error = str(exc)
            self.status.deepfake_provider = None

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
                "pad_state": result.pad_state,
                "pad_real_score": result.pad_real_score,
                "pad_spoof_score": result.pad_spoof_score,
                "pad_latency_ms": result.pad_latency_ms,
                "pad_provider": result.pad_provider,
            }
            for result in results
        ]

    def evaluate_pad(self, image_bytes: bytes) -> dict:
        self._require_ready()
        if self.pad is None:
            raise ModelUnavailableError(
                self.status.pad_error or "PAD model is unavailable"
            )
        image = self.engine.load_image_from_bytes(image_bytes)
        faces = self.engine.detect_faces(image)
        if len(faces) == 0:
            raise FaceRecognitionError("No face detected for PAD evaluation")
        if len(faces) > 1:
            raise FaceRecognitionError("PAD evaluation requires exactly one face")
        face = faces[0]

        threshold = settings.FACE_LIVENESS_MIN_CONFIDENCE
        if isinstance(self.pad, MiniFASNetEnsemble):
            started = time.perf_counter()
            prediction = self.pad.predict_score(image, face.bounding_box)
            inference_time_ms = (time.perf_counter() - started) * 1000.0
            real_score = prediction.bona_fide_score
            spoof_score = 1.0 - real_score
            if real_score >= threshold:
                pad_state = "bona_fide"
            elif real_score <= 0.60:
                pad_state = "attack"
            else:
                pad_state = "uncertain"

            return {
                "status": "available",
                "face_detected": True,
                "bounding_box": face.bounding_box,
                "model_name": prediction.model_name,
                "model_version": "silent-face-minifasnet",
                "provider": self.pad.execution_provider or "CPUExecutionProvider",
                "real_score": round(real_score, 4),
                "spoof_score": round(spoof_score, 4),
                "threshold": threshold,
                "pad_state": pad_state,
                "branch_scores": [round(s, 4) for s in prediction.branch_scores],
                "inference_time_ms": round(inference_time_ms, 2),
            }

        height, width = image.shape[:2]
        x1, y1, x2, y2 = face.bounding_box
        left, top = max(0, x1), max(0, y1)
        right, bottom = min(width, x2), min(height, y2)
        if right <= left or bottom <= top:
            raise FaceRecognitionError("Detected face crop is invalid")
        raw = self.pad.predict_raw(image[top:bottom, left:right])
        real_score = raw.real_score
        spoof_score = raw.spoof_score
        if real_score >= threshold:
            pad_state = "bona_fide"
        elif real_score <= 0.50:
            pad_state = "attack"
        else:
            pad_state = "uncertain"
        return {
            "status": "available",
            "face_detected": True,
            "bounding_box": face.bounding_box,
            "model_name": raw.model_name,
            "model_version": raw.model_version,
            "provider": raw.execution_provider,
            "real_score": round(real_score, 4),
            "spoof_score": round(spoof_score, 4),
            "threshold": threshold,
            "pad_state": pad_state,
            "inference_time_ms": round(raw.inference_time_ms, 2),
        }

    def evaluate_deepfake(self, image_bytes: bytes) -> dict:
        self._require_ready()
        if self.deepfake is None:
            raise ModelUnavailableError(
                self.status.deepfake_error or "Deepfake detection model is unavailable"
            )
        image = self.engine.load_image_from_bytes(image_bytes)
        faces = self.engine.detect_faces(image)
        if len(faces) == 0:
            raise FaceRecognitionError("No face detected for deepfake evaluation")
        if len(faces) > 1:
            raise FaceRecognitionError("Deepfake evaluation requires exactly one face")
        face = faces[0]
        prediction = self.deepfake.predict_image(image, face.bounding_box)
        return {
            "status": "available",
            "face_detected": True,
            "bounding_box": face.bounding_box,
            "model_name": prediction.model_name,
            "model_version": prediction.model_version,
            "provider": prediction.execution_provider,
            "authenticity_score": prediction.authenticity_score,
            "manipulation_score": prediction.manipulation_score,
            "deepfake_state": prediction.deepfake_state,
            "is_deepfake": prediction.is_deepfake,
            "threshold": self.deepfake.config.min_authenticity_threshold,
            "inference_time_ms": prediction.inference_time_ms,
        }

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

    def search(
        self,
        embedding: np.ndarray,
        top_k: int = 1,
        target_subject_id: Optional[str] = None,
    ) -> tuple[Optional[str], Optional[float]]:
        if self.gallery is None or not hasattr(self.gallery, "search"):
            return None, None
        k = max(top_k, 20 if target_subject_id else 1)
        results = self.gallery.search(self._validate_embedding(embedding), top_k=k)
        if not results:
            return None, None
        if target_subject_id:
            for subj_id, sim in results:
                if subj_id == target_subject_id:
                    return subj_id, max(-1.0, min(1.0, float(sim)))
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
        else:
            if not subject.is_active:
                subject.is_active = True
            subject.consent_granted = True
            subject.consent_timestamp = datetime.utcnow()
            await session.flush()

        digest = hashlib.sha256(embedding.tobytes()).hexdigest()
        duplicate_result = await session.execute(
            select(BiometricTemplate).where(
                BiometricTemplate.subject_id == subject.id,
                BiometricTemplate.modality == "FACE",
                BiometricTemplate.template_hash == digest,
            )
        )
        existing_template = duplicate_result.scalars().first()
        if existing_template is not None:
            # Re-register into active in-memory search galleries
            self.gallery.add_vector(embedding, subject_id)
            self.realtime_gallery.enroll(subject_id, subject_id, embedding)
            self.status.template_count = max(self.status.template_count, 1)
            self.status.subject_count = max(self.status.subject_count, 1)
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
