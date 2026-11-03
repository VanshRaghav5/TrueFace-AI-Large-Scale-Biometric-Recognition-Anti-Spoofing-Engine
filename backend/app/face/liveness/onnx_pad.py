"""Explicit-state ONNX face PAD adapter.

The adapter intentionally does not download weights or infer a model contract
from an arbitrary ONNX file. The configured model must output either a scalar
or a two-class vector whose bona-fide probability is documented by the caller.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import cv2
import numpy as np

from .config import PadConfig
from .exceptions import (
    PadInferenceError,
    PadInputError,
    PadModelUnavailableError,
    PadOutputContractError,
)
from .types import PadResult, PadState


class OnnxPadEngine:
    """Run a configured, model-specific ONNX PAD model on an aligned BGR face."""

    def __init__(self, config: PadConfig | None = None) -> None:
        self.config = config or PadConfig()
        self._session = None

    @property
    def is_loaded(self) -> bool:
        return self._session is not None

    def load_model(self) -> None:
        if not self.config.model_path.is_file():
            raise PadModelUnavailableError(
                f"PAD model weights were not found: {self.config.model_path}"
            )
        try:
            import onnxruntime

            self._session = onnxruntime.InferenceSession(
                str(self.config.model_path),
                providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
            )
        except Exception as exc:
            raise PadModelUnavailableError(
                f"Failed to load PAD model '{self.config.model_path}': {exc}"
            ) from exc

    def unavailable_result(self, reason_code: str = "PAD_MODEL_UNAVAILABLE") -> PadResult:
        return PadResult(
            state=PadState.UNAVAILABLE,
            bona_fide_score=None,
            threshold=self.config.threshold,
            reason_code=reason_code,
            model_name=self.config.model_name,
            input_size=self.config.input_size,
        )

    def _preprocess(self, aligned_face_bgr: np.ndarray) -> np.ndarray:
        if not isinstance(aligned_face_bgr, np.ndarray) or aligned_face_bgr.size == 0:
            raise PadInputError("PAD input must be a non-empty image array")
        if aligned_face_bgr.ndim != 3 or aligned_face_bgr.shape[2] != 3:
            raise PadInputError("PAD input must be a BGR color image")
        resized = cv2.resize(
            aligned_face_bgr,
            (self.config.input_size, self.config.input_size),
            interpolation=cv2.INTER_LINEAR,
        )
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        return (rgb.astype(np.float32) / 255.0).transpose(2, 0, 1)[None, ...]

    @staticmethod
    def _bona_fide_score(output: np.ndarray) -> float:
        values = np.asarray(output, dtype=np.float32).reshape(-1)
        if values.size == 1:
            score = float(values[0])
        elif values.size == 2:
            probabilities = np.exp(values - np.max(values))
            probabilities /= np.sum(probabilities)
            score = float(probabilities[1])
        else:
            raise PadOutputContractError(
                "PAD model output must be a scalar or two-class vector"
            )
        if not np.isfinite(score) or not 0.0 <= score <= 1.0:
            raise PadOutputContractError("PAD bona-fide score is invalid")
        return score

    def predict(self, aligned_face_bgr: np.ndarray) -> PadResult:
        if self._session is None:
            raise PadModelUnavailableError("PAD model is not loaded")
        tensor = self._preprocess(aligned_face_bgr)
        try:
            input_name = self._session.get_inputs()[0].name
            output = self._session.run(None, {input_name: tensor})[0]
            score = self._bona_fide_score(output)
        except (PadInputError, PadInferenceError):
            raise
        except Exception as exc:
            raise PadInferenceError(f"PAD inference failed: {exc}") from exc

        margin = self.config.uncertainty_margin
        if abs(score - self.config.threshold) < margin:
            state = PadState.UNCERTAIN
            reason = "PAD_SCORE_UNCERTAIN"
        elif score >= self.config.threshold:
            state = PadState.BONA_FIDE
            reason = "PAD_BONA_FIDE"
        else:
            state = PadState.ATTACK
            reason = "PAD_ATTACK_RISK"
        return PadResult(
            state=state,
            bona_fide_score=score,
            threshold=self.config.threshold,
            reason_code=reason,
            model_name=self.config.model_name,
            input_size=self.config.input_size,
        )

    def evaluate_faces(self, faces: Sequence[np.ndarray]) -> PadResult:
        if len(faces) != 1:
            raise PadInputError(
                f"PAD requires exactly one face crop, received {len(faces)}"
            )
        return self.predict(faces[0])
