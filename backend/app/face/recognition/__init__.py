"""
Face Recognition Module — TrueFace AI-X.

Provides ArcFace-based face recognition with:
- Face detection (SCRFD via InsightFace)
- Face alignment (5-point landmark-based)
- 512-d ArcFace embedding extraction
- 1:1 face verification via cosine similarity

Usage:
    from backend.app.face.recognition import ArcFaceEngine, FaceVerifier

    engine = ArcFaceEngine()
    engine.load_model()
    result = engine.extract_from_path("face.jpg")

    verifier = FaceVerifier(engine=engine)
    match = verifier.verify_images("face1.jpg", "face2.jpg")
"""

from .arcface_engine import (
    ArcFaceEngine,
    DetectedFace,
    EmbeddingResult,
    VerificationResult,
)
from .exceptions import (
    FaceNotDetectedError,
    FaceRecognitionError,
    InvalidImageError,
    ModelUnavailableError,
    MultipleFacesDetectedError,
)
from .verifier import FaceVerifier

__all__ = [
    "ArcFaceEngine",
    "DetectedFace",
    "EmbeddingResult",
    "VerificationResult",
    "FaceVerifier",
    "FaceRecognitionError",
    "FaceNotDetectedError",
    "MultipleFacesDetectedError",
    "InvalidImageError",
    "ModelUnavailableError",
]
