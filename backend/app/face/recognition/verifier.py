"""
Face Verifier for TrueFace AI-X.

Provides 1:1 face verification by comparing two face images using
ArcFace embeddings and cosine similarity.

The similarity threshold is configurable and defaults to the value
from the project configuration (FACE_MATCH_THRESHOLD). This threshold
is a placeholder — proper calibration based on validation data is
required before production use.
"""

import logging
import time
from typing import Optional

import numpy as np

from ...core.config import settings
from .arcface_engine import (
    ArcFaceEngine,
    EmbeddingResult,
    VerificationResult,
)
from .exceptions import (
    FaceRecognitionError,
)

logger = logging.getLogger(__name__)


class FaceVerifier:
    """
    1:1 Face verification using ArcFace embeddings.

    Compares two face images (or precomputed embeddings) using cosine
    similarity and a configurable threshold.

    Usage:
        verifier = FaceVerifier()
        result = verifier.verify_images("face1.jpg", "face2.jpg")

    Note:
        - ArcFace similarity is an identity-match score ONLY.
        - It does NOT indicate liveness, deepfake detection, or authenticity.
        - A high similarity score means the faces likely belong to the same person,
          but does NOT guarantee the images are of a real, live person.
    """

    def __init__(
        self,
        engine: Optional[ArcFaceEngine] = None,
        threshold: Optional[float] = None,
    ):
        """
        Initialize the verifier.

        Args:
            engine: ArcFaceEngine instance. If None, uses the singleton.
            threshold: Similarity threshold for match decisions.
                       Defaults to settings.FACE_MATCH_THRESHOLD (0.75).
                       This is a placeholder — calibration pending.
        """
        self._engine = engine or ArcFaceEngine()
        self._threshold = (
            threshold if threshold is not None else settings.FACE_MATCH_THRESHOLD
        )
        self._validate_threshold(self._threshold)

    @staticmethod
    def _validate_threshold(value: float) -> None:
        if not np.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {value}")

    @staticmethod
    def _validate_embedding(embedding: np.ndarray, name: str) -> np.ndarray:
        vector = np.asarray(embedding, dtype=np.float64).flatten()
        if vector.shape != (512,):
            raise ValueError(
                f"{name} must contain exactly 512 values, got {vector.size}"
            )
        if not np.all(np.isfinite(vector)):
            raise ValueError(f"{name} contains non-finite values")
        norm = np.linalg.norm(vector)
        if norm <= np.finfo(np.float64).eps:
            raise ValueError(f"{name} must have a non-zero norm")
        return vector / norm

    @property
    def threshold(self) -> float:
        """Current verification threshold."""
        return self._threshold

    @threshold.setter
    def threshold(self, value: float) -> None:
        """Set a new verification threshold."""
        self._validate_threshold(value)
        self._threshold = value

    @staticmethod
    def cosine_similarity(
        embedding_1: np.ndarray,
        embedding_2: np.ndarray,
    ) -> float:
        """
        Compute cosine similarity between two L2-normalized embeddings.

        For L2-normalized vectors, cosine similarity equals the dot product.

        Args:
            embedding_1: First 512-d L2-normalized embedding.
            embedding_2: Second 512-d L2-normalized embedding.

        Returns:
            Cosine similarity in range [-1.0, 1.0].
            Typically [0.0, 1.0] for face embeddings.
        """
        e1 = FaceVerifier._validate_embedding(embedding_1, "embedding_1")
        e2 = FaceVerifier._validate_embedding(embedding_2, "embedding_2")

        similarity = float(np.dot(e1, e2))

        # Clamp to valid range (handles floating-point precision issues)
        similarity = max(-1.0, min(1.0, similarity))

        return similarity

    def verify_embeddings(
        self,
        embedding_1: np.ndarray,
        embedding_2: np.ndarray,
        threshold: Optional[float] = None,
    ) -> VerificationResult:
        """
        Compare two precomputed embeddings.

        Args:
            embedding_1: First 512-d embedding.
            embedding_2: Second 512-d embedding.
            threshold: Override threshold for this comparison.

        Returns:
            VerificationResult with similarity score and match decision.
        """
        thresh = threshold if threshold is not None else self._threshold
        self._validate_threshold(thresh)

        first = self._validate_embedding(embedding_1, "embedding_1")
        second = self._validate_embedding(embedding_2, "embedding_2")
        similarity = self.cosine_similarity(first, second)
        is_match = similarity >= thresh

        return VerificationResult(
            similarity=round(similarity, 6),
            threshold=thresh,
            is_match=is_match,
            model_name=f"arcface_{self._engine.model_pack}",
        )

    def verify_images(
        self,
        image_path_1: str,
        image_path_2: str,
        threshold: Optional[float] = None,
        allow_multiple: bool = False,
    ) -> VerificationResult:
        """
        Perform 1:1 face verification on two image files.

        Args:
            image_path_1: Path to the first face image.
            image_path_2: Path to the second face image.
            threshold: Override threshold for this comparison.
            allow_multiple: If True, use highest-confidence face when multiple detected.

        Returns:
            VerificationResult with similarity, threshold, and match decision.

        Raises:
            FaceRecognitionError: If either image cannot be processed.
        """
        if not self._engine.is_loaded:
            self._engine.load_model()

        start_time = time.perf_counter()

        # Extract embeddings from both images
        result_1 = self._engine.extract_from_path(
            image_path_1, allow_multiple=allow_multiple
        )
        result_2 = self._engine.extract_from_path(
            image_path_2, allow_multiple=allow_multiple
        )

        # Compute similarity
        thresh = threshold if threshold is not None else self._threshold
        self._validate_threshold(thresh)
        similarity = self.cosine_similarity(result_1.embedding, result_2.embedding)
        is_match = similarity >= thresh

        total_ms = (time.perf_counter() - start_time) * 1000

        result = VerificationResult(
            similarity=round(similarity, 6),
            threshold=thresh,
            is_match=is_match,
            model_name=f"arcface_{self._engine.model_pack}",
            embedding_1_time_ms=result_1.inference_time_ms,
            embedding_2_time_ms=result_2.inference_time_ms,
            total_time_ms=round(total_ms, 2),
        )

        logger.info(
            f"Verification complete: similarity={result.similarity:.4f}, "
            f"threshold={thresh}, match={is_match}, "
            f"time={result.total_time_ms:.1f}ms"
        )

        return result

    def verify_image_arrays(
        self,
        image_1: np.ndarray,
        image_2: np.ndarray,
        threshold: Optional[float] = None,
        allow_multiple: bool = False,
    ) -> VerificationResult:
        """
        Perform 1:1 face verification on two in-memory images.

        Args:
            image_1: First BGR image as numpy array.
            image_2: Second BGR image as numpy array.
            threshold: Override threshold for this comparison.
            allow_multiple: If True, use highest-confidence face when multiple detected.

        Returns:
            VerificationResult with similarity, threshold, and match decision.

        Raises:
            FaceRecognitionError: If either image cannot be processed.
        """
        if not self._engine.is_loaded:
            self._engine.load_model()

        start_time = time.perf_counter()

        result_1 = self._engine.extract_embedding(
            image_1, allow_multiple=allow_multiple
        )
        result_2 = self._engine.extract_embedding(
            image_2, allow_multiple=allow_multiple
        )

        thresh = threshold if threshold is not None else self._threshold
        self._validate_threshold(thresh)
        similarity = self.cosine_similarity(result_1.embedding, result_2.embedding)
        is_match = similarity >= thresh

        total_ms = (time.perf_counter() - start_time) * 1000

        return VerificationResult(
            similarity=round(similarity, 6),
            threshold=thresh,
            is_match=is_match,
            model_name=f"arcface_{self._engine.model_pack}",
            embedding_1_time_ms=result_1.inference_time_ms,
            embedding_2_time_ms=result_2.inference_time_ms,
            total_time_ms=round(total_ms, 2),
        )
