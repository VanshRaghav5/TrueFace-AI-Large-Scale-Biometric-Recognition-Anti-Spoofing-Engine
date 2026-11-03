from typing import Optional, Tuple, List
from ..schemas.face import FaceResult
from ..schemas.voice import VoiceResult

class RiskEngine:
    """Evaluates authenticity risks across presentation attack, deepfake, and audio spoofing."""

    def __init__(
        self,
        min_face_liveness: float = 0.80,
        min_deepfake_genuineness: float = 0.80,
        min_voice_antispoof: float = 0.80
    ):
        self.min_face_liveness = min_face_liveness
        self.min_deepfake_genuineness = min_deepfake_genuineness
        self.min_voice_antispoof = min_voice_antispoof

    def evaluate_authenticity(
        self,
        face_result: Optional[FaceResult] = None,
        voice_result: Optional[VoiceResult] = None
    ) -> Tuple[float, List[str]]:
        """
        Calculates an overall authenticity score [0.0, 1.0] and identifies risk reason codes.
        A score of 1.0 indicates completely authentic/live presentation.
        """
        authenticity_scores = []
        reason_codes = []

        if face_result and face_result.status == "available":
            if face_result.liveness_score is not None:
                authenticity_scores.append(face_result.liveness_score)
                if face_result.liveness_score < self.min_face_liveness:
                    reason_codes.append("FACE_PAD_RISK")

            if face_result.deepfake_score is not None:
                authenticity_scores.append(face_result.deepfake_score)
                if face_result.deepfake_score < self.min_deepfake_genuineness:
                    reason_codes.append("FACE_MANIPULATION_RISK")

        if voice_result and voice_result.status == "available":
            if voice_result.antispoof_score is not None:
                authenticity_scores.append(voice_result.antispoof_score)
                if voice_result.antispoof_score < self.min_voice_antispoof:
                    reason_codes.append("AUDIO_SPOOF_RISK")

        if not authenticity_scores:
            # If no authenticity evidence is available, risk is high
            return 0.0, ["MODALITY_MISSING"]

        # Minimum / pessimistic authenticity rule: the weakest link determines authenticity risk
        overall_authenticity = min(authenticity_scores)
        return float(overall_authenticity), reason_codes

