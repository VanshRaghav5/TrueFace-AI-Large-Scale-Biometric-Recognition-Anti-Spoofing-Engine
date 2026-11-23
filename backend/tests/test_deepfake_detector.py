import numpy as np
import pytest

from backend.app.face.deepfake import (
    DeepfakeDetectorConfig,
    DeepfakeDetectorEngine,
    DeepfakeInputError,
    DeepfakeModelUnavailableError,
    crop_face_for_deepfake,
    deepfake_tensor,
)


def sample_image():
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    img[50:250, 50:250] = [120, 150, 180]
    return img


def test_crop_face_for_deepfake_expands_contextual_margin():
    img = sample_image()
    bbox = [100, 100, 200, 200]
    crop = crop_face_for_deepfake(img, bbox, margin=0.15, output_size=256)
    assert crop.shape == (256, 256, 3)
    assert crop.dtype == np.uint8


def test_crop_face_rejects_invalid_inputs():
    with pytest.raises(DeepfakeInputError):
        crop_face_for_deepfake(np.empty((0, 0, 3), dtype=np.uint8), [10, 10, 50, 50])
    with pytest.raises(DeepfakeInputError):
        crop_face_for_deepfake(sample_image(), [50, 50, 50, 50])
    with pytest.raises(DeepfakeInputError):
        crop_face_for_deepfake(sample_image(), [float("nan"), 0, 50, 50])


def test_deepfake_tensor_rgb_normalization(tmp_path):
    cfg = DeepfakeDetectorConfig(model_path=tmp_path / "model.onnx", input_size=256)
    face_bgr = np.full((100, 100, 3), 128, dtype=np.uint8)
    tensor = deepfake_tensor(face_bgr, cfg)
    assert tensor.shape == (1, 3, 256, 256)
    assert tensor.dtype == np.float32
    assert np.all(np.isfinite(tensor))


class FakeSession:
    def __init__(self, logits):
        self.logits = logits

    def get_inputs(self):
        class InputMeta:
            name = "input"
        return [InputMeta()]

    def run(self, _output_names, _input_feed):
        return [self.logits]


def test_deepfake_detector_prediction_authentic(tmp_path):
    model_path = tmp_path / "detector.onnx"
    model_path.write_bytes(b"dummy_bytes")
    # Logits: class 0 = Real (3.0), class 1 = Fake (-1.0) -> Authentic
    engine = DeepfakeDetectorEngine(
        DeepfakeDetectorConfig(model_path=model_path),
        session_factory=lambda p: FakeSession(np.asarray([[3.0, -1.0]], dtype=np.float32)),
    )
    engine.load_model()
    pred = engine.predict_crop(np.zeros((100, 100, 3), dtype=np.uint8))
    assert pred.authenticity_score > 0.90
    assert pred.manipulation_score < 0.10
    assert pred.deepfake_state == "authentic"
    assert pred.is_deepfake is False


def test_deepfake_detector_prediction_manipulated(tmp_path):
    model_path = tmp_path / "detector.onnx"
    model_path.write_bytes(b"dummy_bytes")
    # Logits: class 0 = Real (-2.0), class 1 = Fake (3.0) -> Deepfake manipulated
    engine = DeepfakeDetectorEngine(
        DeepfakeDetectorConfig(model_path=model_path),
        session_factory=lambda p: FakeSession(np.asarray([[-2.0, 3.0]], dtype=np.float32)),
    )
    engine.load_model()
    pred = engine.predict_crop(np.zeros((100, 100, 3), dtype=np.uint8))
    assert pred.authenticity_score < 0.10
    assert pred.manipulation_score > 0.90
    assert pred.deepfake_state == "manipulated"
    assert pred.is_deepfake is True


def test_deepfake_detector_missing_model_raises(tmp_path):
    engine = DeepfakeDetectorEngine(
        DeepfakeDetectorConfig(model_path=tmp_path / "non_existent.onnx")
    )
    with pytest.raises(DeepfakeModelUnavailableError):
        engine.load_model()

