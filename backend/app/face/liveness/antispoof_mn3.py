"""Model-specific ONNX adapter for Open Model Zoo anti-spoof-mn3.

This module intentionally does not download the model or perform face
detection. Callers provide a BGR face crop produced from the existing SCRFD
detection result.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, Optional

import cv2
import numpy as np

from .exceptions import (
    PadError,
    PadInferenceError,
    PadInputError,
    PadModelUnavailableError,
    PadOutputContractError,
)

OutputKind = Literal["probabilities", "logits"]


@dataclass(frozen=True)
class AntiSpoofMn3Config:
    model_path: Path
    model_version: str = "omz-anti-spoof-mn3"
    input_size: int = 128
    mean: tuple[float, float, float] = (151.2405, 119.5950, 107.8395)
    scale: tuple[float, float, float] = (63.0105, 56.4570, 55.0035)
    output_kind: OutputKind = "probabilities"
    providers: Optional[tuple[str, ...]] = None

    def __post_init__(self) -> None:
        if self.input_size != 128:
            raise ValueError("anti-spoof-mn3 requires 128x128 input")
        if len(self.mean) != 3 or len(self.scale) != 3:
            raise ValueError("mean and scale must contain three channel values")
        if any(not np.isfinite(value) for value in (*self.mean, *self.scale)):
            raise ValueError("mean and scale must be finite")
        if any(value <= 0.0 for value in self.scale):
            raise ValueError("scale values must be positive")
        if self.output_kind not in {"probabilities", "logits"}:
            raise ValueError("output_kind must be 'probabilities' or 'logits'")


@dataclass(frozen=True)
class AntiSpoofMn3RawResult:
    real_score: float
    spoof_score: float
    model_name: str
    model_version: str
    execution_provider: str
    inference_time_ms: float


def antispoof_mn3_tensor(
    face_bgr: np.ndarray,
    config: AntiSpoofMn3Config,
) -> np.ndarray:
    """Prepare a BGR crop for the converted OMZ model.

    OMZ's converted artifact uses BGR input and Model Optimizer
    mean/scale semantics: ``(pixel - mean) / scale``.
    """
    if not isinstance(face_bgr, np.ndarray) or face_bgr.size == 0:
        raise PadInputError("anti-spoof-mn3 input must be a non-empty image")
    if face_bgr.ndim != 3 or face_bgr.shape[2] != 3:
        raise PadInputError("anti-spoof-mn3 input must be a BGR color image")
    if not np.issubdtype(face_bgr.dtype, np.number):
        raise PadInputError("anti-spoof-mn3 input must contain numeric pixels")
    if not np.all(np.isfinite(face_bgr)):
        raise PadInputError("anti-spoof-mn3 input contains non-finite pixels")
    resized = cv2.resize(
        face_bgr,
        (config.input_size, config.input_size),
        interpolation=cv2.INTER_LINEAR,
    )
    normalized = (
        resized.astype(np.float32)
        - np.asarray(config.mean, dtype=np.float32).reshape(1, 1, 3)
    ) / np.asarray(config.scale, dtype=np.float32).reshape(1, 1, 3)
    tensor = normalized.transpose(2, 0, 1)[None, ...]
    if tensor.shape != (1, 3, 128, 128) or not np.all(np.isfinite(tensor)):
        raise PadInputError("anti-spoof-mn3 preprocessing produced an invalid tensor")
    return tensor.astype(np.float32, copy=False)


def _softmax_two_class(values: np.ndarray) -> np.ndarray:
    shifted = values - np.max(values, axis=1, keepdims=True)
    exponentials = np.exp(shifted)
    return exponentials / np.sum(exponentials, axis=1, keepdims=True)


class AntiSpoofMn3Engine:
    """Reusable anti-spoof-mn3 ONNX Runtime session."""

    def __init__(
        self,
        config: AntiSpoofMn3Config,
        session_factory: Optional[Callable[..., object]] = None,
    ) -> None:
        self.config = config
        self._session_factory = session_factory
        self._session: Optional[object] = None
        self._input_name: Optional[str] = None
        self._execution_provider: Optional[str] = None

    @property
    def is_loaded(self) -> bool:
        return self._session is not None

    @property
    def execution_provider(self) -> Optional[str]:
        return self._execution_provider

    def _providers(self) -> list[str]:
        if self.config.providers is not None:
            return list(self.config.providers)
        # A default session must be truthful across machines. Callers that
        # explicitly configure CUDA can opt into it after validating the
        # machine's CUDA/cuDNN runtime.
        return ["CPUExecutionProvider"]

    @staticmethod
    def _validate_metadata(session: object) -> str:
        try:
            inputs = session.get_inputs()
            outputs = session.get_outputs()
        except Exception as exc:
            raise PadModelUnavailableError(
                f"Could not inspect anti-spoof-mn3 session metadata: {exc}"
            ) from exc
        if len(inputs) != 1:
            raise PadOutputContractError("anti-spoof-mn3 requires exactly one input")
        if len(outputs) != 1:
            raise PadOutputContractError("anti-spoof-mn3 requires exactly one output")
        input_meta = inputs[0]
        if list(input_meta.shape) != [1, 3, 128, 128]:
            raise PadOutputContractError(
                f"Unexpected anti-spoof-mn3 input shape: {input_meta.shape}"
            )
        if input_meta.type not in {"tensor(float)", "float32"}:
            raise PadOutputContractError(
                f"Unexpected anti-spoof-mn3 input dtype: {input_meta.type}"
            )
        output_meta = outputs[0]
        if list(output_meta.shape) != [1, 2]:
            raise PadOutputContractError(
                f"Unexpected anti-spoof-mn3 output shape: {output_meta.shape}"
            )
        if output_meta.type not in {"tensor(float)", "float32"}:
            raise PadOutputContractError(
                f"Unexpected anti-spoof-mn3 output dtype: {output_meta.type}"
            )
        return str(input_meta.name)

    def load_model(self) -> None:
        if not self.config.model_path.is_file():
            raise PadModelUnavailableError(
                f"anti-spoof-mn3 weights were not found: {self.config.model_path}"
            )
        providers = self._providers()
        if not providers:
            raise PadModelUnavailableError(
                "No supported ONNX Runtime execution providers are available"
            )
        factory = self._session_factory
        try:
            if factory is None:
                import onnxruntime
                if "CUDAExecutionProvider" in providers:
                    session = onnxruntime.InferenceSession(
                        str(self.config.model_path),
                        providers=["CUDAExecutionProvider"],
                    )
                    if "CUDAExecutionProvider" not in session.get_providers():
                        session = onnxruntime.InferenceSession(
                            str(self.config.model_path),
                            providers=["CPUExecutionProvider"],
                        )
                else:
                    session = onnxruntime.InferenceSession(
                        str(self.config.model_path),
                        providers=providers,
                    )
            else:
                try:
                    session = factory(self.config.model_path, providers=providers)
                except TypeError:
                    session = factory(self.config.model_path)
            input_name = self._validate_metadata(session)
            active = list(session.get_providers())
        except PadError:
            raise
        except Exception as exc:
            self._session = None
            raise PadModelUnavailableError(
                f"Failed to load anti-spoof-mn3: {exc}"
            ) from exc
        self._session = session
        self._input_name = input_name
        self._execution_provider = self._select_active_provider(active)

    @staticmethod
    def _select_active_provider(providers: list[str]) -> str:
        for provider in ("CUDAExecutionProvider", "CPUExecutionProvider"):
            if provider in providers:
                return provider
        if providers:
            return providers[0]
        raise PadModelUnavailableError("Loaded session reported no providers")

    def _parse_output(self, output: np.ndarray) -> tuple[float, float]:
        values = np.asarray(output, dtype=np.float64)
        if values.shape != (1, 2):
            raise PadOutputContractError(
                f"anti-spoof-mn3 output must have shape (1, 2), got {values.shape}"
            )
        if not np.all(np.isfinite(values)):
            raise PadOutputContractError("anti-spoof-mn3 output is non-finite")
        probabilities = (
            _softmax_two_class(values)
            if self.config.output_kind == "logits"
            else values
        )
        if not np.all((0.0 <= probabilities) & (probabilities <= 1.0)):
            raise PadOutputContractError("anti-spoof-mn3 probabilities are out of range")
        if not np.isclose(float(np.sum(probabilities)), 1.0, atol=1e-3):
            raise PadOutputContractError(
                "anti-spoof-mn3 probabilities must sum to one"
            )
        return float(probabilities[0, 0]), float(probabilities[0, 1])

    def predict_raw(self, face_bgr: np.ndarray) -> AntiSpoofMn3RawResult:
        if self._session is None or self._input_name is None:
            raise PadModelUnavailableError("anti-spoof-mn3 model is not loaded")
        tensor = antispoof_mn3_tensor(face_bgr, self.config)
        started = cv2.getTickCount()
        try:
            output = self._session.run(None, {self._input_name: tensor})[0]
            real_score, spoof_score = self._parse_output(output)
        except (PadInputError, PadOutputContractError):
            raise
        except Exception as exc:
            raise PadInferenceError(
                f"anti-spoof-mn3 inference failed: {type(exc).__name__}"
            ) from exc
        elapsed_ms = (
            (cv2.getTickCount() - started)
            / cv2.getTickFrequency()
            * 1000.0
        )
        return AntiSpoofMn3RawResult(
            real_score=real_score,
            spoof_score=spoof_score,
            model_name="anti-spoof-mn3",
            model_version=self.config.model_version,
            execution_provider=self._execution_provider or "unknown",
            inference_time_ms=elapsed_ms,
        )
