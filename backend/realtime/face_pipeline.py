"""Per-face coordination for identity recognition and PAD."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Protocol

import numpy as np

try:
    from backend.app.face.liveness import PadResult, PadState
    from backend.app.face.liveness.exceptions import PadError, PadModelUnavailableError
    from backend.app.face.recognition.arcface_engine import DetectedFace
    from backend.realtime.identity_gallery import GalleryMatch, IdentityGallery
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    from app.face.liveness import PadResult, PadState
    from app.face.liveness.exceptions import PadError, PadModelUnavailableError
    from app.face.recognition.arcface_engine import DetectedFace
    from realtime.identity_gallery import GalleryMatch, IdentityGallery


class PadAdapter(Protocol):
    execution_provider: Optional[str]

    def predict_raw(self, face_bgr: np.ndarray): ...


@dataclass(frozen=True)
class FacePipelineResult:
    match: GalleryMatch
    identity_state: str
    pad_result: PadResult
    pad_real_score: float | None
    pad_spoof_score: float | None
    identity_latency_ms: float
    pad_latency_ms: float
    total_processing_latency_ms: float
    arcface_provider: str
    pad_provider: Optional[str]


class FacePipelineService:
    """Run independent identity and authenticity branches for one detection."""

    def __init__(
        self,
        gallery: IdentityGallery,
        pad_adapter: Optional[PadAdapter] = None,
        pad_threshold: Optional[float] = None,
        pad_uncertainty_margin: float = 0.05,
        pad_model_name: str = "anti-spoof-mn3",
        arcface_provider: str = "unknown",
    ) -> None:
        if pad_threshold is not None and not 0.0 <= pad_threshold <= 1.0:
            raise ValueError("pad_threshold must be between 0.0 and 1.0")
        if not 0.0 <= pad_uncertainty_margin < 0.5:
            raise ValueError("pad_uncertainty_margin must be in [0.0, 0.5)")
        self.gallery = gallery
        self.pad_adapter = pad_adapter
        self.pad_threshold = pad_threshold
        self.pad_uncertainty_margin = pad_uncertainty_margin
        self.pad_model_name = pad_model_name
        self.arcface_provider = arcface_provider

    @staticmethod
    def _pad_unavailable(reason: str, model_name: str) -> PadResult:
        return PadResult(
            PadState.UNAVAILABLE,
            None,
            None,
            reason,
            model_name,
            128,
        )

    @staticmethod
    def _crop(frame: np.ndarray, face: DetectedFace) -> np.ndarray:
        if frame is None or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("Frame must be a BGR color image")
        height, width = frame.shape[:2]
        x1, y1, x2, y2 = face.bounding_box
        left, top = max(0, x1), max(0, y1)
        right, bottom = min(width, x2), min(height, y2)
        if right <= left or bottom <= top:
            raise ValueError("Detected face bounding box is outside the frame")
        return frame[top:bottom, left:right]

    def _evaluate_pad(
        self, frame: np.ndarray, face: DetectedFace
    ) -> tuple[PadResult, float, float | None, float | None]:
        if self.pad_adapter is None:
            return (
                self._pad_unavailable("PAD_MODEL_UNAVAILABLE", self.pad_model_name),
                0.0,
                None,
                None,
            )
        started = time.perf_counter()
        real_score = None
        spoof_score = None
        try:
            raw = self.pad_adapter.predict_raw(self._crop(frame, face))
            real_score = float(raw.real_score)
            spoof_score = float(raw.spoof_score)
            if (
                not np.isfinite(real_score)
                or not np.isfinite(spoof_score)
                or not 0.0 <= real_score <= 1.0
                or not 0.0 <= spoof_score <= 1.0
            ):
                real_score = None
                spoof_score = None
                raise ValueError("PAD adapter returned invalid scores")
            if self.pad_threshold is None:
                pad_result = PadResult(
                    PadState.UNCERTAIN,
                    raw.real_score,
                    None,
                    "PAD_THRESHOLD_UNCALIBRATED",
                    raw.model_name,
                    128,
                )
            else:
                try:
                    from backend.app.face.liveness import PadOrchestrator
                except ModuleNotFoundError as exc:
                    if exc.name != "backend":
                        raise
                    from app.face.liveness import PadOrchestrator

                pad_result = PadOrchestrator(raw.model_name, 128).classify_score(
                    raw.real_score,
                    self.pad_threshold,
                    self.pad_uncertainty_margin,
                )
        except PadModelUnavailableError:
            pad_result = self._pad_unavailable(
                "PAD_MODEL_UNAVAILABLE", self.pad_model_name
            )
        except PadError:
            pad_result = PadResult(
                PadState.ERROR,
                None,
                self.pad_threshold,
                "PAD_EVALUATION_ERROR",
                self.pad_model_name,
                128,
            )
        except Exception as exc:
            pad_result = PadResult(
                PadState.ERROR,
                None,
                self.pad_threshold,
                f"PAD_UNEXPECTED_ERROR:{type(exc).__name__}",
                self.pad_model_name,
                128,
            )
        return (
            pad_result,
            (time.perf_counter() - started) * 1000.0,
            real_score,
            spoof_score,
        )

    def process_face(
        self,
        frame: np.ndarray,
        face: DetectedFace,
    ) -> FacePipelineResult:
        started = time.perf_counter()
        identity_started = time.perf_counter()
        try:
            if face.embedding is None:
                raise ValueError("Detected face did not include an ArcFace embedding")
            match = self.gallery.match(face.embedding)
            identity_state = "known" if match.is_match else "unknown"
        except Exception:
            match = GalleryMatch(None, "Unknown", None, False)
            identity_state = "error"
        identity_latency = (time.perf_counter() - identity_started) * 1000.0
        pad_result, pad_latency, pad_real_score, pad_spoof_score = (
            self._evaluate_pad(frame, face)
        )
        return FacePipelineResult(
            match=match,
            identity_state=identity_state,
            pad_result=pad_result,
            pad_real_score=pad_real_score,
            pad_spoof_score=pad_spoof_score,
            identity_latency_ms=identity_latency,
            pad_latency_ms=pad_latency,
            total_processing_latency_ms=(time.perf_counter() - started) * 1000.0,
            arcface_provider=self.arcface_provider,
            pad_provider=getattr(self.pad_adapter, "execution_provider", None),
        )
