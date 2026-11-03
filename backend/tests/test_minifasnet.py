import cv2
import numpy as np
import pytest

from backend.app.face.liveness import (
    MiniFASNetConfig,
    MiniFASNetEnsemble,
    PadInputError,
    PadModelUnavailableError,
    PadOrchestrator,
    PadOutputContractError,
    PadState,
)
from backend.app.face.liveness.minifasnet import (
    _softmax_three_class,
    crop_scaled_face,
    minifasnet_tensor,
)


def image():
    value = np.zeros((120, 160, 3), dtype=np.uint8)
    value[..., 0] = 10
    value[..., 1] = 20
    value[..., 2] = 30
    return value


def test_bbox_conversion_and_scaled_crops_are_80x80():
    crop_small = crop_scaled_face(image(), [50, 30, 90, 90], 2.7)
    crop_large = crop_scaled_face(image(), [50, 30, 90, 90], 4.0)
    assert crop_small.shape == (80, 80, 3)
    assert crop_large.shape == (80, 80, 3)
    assert tuple(crop_small[40, 40]) == (10, 20, 30)


def test_fractional_bbox_uses_floor_for_start_and_ceil_for_end():
    crop = crop_scaled_face(image(), [50.9, 30.9, 90.1, 90.1], 1.0)
    expected = image()[30:91, 50:91]
    expected = cv2.resize(expected, (80, 80))
    assert np.array_equal(crop, expected)


def test_crop_clips_at_image_boundaries():
    for bbox in ([0, 0, 40, 40], [120, 0, 160, 40], [0, 80, 40, 120], [120, 80, 160, 120]):
        crop = crop_scaled_face(image(), bbox, 4.0)
        assert crop.shape == (80, 80, 3)


@pytest.mark.parametrize(
    "bbox",
    [
        [1, 2, 3],
        [10, 10, 10, 20],
        [-1, 0, 20, 20],
        [0, 0, 200, 200],
        [10, 20, 10, 20],
        [float("nan"), 0, 20, 20],
    ],
)
def test_invalid_bounding_boxes_are_rejected(bbox):
    with pytest.raises(PadInputError):
        crop_scaled_face(image(), bbox, 2.7)


def test_tensor_is_bgr_nchw_float32_without_division():
    crop = np.zeros((80, 80, 3), dtype=np.uint8)
    crop[..., 0] = 10
    crop[..., 1] = 20
    crop[..., 2] = 30
    tensor = minifasnet_tensor(crop)
    assert tensor.shape == (1, 3, 80, 80)
    assert tensor.dtype == np.float32
    assert tensor[0, :, 0, 0].tolist() == [10.0, 20.0, 30.0]


def test_empty_and_invalid_crops_are_rejected():
    with pytest.raises(PadInputError):
        crop_scaled_face(np.empty((0, 0, 3), dtype=np.uint8), [0, 0, 1, 1], 2.7)
    with pytest.raises(PadInputError):
        minifasnet_tensor(np.zeros((80, 80), dtype=np.uint8))


def test_three_class_softmax_and_contract_validation():
    probabilities = _softmax_three_class(np.asarray([[0.0, 2.0, 0.0]]))
    assert probabilities.shape == (1, 3)
    assert np.isclose(float(probabilities.sum()), 1.0)
    assert probabilities[0, 1] > probabilities[0, 0]
    with pytest.raises(PadOutputContractError):
        _softmax_three_class(np.zeros((1, 2), dtype=np.float32))
    with pytest.raises(PadOutputContractError):
        _softmax_three_class(np.full((1, 3), np.nan, dtype=np.float32))


class FakeInput:
    name = "input"


class FakeSession:
    def __init__(self, output):
        self.output = output

    def get_inputs(self):
        return [FakeInput()]

    def run(self, _outputs, _inputs):
        return [self.output]


def config(tmp_path):
    return MiniFASNetConfig(tmp_path / "v2.onnx", tmp_path / "v1se.onnx")


def test_ensemble_fuses_two_branch_bona_fide_scores(tmp_path):
    paths = [tmp_path / "v2.onnx", tmp_path / "v1se.onnx"]
    for path in paths:
        path.write_bytes(b"test-only-placeholder")
    engine = MiniFASNetEnsemble(
        config(tmp_path),
        session_factory=lambda path: FakeSession(
            np.asarray([[0.0, 2.0 if path == paths[0] else 1.0, 0.0]])
        ),
    )
    engine.load_model()
    result = engine.predict_score(image(), [50, 30, 90, 90])
    assert len(result.branch_scores) == 2
    assert result.branch_scores[0] > result.branch_scores[1]
    assert 0.0 < result.bona_fide_score < 1.0


def test_ensemble_requires_both_models(tmp_path):
    engine = MiniFASNetEnsemble(config(tmp_path))
    with pytest.raises(PadModelUnavailableError):
        engine.load_model()


def test_ensemble_reports_one_unavailable_branch(tmp_path):
    paths = [tmp_path / "v2.onnx", tmp_path / "v1se.onnx"]
    for path in paths:
        path.write_bytes(b"test-only-placeholder")

    def factory(path):
        if path == paths[1]:
            raise RuntimeError("branch unavailable")
        return FakeSession(np.zeros((1, 3)))

    engine = MiniFASNetEnsemble(config(tmp_path), session_factory=factory)
    with pytest.raises(PadModelUnavailableError):
        engine.load_model()


def test_ensemble_rejects_missing_branch_output(tmp_path):
    paths = [tmp_path / "v2.onnx", tmp_path / "v1se.onnx"]
    for path in paths:
        path.write_bytes(b"test-only-placeholder")
    engine = MiniFASNetEnsemble(
        config(tmp_path),
        session_factory=lambda _path: FakeSession(np.zeros((1, 2))),
    )
    engine.load_model()
    with pytest.raises(PadOutputContractError):
        engine.predict_score(image(), [50, 30, 90, 90])


def test_orchestrator_rejects_invalid_score_and_classifies_uncertain():
    orchestrator = PadOrchestrator("minifasnet")
    invalid = orchestrator.classify_score(np.nan, 0.5, 0.05)
    assert invalid.state is PadState.ERROR
    uncertain = orchestrator.classify_score(0.5, 0.5, 0.05)
    assert uncertain.state is PadState.UNCERTAIN
