import numpy as np
import pytest

from backend.app.face.liveness import (
    OnnxPadEngine,
    PadConfig,
    PadInputError,
    PadModelUnavailableError,
    PadOrchestrator,
    PadState,
)


def test_missing_weights_are_unavailable(tmp_path):
    engine = OnnxPadEngine(PadConfig(model_path=tmp_path / "missing.onnx"))

    with pytest.raises(PadModelUnavailableError):
        engine.load_model()

    result = engine.unavailable_result()
    assert result.state is PadState.UNAVAILABLE
    assert result.is_bona_fide is False


def test_pad_requires_exactly_one_face():
    engine = OnnxPadEngine()

    with pytest.raises(PadInputError):
        engine.evaluate_faces([])
    with pytest.raises(PadInputError):
        engine.evaluate_faces(
            [
                np.zeros((112, 112, 3), dtype=np.uint8),
                np.zeros((112, 112, 3), dtype=np.uint8),
            ]
        )


def test_pad_requires_model_before_processing():
    engine = OnnxPadEngine()

    with pytest.raises(PadModelUnavailableError):
        engine.predict(np.zeros((112, 112), dtype=np.uint8))


def test_orchestrator_converts_input_failure_to_error():
    result = PadOrchestrator("test").evaluate(
        lambda: (_ for _ in ()).throw(PadInputError("invalid"))
    )
    assert result.state is PadState.ERROR
    assert result.is_bona_fide is False


@pytest.mark.parametrize("error", [RuntimeError("runtime"), ValueError("unexpected")])
def test_orchestrator_converts_unexpected_failures_to_error(error):
    result = PadOrchestrator("test").evaluate(
        lambda: (_ for _ in ()).throw(error)
    )
    assert result.state is PadState.ERROR
    assert result.reason_code == f"PAD_UNEXPECTED_ERROR:{type(error).__name__}"
    assert result.is_bona_fide is False


class FakeInput:
    name = "input"


class FakeSession:
    def __init__(self, output):
        self.output = output

    def get_inputs(self):
        return [FakeInput()]

    def run(self, _outputs, _inputs):
        return [self.output]


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (np.asarray([0.9], dtype=np.float32), PadState.BONA_FIDE),
        (np.asarray([0.1], dtype=np.float32), PadState.ATTACK),
        (np.asarray([0.5], dtype=np.float32), PadState.UNCERTAIN),
    ],
)
def test_pad_result_states_are_explicit(score, expected):
    engine = OnnxPadEngine(PadConfig(threshold=0.5, uncertainty_margin=0.05))
    engine._session = FakeSession(score)

    result = engine.predict(np.zeros((112, 112, 3), dtype=np.uint8))

    assert result.state is expected
    assert result.is_bona_fide is (expected is PadState.BONA_FIDE)
