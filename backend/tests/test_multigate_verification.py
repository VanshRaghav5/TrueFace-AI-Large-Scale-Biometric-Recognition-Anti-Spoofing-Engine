import pytest
from backend.app.schemas.face import FaceResult, ModalityStatus
from backend.app.schemas.voice import VoiceResult
from backend.app.schemas.authentication import DecisionOutcome
from backend.app.fusion.decision_policy import DecisionPolicy
from backend.app.core.security import hash_security_pin, verify_security_pin


def test_security_pin_hashing_and_verification():
    pin = "482910"
    pin_hash = hash_security_pin(pin)
    assert verify_security_pin("482910", pin_hash) is True
    assert verify_security_pin("000000", pin_hash) is False
    assert verify_security_pin("", pin_hash) is False


def test_zero_trust_all_gates_pass_resolves_to_allow():
    policy = DecisionPolicy(min_identity_threshold=0.75, min_authenticity_threshold=0.80)
    face_res = FaceResult(
        status=ModalityStatus.AVAILABLE,
        identity="subject_01",
        identity_similarity=0.92,
        liveness_score=0.98,
        deepfake_score=0.96,
        reason_codes=["FACE_IDENTITY_MATCH", "FACE_PAD_BONA_FIDE", "FACE_DEEPFAKE_AUTHENTIC"],
    )
    voice_res = VoiceResult(
        status=ModalityStatus.AVAILABLE,
        identity_similarity=0.88,
        antispoof_score=0.94,
        reason_codes=["VOICE_IDENTITY_MATCH", "VOICE_ANTISPOOF_BONA_FIDE"],
    )

    decision, reasons = policy.decide(
        fused_identity_score=0.90,
        fused_authenticity_score=0.95,
        face_result=face_res,
        voice_result=voice_res,
        detected_reasons=["SECURITY_CODE_MATCH"],
    )
    assert decision == DecisionOutcome.ALLOW
    assert "FACE_IDENTITY_MATCH" in reasons


def test_zero_trust_deepfake_blocks_verification():
    policy = DecisionPolicy()
    face_res = FaceResult(
        status=ModalityStatus.AVAILABLE,
        identity="subject_01",
        identity_similarity=0.95,
        liveness_score=0.95,
        deepfake_score=0.15,
        reason_codes=["FACE_IDENTITY_MATCH", "FACE_DEEPFAKE_MANIPULATION_DETECTED"],
    )
    voice_res = VoiceResult(status=ModalityStatus.MISSING)

    decision, reasons = policy.decide(
        fused_identity_score=0.95,
        fused_authenticity_score=0.15,
        face_result=face_res,
        voice_result=voice_res,
        detected_reasons=["FACE_MANIPULATION_RISK", "SECURITY_CODE_MATCH"],
    )
    assert decision == DecisionOutcome.BLOCK
    assert "FACE_MANIPULATION_RISK" in reasons


def test_zero_trust_spoof_attack_blocks_verification():
    policy = DecisionPolicy()
    face_res = FaceResult(
        status=ModalityStatus.AVAILABLE,
        identity=None,
        identity_similarity=0.91,
        liveness_score=0.10,
        pad_state="attack",
        reason_codes=["FACE_PAD_ATTACK", "BIOMETRIC_SPOOF_REJECTED"],
    )
    voice_res = VoiceResult(status=ModalityStatus.MISSING)

    decision, reasons = policy.decide(
        fused_identity_score=0.91,
        fused_authenticity_score=0.10,
        face_result=face_res,
        voice_result=voice_res,
        detected_reasons=["FACE_PAD_ATTACK", "FACE_PAD_RISK"],
    )
    assert decision == DecisionOutcome.BLOCK


def test_zero_trust_security_pin_mismatch_blocks_verification():
    policy = DecisionPolicy()
    face_res = FaceResult(
        status=ModalityStatus.AVAILABLE,
        identity="subject_01",
        identity_similarity=0.95,
        liveness_score=0.95,
        deepfake_score=0.95,
    )
    voice_res = VoiceResult(status=ModalityStatus.MISSING)

    decision, reasons = policy.decide(
        fused_identity_score=0.95,
        fused_authenticity_score=0.95,
        face_result=face_res,
        voice_result=voice_res,
        detected_reasons=["SECURITY_CODE_MISMATCH"],
    )
    assert decision == DecisionOutcome.BLOCK
    assert "SECURITY_CODE_MISMATCH" in reasons

