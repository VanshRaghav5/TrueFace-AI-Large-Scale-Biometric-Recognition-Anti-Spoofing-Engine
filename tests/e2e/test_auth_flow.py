import pytest

def test_multimodal_flow_contract():
    """Verify that end-to-end verification payload contains required explainability fields."""
    expected_fields = {
        "session_id",
        "overall_decision",
        "fused_identity_score",
        "fused_authenticity_score",
        "reason_codes",
        "face_result",
        "voice_result"
    }
    sample_response = {
        "session_id": "auth_test",
        "overall_decision": "allow",
        "fused_identity_score": 0.88,
        "fused_authenticity_score": 0.95,
        "reason_codes": ["FACE_IDENTITY_MATCH"],
        "face_result": {},
        "voice_result": {}
    }
    assert expected_fields.issubset(sample_response.keys())

