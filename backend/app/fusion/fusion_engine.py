from typing import Optional, Tuple, List
from ..schemas.face import FaceResult
from ..schemas.voice import VoiceResult
from .score_calibration import ScoreCalibrator

class FusionEngine:
    """Combines identity evidence across available face and voice modalities."""

    def __init__(self, weight_face: float = 0.60, weight_voice: float = 0.40):
        total = weight_face + weight_voice
        self.weight_face = weight_face / total
        self.weight_voice = weight_voice / total

    def fuse_identity(
        self,
        face_result: Optional[FaceResult] = None,
        voice_result: Optional[VoiceResult] = None
    ) -> Tuple[float, List[str]]:
        """
        Fuses face and voice identity similarities into a single calibrated score [0.0, 1.0].
        Reports signal conflicts if one modality strongly accepts and another strongly rejects.
        """
        scores = []
        weights = []
        reason_codes = []

        face_sim = None
        voice_sim = None

        if face_result and face_result.status == "available" and face_result.identity_similarity is not None:
            face_sim = ScoreCalibrator.calibrate_face_similarity(face_result.identity_similarity)
            scores.append(face_sim)
            weights.append(self.weight_face)

        if voice_result and voice_result.status == "available" and voice_result.identity_similarity is not None:
            voice_sim = ScoreCalibrator.calibrate_voice_similarity(voice_result.identity_similarity)
            scores.append(voice_sim)
            weights.append(self.weight_voice)

        if not scores:
            return 0.0, ["MODALITY_MISSING"]

        # Conflict detection: face passes high, voice fails low, or vice versa
        if face_sim is not None and voice_sim is not None:
            if abs(face_sim - voice_sim) > 0.40:
                reason_codes.append("SIGNAL_CONFLICT")

        total_weight = sum(weights)
        fused_score = sum(s * w for s, w in zip(scores, weights)) / total_weight

        return float(fused_score), reason_codes

