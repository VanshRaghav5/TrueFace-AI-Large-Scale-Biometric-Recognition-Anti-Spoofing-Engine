import numpy as np
import pytest

from backend.app.face.liveness import PadState
from backend.app.face.liveness.antispoof_mn3 import AntiSpoofMn3RawResult
from backend.app.face.recognition.arcface_engine import DetectedFace
from backend.realtime.config import RealtimeConfig
from backend.realtime.identity_gallery import IdentityGallery
from backend.realtime.realtime_recognition import RealtimeRecognizer


EMBEDDING = np.eye(512, dtype=np.float32)[0]


class FakeEngine:
    is_gpu_active = False
    active_providers = ["CPUExecutionProvider"]

    def __init__(self, faces=None):
        self.faces = faces or [
            DetectedFace([10, 10, 50, 50], 0.9, embedding=EMBEDDING)
        ]

    def detect_faces(self, _frame):
        return list(self.faces)


class FakePad:
    execution_provider = "CPUExecutionProvider"

    def __init__(self, real_score=0.9, failure=None):
        self.real_score = real_score
        self.failure = failure
        self.calls = 0

    def predict_raw(self, face_bgr):
        self.calls += 1
        assert face_bgr.ndim == 3
        if self.failure is not None:
            raise self.failure
        return AntiSpoofMn3RawResult(
            self.real_score,
            1.0 - self.real_score,
            "anti-spoof-mn3",
            "test-double",
            self.execution_provider,
            0.1,
        )


def build_recognizer(engine, pad_adapter=None, threshold=None):
    gallery = IdentityGallery(0.75)
    gallery.enroll("person-a", "Person A", EMBEDDING)
    return RealtimeRecognizer(
        engine,
        gallery,
        RealtimeConfig(confirmation_frames=1, track_timeout_frames=2),
        pad_adapter=pad_adapter,
        pad_threshold=threshold,
    )


def test_known_identity_with_pad_unavailable():
    result = build_recognizer(FakeEngine()).process_frame(
        np.zeros((80, 80, 3), dtype=np.uint8)
    )[0]
    assert result.match.display_name == "Person A"
    assert result.identity_state == "known"
    assert result.pad_state == PadState.UNAVAILABLE.value
    assert result.pad_real_score is None


def test_unknown_identity_with_pad_unavailable():
    engine = FakeEngine([DetectedFace([10, 10, 50, 50], 0.9, embedding=-EMBEDDING)])
    result = build_recognizer(engine).process_frame(
        np.zeros((80, 80, 3), dtype=np.uint8)
    )[0]
    assert result.match.display_name == "Unknown"
    assert result.identity_state == "unknown"
    assert result.pad_state == PadState.UNAVAILABLE.value


def test_known_identity_with_controlled_bona_fide_pad():
    result = build_recognizer(
        FakeEngine(), FakePad(real_score=0.9), threshold=0.75
    ).process_frame(np.zeros((80, 80, 3), dtype=np.uint8))[0]
    assert result.match.display_name == "Person A"
    assert result.pad_state == PadState.BONA_FIDE.value
    assert result.pad_real_score == 0.9
    assert result.pad_spoof_score == pytest.approx(0.1)


def test_known_identity_with_controlled_attack_pad():
    result = build_recognizer(
        FakeEngine(), FakePad(real_score=0.1), threshold=0.75
    ).process_frame(np.zeros((80, 80, 3), dtype=np.uint8))[0]
    assert result.match.display_name == "Person A"
    assert result.pad_state == PadState.ATTACK.value


def test_unset_pad_threshold_is_uncertain_with_scores_only():
    result = build_recognizer(
        FakeEngine(), FakePad(real_score=0.9), threshold=None
    ).process_frame(np.zeros((80, 80, 3), dtype=np.uint8))[0]
    assert result.pad_state == PadState.UNCERTAIN.value
    assert result.pad_real_score == 0.9


def test_invalid_controlled_pad_scores_are_errors_and_not_displayed():
    result = build_recognizer(
        FakeEngine(), FakePad(real_score=float("nan")), threshold=None
    ).process_frame(np.zeros((80, 80, 3), dtype=np.uint8))[0]
    assert result.pad_state == PadState.ERROR.value
    assert result.pad_real_score is None
    assert result.pad_spoof_score is None


def test_unknown_identity_can_have_bona_fide_pad():
    engine = FakeEngine([DetectedFace([10, 10, 50, 50], 0.9, embedding=-EMBEDDING)])
    result = build_recognizer(
        engine, FakePad(real_score=0.9), threshold=0.75
    ).process_frame(np.zeros((80, 80, 3), dtype=np.uint8))[0]
    assert result.match.display_name == "Unknown"
    assert result.pad_state == PadState.BONA_FIDE.value


def test_pad_failure_is_explicit():
    result = build_recognizer(
        FakeEngine(), FakePad(failure=RuntimeError("controlled failure")), threshold=0.75
    ).process_frame(np.zeros((80, 80, 3), dtype=np.uint8))[0]
    assert result.pad_state == PadState.ERROR.value
    assert result.pad_real_score is None


def test_identity_failure_is_independent_from_pad():
    face = DetectedFace([10, 10, 50, 50], 0.9, embedding=None)
    result = build_recognizer(
        FakeEngine([face]), FakePad(real_score=0.9), threshold=0.75
    ).process_frame(np.zeros((80, 80, 3), dtype=np.uint8))[0]
    assert result.identity_state == "error"
    assert result.match.display_name == "Unknown"
    assert result.pad_state == PadState.BONA_FIDE.value


def test_multiple_faces_have_independent_results():
    faces = [
        DetectedFace([2, 2, 30, 30], 0.9, embedding=EMBEDDING),
        DetectedFace([40, 40, 78, 78], 0.8, embedding=-EMBEDDING),
    ]
    results = build_recognizer(
        FakeEngine(faces), FakePad(real_score=0.9), threshold=0.75
    ).process_frame(np.zeros((80, 80, 3), dtype=np.uint8))
    assert [result.match.display_name for result in results] == [
        "Person A",
        "Unknown",
    ]
    assert [result.track_id for result in results] == [1, 2]
    assert all(result.pad_state == PadState.BONA_FIDE.value for result in results)


def test_track_expiration_removes_stale_track():
    engine = FakeEngine()
    recognizer = build_recognizer(engine)
    frame = np.zeros((80, 80, 3), dtype=np.uint8)
    recognizer.process_frame(frame)
    engine.faces = []
    recognizer.process_frame(frame)
    recognizer.process_frame(frame)
    recognizer.process_frame(frame)
    assert recognizer.tracker.active_track_count == 0


def test_missing_pad_adapter_is_unavailable_without_fake_scores():
    result = build_recognizer(FakeEngine(), pad_adapter=None, threshold=0.75).process_frame(
        np.zeros((80, 80, 3), dtype=np.uint8)
    )[0]
    assert result.pad_state == PadState.UNAVAILABLE.value
    assert result.pad_real_score is None
    assert result.pad_spoof_score is None
