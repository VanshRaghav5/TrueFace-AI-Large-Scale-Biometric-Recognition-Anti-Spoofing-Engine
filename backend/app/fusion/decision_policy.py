from typing import List, Tuple
from ..schemas.authentication import DecisionOutcome
from ..schemas.face import FaceResult, ModalityStatus
from ..schemas.voice import VoiceResult

class DecisionPolicy:
    """
    Enforces deterministic decision rules.
    Invariant: No error, quality failure, timeout, missing modality, or attack risk can resolve to Allow.
    """

    def __init__(
        self,
        min_identity_threshold: float = 0.75,
        min_authenticity_threshold: float = 0.80,
        step_up_identity_band: float = 0.65
    ):
        self.min_identity_threshold = min_identity_threshold
        self.min_authenticity_threshold = min_authenticity_threshold
        self.step_up_identity_band = step_up_identity_band

    def decide(
        self,
        fused_identity_score: float,
        fused_authenticity_score: float,
        face_result: FaceResult,
        voice_result: VoiceResult,
        detected_reasons: List[str]
    ) -> Tuple[DecisionOutcome, List[str]]:
        reasons = list(detected_reasons)

        # 1. Check for system / pipeline error states
        for res, prefix in [(face_result, "FACE"), (voice_result, "VOICE")]:
            if res.status == ModalityStatus.TIMEOUT:
                reasons.append("MODEL_TIMEOUT")
                return DecisionOutcome.ERROR, list(set(reasons))
            elif res.status == ModalityStatus.MODEL_UNAVAILABLE:
                reasons.append("MODEL_UNAVAILABLE")
                return DecisionOutcome.ERROR, list(set(reasons))
            elif res.status in (ModalityStatus.ERROR, ModalityStatus.INVALID):
                return DecisionOutcome.ERROR, list(set(reasons))
            elif res.status == ModalityStatus.LOW_QUALITY:
                reasons.append(f"{prefix}_QUALITY_LOW")

        # 2. Check for missing modalities
        if face_result.status == ModalityStatus.MISSING and voice_result.status == ModalityStatus.MISSING:
            reasons.append("MODALITY_MISSING")
            return DecisionOutcome.BLOCK, list(set(reasons))

        # 3. Check authenticity / spoofing risk (presentation attack or synthetic audio)
        authenticity_risks = {"FACE_PAD_RISK", "FACE_MANIPULATION_RISK", "AUDIO_SPOOF_RISK"}
        if any(r in authenticity_risks for r in reasons) or fused_authenticity_score < self.min_authenticity_threshold:
            return DecisionOutcome.BLOCK, list(set(reasons))

        # 4. Check for modality signal conflict
        if "SIGNAL_CONFLICT" in reasons:
            return DecisionOutcome.STEP_UP, list(set(reasons))

        # 5. Check quality failures
        if any("QUALITY_LOW" in r for r in reasons):
            return DecisionOutcome.STEP_UP, list(set(reasons))

        # 6. Evaluate identity match
        if fused_identity_score >= self.min_identity_threshold:
            if face_result.status == ModalityStatus.AVAILABLE:
                reasons.append("FACE_IDENTITY_MATCH")
            if voice_result.status == ModalityStatus.AVAILABLE:
                reasons.append("VOICE_IDENTITY_MATCH")
            return DecisionOutcome.ALLOW, list(set(reasons))
        elif fused_identity_score >= self.step_up_identity_band:
            reasons.append("FACE_IDENTITY_MISMATCH")
            return DecisionOutcome.STEP_UP, list(set(reasons))
        else:
            reasons.append("FACE_IDENTITY_MISMATCH")
            return DecisionOutcome.BLOCK, list(set(reasons))

