"""
Face Processing Subsystem — TrueFace AI-X.

Modular components for face detection (SCRFD), facial alignment (norm_crop),
feature extraction & recognition (ArcFace), preprocessing, and liveness / PAD.
"""

from . import alignment, detection, liveness, preprocessing, recognition

__all__ = [
    "alignment",
    "detection",
    "liveness",
    "preprocessing",
    "recognition",
]

