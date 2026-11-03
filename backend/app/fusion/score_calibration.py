import numpy as np
from typing import Optional

class ScoreCalibrator:
    """Calibrates raw distance and similarity scores to probability-like [0.0, 1.0] ranges."""

    @staticmethod
    def min_max_normalize(score: float, min_val: float, max_val: float) -> float:
        """Min-max scaling clamped between 0.0 and 1.0."""
        if max_val <= min_val:
            return 0.0
        norm = (score - min_val) / (max_val - min_val)
        return float(np.clip(norm, 0.0, 1.0))

    @staticmethod
    def sigmoid_calibrate(score: float, midpoint: float = 0.5, steepness: float = 10.0) -> float:
        """Sigmoidal logistic calibration centered at midpoint."""
        return float(1.0 / (1.0 + np.exp(-steepness * (score - midpoint))))

    @staticmethod
    def calibrate_face_similarity(raw_cosine: float) -> float:
        """ArcFace cosine similarity [-1.0, 1.0] to [0.0, 1.0]."""
        # Cosine similarity for face typically falls between 0.2 (unrelated) and 0.85 (same identity)
        return ScoreCalibrator.min_max_normalize(raw_cosine, min_val=0.0, max_val=1.0)

    @staticmethod
    def calibrate_voice_similarity(raw_cosine: float) -> float:
        """Speaker verification cosine similarity to [0.0, 1.0]."""
        return ScoreCalibrator.min_max_normalize(raw_cosine, min_val=0.0, max_val=1.0)

