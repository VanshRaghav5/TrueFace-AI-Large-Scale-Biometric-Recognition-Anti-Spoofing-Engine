import pytest
from backend.app.schemas.face import FaceResult, ModalityStatus
from backend.app.schemas.voice import VoiceResult
from backend.app.schemas.authentication import DecisionOutcome
from backend.app.fusion.decision_policy import DecisionPolicy
from backend.app.fusion.risk_engine import RiskEngine
from backend.app.fusion.fusion_engine import FusionEngine

def test_genuine_multimodal_allow():
    policy = DecisionPolicy(min_identity_threshold=0.75, min_authenticity_threshold=0.80)
    face_res = FaceResult(status=ModalityStatus.AVAILABLE, identity_similarity=0.90, liveness_score=0.95, deepfake_score=0.96)
    voice_res = VoiceResult(status=ModalityStatus.AVAILABLE, identity_similarity=0.88, antispoof_score=0.92)

    decision, reasons = policy.decide(
        fused_identity_score=0.89,
        fused_authenticity_score=0.94,
        face_result=face_res,
        voice_result=voice_res,
        detected_reasons=[]
    )
    assert decision == DecisionOutcome.ALLOW
    assert "FACE_IDENTITY_MATCH" in reasons

def test_never_silent_allow_on_presentation_attack():
    policy = DecisionPolicy()
    face_res = FaceResult(status=ModalityStatus.AVAILABLE, identity_similarity=0.95, liveness_score=0.20)
    voice_res = VoiceResult(status=ModalityStatus.AVAILABLE, identity_similarity=0.92, antispoof_score=0.90)

    decision, reasons = policy.decide(
        fused_identity_score=0.94,
        fused_authenticity_score=0.20,
        face_result=face_res,
        voice_result=voice_res,
        detected_reasons=["FACE_PAD_RISK"]
    )
    assert decision == DecisionOutcome.BLOCK
    assert "FACE_PAD_RISK" in reasons

def test_missing_both_modalities_never_allows():
    policy = DecisionPolicy()
    face_res = FaceResult(status=ModalityStatus.MISSING, face_detected=False)
    voice_res = VoiceResult(status=ModalityStatus.MISSING, speech_detected=False)

    decision, reasons = policy.decide(
        fused_identity_score=0.0,
        fused_authenticity_score=0.0,
        face_result=face_res,
        voice_result=voice_res,
        detected_reasons=["MODALITY_MISSING"]
    )
    assert decision != DecisionOutcome.ALLOW
    assert decision == DecisionOutcome.BLOCK

