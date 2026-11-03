import numpy as np

from backend.app.face.recognition.arcface_engine import DetectedFace, EmbeddingResult
from backend.realtime.config import RealtimeConfig
from backend.realtime.identity_gallery import IdentityGallery
from backend.realtime.realtime_recognition import RealtimeRecognizer


class FakeEngine:
    model_pack = "buffalo_l"
    is_gpu_active = False

    def __init__(self):
        self.calls = 0

    def detect_faces(self, _frame):
        return [
            DetectedFace(
                bounding_box=[10, 10, 50, 50],
                detection_score=0.9,
                landmarks=None,
                embedding=np.eye(512, dtype=np.float32)[0],
            )
        ]

    def extract_embedding(self, _crop):
        self.calls += 1
        embedding = np.zeros(512, dtype=np.float32)
        embedding[0] = 1.0
        return EmbeddingResult(embedding, [0, 0, 40, 40], 0.9)


def test_realtime_matching_and_refresh_cache():
    engine = FakeEngine()
    gallery = IdentityGallery(0.75)
    template = np.zeros(512, dtype=np.float32)
    template[0] = 1.0
    gallery.enroll("a", "Person A", template)
    recognizer = RealtimeRecognizer(
        engine,
        gallery,
        RealtimeConfig(recognition_refresh_interval=3, confirmation_frames=1),
    )
    frame = np.zeros((80, 80, 3), dtype=np.uint8)

    first = recognizer.process_frame(frame)
    second = recognizer.process_frame(frame)
    third = recognizer.process_frame(frame)

    assert first[0].match.display_name == "Person A"
    assert second[0].match.display_name == "Person A"
    assert third[0].match.display_name == "Person A"
    assert engine.calls == 0


def test_identity_requires_confirmation_and_clears_on_unknown():
    engine = FakeEngine()
    gallery = IdentityGallery(0.75)
    template = np.zeros(512, dtype=np.float32)
    template[0] = 1.0
    gallery.enroll("a", "Person A", template)
    recognizer = RealtimeRecognizer(
        engine,
        gallery,
        RealtimeConfig(confirmation_frames=2),
    )
    frame = np.zeros((80, 80, 3), dtype=np.uint8)

    first = recognizer.process_frame(frame, force_recognition=True)[0]
    second = recognizer.process_frame(frame, force_recognition=True)[0]

    assert first.match.display_name == "Unknown"
    assert second.match.display_name == "Person A"
