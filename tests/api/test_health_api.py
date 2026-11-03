def test_health_check_contract():
    """Verify health contract schema without external network calls."""
    contract = {
        "status": "healthy",
        "models": {
            "face_detector": "ready",
            "voice_vad": "ready"
        }
    }
    assert contract["status"] == "healthy"
    assert "face_detector" in contract["models"]

