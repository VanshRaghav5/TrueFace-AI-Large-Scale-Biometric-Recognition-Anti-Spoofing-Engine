import numpy as np
import pytest
from pathlib import Path

from backend.app.face.recognition.arcface_engine import (
    ArcFaceEngine,
    EmbeddingResult,
)
from backend.app.face.recognition.exceptions import (
    FaceNotDetectedError,
    InvalidImageError,
    MultipleFacesDetectedError,
)
from backend.app.face.recognition.verifier import FaceVerifier


class FakeFace:
    def __init__(self, score: float, embedding: np.ndarray):
        self.bbox = np.array([1.2, 2.4, 30.8, 40.6])
        self.det_score = score
        self.kps = np.zeros((5, 2), dtype=np.float32)
        self.normed_embedding = embedding


class FakeApp:
    def __init__(self, faces):
        self.faces = faces

    def get(self, image):
        return self.faces


def test_detection_threshold_is_validated():
    ArcFaceEngine.reset_instance()

    with pytest.raises(ValueError):
        ArcFaceEngine(det_thresh=1.1)

    with pytest.raises(ValueError):
        ArcFaceEngine(det_thresh=-0.1)


def test_detection_threshold_is_passed_to_insightface(monkeypatch):
    captured = {}

    class FakeFaceAnalysis:
        def __init__(self, **kwargs):
            captured["constructor"] = kwargs
            self.models = {}

        def prepare(self, **kwargs):
            captured["prepare"] = kwargs

    class FakeInsightFace:
        pass

    ArcFaceEngine.reset_instance()
    monkeypatch.setitem(
        __import__("sys").modules,
        "insightface",
        FakeInsightFace(),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "insightface.app",
        type("FakeAppModule", (), {"FaceAnalysis": FakeFaceAnalysis}),
    )

    engine = ArcFaceEngine(det_thresh=0.73)
    engine.load_model()

    assert captured["prepare"]["det_thresh"] == 0.73


def test_demo_reuses_each_embedding(monkeypatch):
    import backend.test_arcface as demo

    calls = []

    class FakeEngine:
        def extract_from_path(self, path):
            calls.append(path)
            return type("Embedding", (), {"embedding": np.ones(512)})()

    class FakeVerifier:
        def verify_embeddings(self, first, second):
            assert first.shape == (512,)
            assert second.shape == (512,)
            return "verified"

    first, second, result = demo.run_verification(
        FakeEngine(),
        FakeVerifier(),
        Path("first.jpg"),
        Path("second.jpg"),
    )

    assert calls == ["first.jpg", "second.jpg"]
    assert first.embedding.shape == (512,)
    assert second.embedding.shape == (512,)
    assert result == "verified"


def configured_engine(faces):
    ArcFaceEngine.reset_instance()
    engine = ArcFaceEngine()
    engine._app = FakeApp(faces)
    engine._model_loaded = True
    engine.model_pack = "buffalo_l"
    return engine


def test_invalid_image_bytes_are_rejected():
    engine = configured_engine([])

    with pytest.raises(InvalidImageError):
        engine.load_image_from_bytes(b"not-an-image")


def test_no_face_is_explicit():
    engine = configured_engine([])

    with pytest.raises(FaceNotDetectedError):
        engine.extract_embedding(np.zeros((64, 64, 3), dtype=np.uint8))


def test_multiple_faces_are_rejected_by_default():
    face = FakeFace(0.9, np.ones(512, dtype=np.float32))
    engine = configured_engine([face, face])

    with pytest.raises(MultipleFacesDetectedError):
        engine.extract_embedding(np.zeros((64, 64, 3), dtype=np.uint8))


def test_embedding_is_512d_and_normalized():
    embedding = np.arange(512, dtype=np.float32) + 1
    engine = configured_engine([FakeFace(0.9, embedding)])

    result = engine.extract_embedding(np.zeros((64, 64, 3), dtype=np.uint8))

    assert isinstance(result, EmbeddingResult)
    assert result.embedding.shape == (512,)
    assert np.all(np.isfinite(result.embedding))
    assert np.isclose(np.linalg.norm(result.embedding), 1.0)
    assert result.bounding_box == [1, 2, 30, 40]


def test_aligned_crop_diagnostics_are_opt_in(tmp_path):
    embedding = np.ones(512, dtype=np.float32)
    engine = configured_engine([FakeFace(0.9, embedding)])
    image = np.zeros((64, 64, 3), dtype=np.uint8)

    result_without_diagnostics = engine.extract_embedding(image)
    assert result_without_diagnostics.aligned_face_path is None

    engine.diagnostic_dir = tmp_path
    result_with_diagnostics = engine.extract_embedding(
        image,
        diagnostic_name="sample",
    )

    assert result_with_diagnostics.aligned_face_path is not None
    assert (tmp_path / "sample_aligned.jpg").is_file()


def test_verification_same_embedding_matches():
    embedding = np.ones(512, dtype=np.float32)
    verifier = FaceVerifier(engine=configured_engine([]), threshold=0.75)

    result = verifier.verify_embeddings(embedding, embedding)

    assert np.isclose(result.similarity, 1.0)
    assert result.is_match is True


@pytest.mark.parametrize(
    "first,second",
    [
        (np.zeros(512), np.ones(512)),
        (np.ones(511), np.ones(512)),
        (np.full(512, np.nan), np.ones(512)),
    ],
)
def test_verification_rejects_invalid_embeddings(first, second):
    verifier = FaceVerifier(engine=configured_engine([]))

    with pytest.raises(ValueError):
        verifier.verify_embeddings(first, second)
