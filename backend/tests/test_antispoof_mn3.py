from pathlib import Path

import numpy as np
import pytest

from backend.app.face.liveness import (
    AntiSpoofMn3Config,
    AntiSpoofMn3Engine,
    PadInferenceError,
    PadInputError,
    PadModelUnavailableError,
    PadOutputContractError,
    PadOrchestrator,
    PadState,
    antispoof_mn3_tensor,
)


def config(tmp_path: Path, **kwargs) -> AntiSpoofMn3Config:
    path = tmp_path / "anti-spoof-mn3.onnx"
    path.write_bytes(b"mocked-session-only")
    return AntiSpoofMn3Config(model_path=path, **kwargs)


def face() -> np.ndarray:
    image = np.zeros((64, 96, 3), dtype=np.uint8)
    image[..., 0] = 10
    image[..., 1] = 20
    image[..., 2] = 30
    return image


class Metadata:
    def __init__(self, name, shape, dtype):
        self.name = name
        self.shape = shape
        self.type = dtype


class FakeSession:
    def __init__(self, output, providers=None, input_shape=None, output_shape=None):
        self.output = output
        self.providers = providers or ["CPUExecutionProvider"]
        self.input_shape = input_shape or [1, 3, 128, 128]
        self.output_shape = output_shape or [1, 2]
        self.last_inputs = None

    def get_inputs(self):
        return [Metadata("actual_input_1", self.input_shape, "tensor(float)")]

    def get_outputs(self):
        return [Metadata("output1", self.output_shape, "tensor(float)")]

    def get_providers(self):
        return self.providers

    def run(self, _outputs, inputs):
        self.last_inputs = inputs
        return [self.output]


def test_preprocessing_preserves_bgr_and_applies_mean_scale():
    tensor = antispoof_mn3_tensor(
        face(), AntiSpoofMn3Config(model_path=Path("mock.onnx"))
    )
    assert tensor.shape == (1, 3, 128, 128)
    assert tensor.dtype == np.float32
    assert np.allclose(tensor[0, :, 64, 64], [
        (10.0 - 151.2405) / 63.0105,
        (20.0 - 119.5950) / 56.4570,
        (30.0 - 107.8395) / 55.0035,
    ], atol=1e-5)


@pytest.mark.parametrize(
    "value",
    [
        np.empty((0, 0, 3), dtype=np.uint8),
        np.zeros((128, 128), dtype=np.uint8),
        np.full((32, 32, 4), 1, dtype=np.uint8),
        np.full((32, 32, 3), np.nan, dtype=np.float32),
    ],
)
def test_preprocessing_rejects_invalid_input(value):
    with pytest.raises(PadInputError):
        antispoof_mn3_tensor(
            value, AntiSpoofMn3Config(model_path=Path("mock.onnx"))
        )


def test_missing_model_is_unavailable(tmp_path):
    engine = AntiSpoofMn3Engine(
        AntiSpoofMn3Config(tmp_path / "missing.onnx")
    )
    with pytest.raises(PadModelUnavailableError):
        engine.load_model()


def test_metadata_and_provider_reporting(tmp_path):
    session = FakeSession(
        np.asarray([[0.8, 0.2]], dtype=np.float32),
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
    )
    engine = AntiSpoofMn3Engine(
        config(tmp_path),
        session_factory=lambda _path, **_kwargs: session,
    )
    engine.load_model()
    result = engine.predict_raw(face())
    assert result.real_score == pytest.approx(0.8)
    assert result.spoof_score == pytest.approx(0.2)
    assert result.execution_provider == "CUDAExecutionProvider"
    assert result.inference_time_ms >= 0.0
    assert session.last_inputs["actual_input_1"].shape == (1, 3, 128, 128)


@pytest.mark.parametrize(
    ("input_shape", "output_shape"),
    [([1, 3, 64, 64], [1, 2]), ([1, 3, 128, 128], [1, 3])],
)
def test_metadata_mismatch_is_rejected(tmp_path, input_shape, output_shape):
    session = FakeSession(
        np.zeros((1, 2), dtype=np.float32),
        input_shape=input_shape,
        output_shape=output_shape,
    )
    engine = AntiSpoofMn3Engine(
        config(tmp_path),
        session_factory=lambda _path, **_kwargs: session,
    )
    with pytest.raises(PadOutputContractError):
        engine.load_model()


@pytest.mark.parametrize(
    "output",
    [
        np.asarray([[0.5]], dtype=np.float32),
        np.asarray([[np.nan, 0.0]], dtype=np.float32),
        np.asarray([[np.inf, 0.0]], dtype=np.float32),
        np.asarray([[0.4, 0.4]], dtype=np.float32),
    ],
)
def test_invalid_outputs_are_rejected(tmp_path, output):
    session = FakeSession(output)
    engine = AntiSpoofMn3Engine(
        config(tmp_path),
        session_factory=lambda _path, **_kwargs: session,
    )
    engine.load_model()
    with pytest.raises(PadOutputContractError):
        engine.predict_raw(face())


def test_logits_are_softmaxed_only_when_configured(tmp_path):
    session = FakeSession(np.asarray([[2.0, 0.0]], dtype=np.float32))
    engine = AntiSpoofMn3Engine(
        config(tmp_path, output_kind="logits"),
        session_factory=lambda _path, **_kwargs: session,
    )
    engine.load_model()
    result = engine.predict_raw(face())
    assert result.real_score > result.spoof_score
    assert result.real_score + result.spoof_score == pytest.approx(1.0)


def test_runtime_failure_is_explicit_and_never_bona_fide(tmp_path):
    class FailingSession(FakeSession):
        def run(self, *_args):
            raise RuntimeError("controlled test failure")

    session = FailingSession(np.zeros((1, 2), dtype=np.float32))
    engine = AntiSpoofMn3Engine(
        config(tmp_path),
        session_factory=lambda _path, **_kwargs: session,
    )
    engine.load_model()
    with pytest.raises(PadInferenceError):
        engine.predict_raw(face())

    result = PadOrchestrator("anti-spoof-mn3").evaluate(
        lambda: (_ for _ in ()).throw(PadInferenceError("failure"))
    )
    assert result.state is PadState.ERROR
    assert result.is_bona_fide is False


def test_cpu_provider_selection(tmp_path):
    session = FakeSession(
        np.asarray([[0.8, 0.2]], dtype=np.float32),
        providers=["CPUExecutionProvider"],
    )
    engine = AntiSpoofMn3Engine(
        config(tmp_path, providers=("CPUExecutionProvider",)),
        session_factory=lambda _path, **_kwargs: session,
    )
    engine.load_model()
    assert engine.execution_provider == "CPUExecutionProvider"
