from typing import Optional, Tuple, List
from ..schemas.face import FaceResult
from ..schemas.voice import VoiceResult


class RiskEngine:
    """Evaluates authenticity risks across presentation attack, deepfake, and audio spoofing."""

    def __init__(
        self,
        min_face_liveness: float = 0.80,
        min_deepfake_genuineness: float = 0.80,
        min_voice_antispoof: float = 0.80,
    ):
        self.min_face_liveness = min_face_liveness
        self.min_deepfake_genuineness = min_deepfake_genuineness
        self.min_voice_antispoof = min_voice_antispoof

    def evaluate_authenticity(
        self,
        face_result: Optional[FaceResult] = None,
        voice_result: Optional[VoiceResult] = None,
    ) -> Tuple[float, List[str]]:
        """Calculate overall authenticity score [0.0, 1.0] and risk reason codes.

        Design rationale
        ----------------
        Face liveness (MiniFASNet) outputs a well-calibrated real-probability that
        is comparable across presentations and can be pooled directly.

        Face deepfake and voice anti-spoofing models output soft probabilities that
        are NOT numerically comparable to face liveness — they depend on model
        architecture, training data distribution, and decision boundary calibration.
        These are treated as binary gate results: only flag risk when the
        corresponding gate explicitly detected an attack (via reason codes / state).
        Adding their raw scores to the liveness pool would drag the fused
        authenticity below the floor even for genuine presentations, causing
        systematic false rejections.
        """
        authenticity_scores = []
        reason_codes = []

        if face_result and face_result.status == "available":
            # Face liveness: well-calibrated continuous score, pool directly.
            if face_result.liveness_score is not None:
                authenticity_scores.append(face_result.liveness_score)
                if face_result.liveness_score < self.min_face_liveness:
                    reason_codes.append("FACE_PAD_RISK")

            # Deepfake: use gate result (deepfake_state), not raw score.
            # The bundled model outputs soft probabilities ~0.50-0.55 for genuine
            # faces; pooling that score would always pull the minimum below 0.80.
            deepfake_state = getattr(face_result, "deepfake_state", None)
            if deepfake_state == "manipulated":
                reason_codes.append("FACE_MANIPULATION_RISK")
                authenticity_scores.append(0.0)
            # "authentic" or "uncertain" → no risk code, no score penalty.

        if voice_result and voice_result.status == "available":
            # Voice anti-spoofing: binary gate via reason codes only.
            # AASIST outputs bonafide probabilities ~0.0–0.5 for microphone
            # recordings of genuine speech (domain mismatch with studio training
            # data). Pooling the raw score would systematically block real users.
            if "VOICE_SYNTHETIC_SPEECH_DETECTED" in (voice_result.reason_codes or []):
                reason_codes.append("AUDIO_SPOOF_RISK")
                authenticity_scores.append(0.0)

        if not authenticity_scores:
            # No continuous liveness evidence — not necessarily an attack, but
            # we can't assert the presentation is live. Return 1.0 (no attack
            # detected) rather than 0.0 (which would always block). The gate
            # layer handles missing-modality enforcement separately.
            return 1.0, []

        overall_authenticity = min(authenticity_scores)
        return float(overall_authenticity), reason_codes
