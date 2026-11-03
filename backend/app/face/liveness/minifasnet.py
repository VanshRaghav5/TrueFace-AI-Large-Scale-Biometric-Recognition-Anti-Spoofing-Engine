"""Checkpoint-independent MiniFASNet two-branch ONNX adapter.

The adapter follows the upstream OpenCV inference contract. It does not
provide defaults for the validation threshold or uncertainty margin.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor, isfinite
from pathlib import Path
from typing import Callable, Optional, Sequence

import cv2
import numpy as np

from .exceptions import (
    PadInferenceError,
    PadInputError,
    PadModelUnavailableError,
    PadOutputContractError,
)


@dataclass(frozen=True)
class MiniFASNetConfig:
    v2_path: Path
    v1se_path: Path
    input_size: int = 80
    bona_fide_class_index: int = 1
    v2_scale: float = 2.7
    v1se_scale: float = 4.0
    model_name: str = "minifasnet_ensemble"

    def __post_init__(self) -> None:
        if self.input_size != 80:
            raise ValueError("MiniFASNet checkpoints require 80x80 inputs")
        if self.bona_fide_class_index != 1:
            raise ValueError("The upstream MiniFASNet contract uses class index 1")
        if self.v2_scale <= 0.0 or self.v1se_scale <= 0.0:
            raise ValueError("Crop scales must be positive")


@dataclass(frozen=True)
class MiniFASNetPrediction:
    bona_fide_score: float
    branch_scores: tuple[float, float]
    model_name: str


def _bbox_to_xywh(bounding_box: Sequence[float]) -> tuple[int, int, int, int]:
    """Convert SCRFD xyxy boxes using floor/ceil edge normalization.

    Upper-left coordinates are floored and lower-right coordinates are
    ceiled. This deterministic policy is an adapter choice, not a claim about
    the upstream floating-point crop implementation.
    """
    if len(bounding_box) != 4:
        raise PadInputError("Bounding box must contain [x1, y1, x2, y2]")
    values = tuple(float(value) for value in bounding_box)
    if not all(isfinite(value) for value in values):
        raise PadInputError("Bounding box must contain finite coordinates")
    raw_x1, raw_y1, raw_x2, raw_y2 = values
    if raw_x2 <= raw_x1 or raw_y2 <= raw_y1:
        raise PadInputError("Bounding box must have positive dimensions")
    x1, y1 = floor(raw_x1), floor(raw_y1)
    x2, y2 = ceil(raw_x2), ceil(raw_y2)
    if x2 <= x1 or y2 <= y1:
        raise PadInputError("Bounding box must have positive dimensions")
    return x1, y1, x2 - x1, y2 - y1


def crop_scaled_face(
    image_bgr: np.ndarray,
    bounding_box: Sequence[float],
    scale: float,
    output_size: int = 80,
) -> np.ndarray:
    """Reproduce upstream center crop expansion and boundary clipping."""
    if not isinstance(image_bgr, np.ndarray) or image_bgr.size == 0:
        raise PadInputError("Image must be a non-empty NumPy array")
    if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
        raise PadInputError("Image must be a BGR color image")
    if scale <= 0.0:
        raise PadInputError("Crop scale must be positive")
    x, y, width, height = _bbox_to_xywh(bounding_box)
    image_height, image_width = image_bgr.shape[:2]
    if x < 0 or y < 0 or x + width > image_width or y + height > image_height:
        raise PadInputError("Bounding box must lie within the image")
    center_x, center_y = x + width / 2, y + height / 2
    crop_width, crop_height = width * scale, height * scale
    left = max(0, int(center_x - crop_width / 2))
    top = max(0, int(center_y - crop_height / 2))
    right = min(image_width - 1, int(center_x + crop_width / 2))
    bottom = min(image_height - 1, int(center_y + crop_height / 2))
    if right <= left or bottom <= top:
        raise PadInputError("Scaled face crop is empty")
    crop = image_bgr[top : bottom + 1, left : right + 1]
    if crop.size == 0:
        raise PadInputError("Scaled face crop is empty")
    return cv2.resize(crop, (output_size, output_size), interpolation=cv2.INTER_LINEAR)


def minifasnet_tensor(image_bgr: np.ndarray) -> np.ndarray:
    """Return upstream-compatible float32 NCHW BGR data without /255 scaling."""
    if not isinstance(image_bgr, np.ndarray) or image_bgr.shape != (80, 80, 3):
        raise PadInputError("MiniFASNet input crop must be exactly 80x80x3")
    if not np.all(np.isfinite(image_bgr)):
        raise PadInputError("MiniFASNet input contains non-finite values")
    return image_bgr.astype(np.float32).transpose(2, 0, 1)[None, ...]


def _softmax_three_class(output: np.ndarray) -> np.ndarray:
    values = np.asarray(output, dtype=np.float64)
    if values.shape != (1, 3):
        raise PadOutputContractError(
            f"MiniFASNet output must have shape (1, 3), got {values.shape}"
        )
    if not np.all(np.isfinite(values)):
        raise PadOutputContractError("MiniFASNet output contains non-finite values")
    shifted = values - np.max(values, axis=1, keepdims=True)
    probabilities = np.exp(shifted)
    probabilities /= np.sum(probabilities, axis=1, keepdims=True)
    return probabilities.astype(np.float32)


class MiniFASNetEnsemble:
    """Run the two official branch contracts without requiring checkpoints."""

    def __init__(
        self,
        config: MiniFASNetConfig,
        session_factory: Optional[Callable[[Path], object]] = None,
    ) -> None:
        self.config = config
        self._session_factory = session_factory
        self._sessions: list[object] = []

    def load_model(self) -> None:
        if not self.config.v2_path.is_file() or not self.config.v1se_path.is_file():
            raise PadModelUnavailableError("Both MiniFASNet checkpoint files are required")
        if self._session_factory is None:
            try:
                import onnxruntime
                self._session_factory = lambda path: onnxruntime.InferenceSession(
                    str(path),
                    providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
                )
            except Exception as exc:
                raise PadModelUnavailableError(
                    f"ONNX Runtime is unavailable for MiniFASNet: {exc}"
                ) from exc
        try:
            self._sessions = [
                self._session_factory(self.config.v2_path),
                self._session_factory(self.config.v1se_path),
            ]
        except Exception as exc:
            self._sessions = []
            raise PadModelUnavailableError(
                f"Failed to load MiniFASNet ensemble: {exc}"
            ) from exc

    def predict_score(
        self,
        image_bgr: np.ndarray,
        bounding_box: Sequence[int],
    ) -> MiniFASNetPrediction:
        if len(self._sessions) != 2:
            raise PadModelUnavailableError("MiniFASNet ensemble is not loaded")
        crops = (
            crop_scaled_face(image_bgr, bounding_box, self.config.v2_scale),
            crop_scaled_face(image_bgr, bounding_box, self.config.v1se_scale),
        )
        scores: list[float] = []
        for session, crop in zip(self._sessions, crops):
            try:
                inputs = session.get_inputs()
                if len(inputs) != 1:
                    raise PadOutputContractError("MiniFASNet requires one input tensor")
                output = session.run(None, {inputs[0].name: minifasnet_tensor(crop)})[0]
                probabilities = _softmax_three_class(output)
                scores.append(float(probabilities[0, self.config.bona_fide_class_index]))
            except (PadInputError, PadOutputContractError):
                raise
            except Exception as exc:
                raise PadInferenceError(f"MiniFASNet inference failed: {exc}") from exc
        return MiniFASNetPrediction(
            bona_fide_score=float(np.mean(scores)),
            branch_scores=(scores[0], scores[1]),
            model_name=self.config.model_name,
        )
