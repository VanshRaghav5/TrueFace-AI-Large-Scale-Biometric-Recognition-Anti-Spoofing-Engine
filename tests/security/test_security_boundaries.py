import pytest
from backend.app.core.security import validate_subject_id
from fastapi import HTTPException
from backend.app.schemas.face import FaceResult, ModalityStatus
from backend.app.schemas.voice import VoiceResult
from backend.app.schemas.authentication import DecisionOutcome
from backend.app.fusion.decision_policy import DecisionPolicy

def test_subject_id_injection_rejection():
    invalid_ids = [
        "../admin",
        "subj; DROP TABLE subjects;--",
        "<script>alert(1)</script>",
        "ab",  # too short
        "a" * 100 # too long
    ]
    for bad_id in invalid_ids:
        with pytest.raises(HTTPException):
            validate_subject_id(bad_id)

def test_valid_subject_ids():
    valid_ids = ["subj_001", "subject-alpha", "USER_1234"]
    for good_id in valid_ids:
        assert validate_subject_id(good_id) == good_id

def test_system_failure_never_results_in_allow():
    policy = DecisionPolicy()
    face_res = FaceResult(status=ModalityStatus.ERROR)
    voice_res = VoiceResult(status=ModalityStatus.ERROR)

    decision, reasons = policy.decide(
        fused_identity_score=1.0, # even with a simulated high score
        fused_authenticity_score=1.0,
        face_result=face_res,
        voice_result=voice_res,
        detected_reasons=[]
    )
    assert decision != DecisionOutcome.ALLOW
    assert decision == DecisionOutcome.ERROR

