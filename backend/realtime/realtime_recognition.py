"""Recognition and enrollment orchestration for the webcam demo."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable, List

import cv2
import numpy as np

try:
    from backend.app.face.recognition.arcface_engine import ArcFaceEngine
    from backend.app.face.recognition.exceptions import FaceRecognitionError
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    from app.face.recognition.arcface_engine import ArcFaceEngine
    from app.face.recognition.exceptions import FaceRecognitionError

from .config import RealtimeConfig
from .face_tracker import FaceTracker, Track
from .face_pipeline import FacePipelineService
from .identity_gallery import GalleryMatch, IdentityGallery

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EnrollmentFailure:
    identity_id: str
    image_path: str
    error_type: str
    error: str


@dataclass(frozen=True)
class FaceRecognitionResult:
    bounding_box: List[int]
    match: GalleryMatch
    detection_score: float
    processing_time_ms: float
    track_id: int | None = None
    identity_state: str = "unknown"
    pad_real_score: float | None = None
    pad_spoof_score: float | None = None
    pad_state: str = "unavailable"
    identity_latency_ms: float = 0.0
    pad_latency_ms: float = 0.0
    total_processing_latency_ms: float = 0.0
    arcface_provider: str = "unknown"
    pad_provider: str | None = None


class RealtimeRecognizer:
    def __init__(
        self,
        engine: ArcFaceEngine,
        gallery: IdentityGallery,
        config: RealtimeConfig,
        pad_adapter=None,
        pad_threshold: float | None = None,
        pad_uncertainty_margin: float = 0.05,
    ) -> None:
        self.engine = engine
        self.gallery = gallery
        self.config = config
        self.tracker = FaceTracker(config.track_timeout_frames)
        self.pipeline = FacePipelineService(
            gallery,
            pad_adapter=pad_adapter,
            pad_threshold=pad_threshold,
            pad_uncertainty_margin=pad_uncertainty_margin,
            arcface_provider=self._provider_name(),
        )
        self._frame_number = 0

    def _provider_name(self) -> str:
        providers = getattr(self.engine, "active_providers", [])
        if providers:
            return str(providers[0])
        return "CUDAExecutionProvider" if getattr(self.engine, "is_gpu_active", False) else "CPU/fallback"

    @staticmethod
    def _unknown_match(similarity: float | None = None) -> GalleryMatch:
        return GalleryMatch(None, "Unknown", similarity, False)

    def _stabilize_match(self, track: Track, raw_match: GalleryMatch) -> GalleryMatch:
        """Require repeated strong evidence before displaying an identity."""
        track.recognition_history.append(raw_match)
        track.recognition_history = track.recognition_history[-10:]

        if not raw_match.is_match or raw_match.identity_id is None:
            track.candidate_identity_id = None
            track.candidate_count = 0
            track.current_identity_id = None
            return self._unknown_match(raw_match.similarity)

        if raw_match.identity_id == track.candidate_identity_id:
            track.candidate_count += 1
        else:
            track.candidate_identity_id = raw_match.identity_id
            track.candidate_count = 1

        if track.candidate_count < self.config.confirmation_frames:
            return self._unknown_match(raw_match.similarity)

        track.current_identity_id = raw_match.identity_id
        return raw_match

    def enroll_images(
        self,
        identity_id: str,
        display_name: str,
        image_paths: Iterable[str | Path],
        consent_confirmed: bool = False,
    ) -> List[EnrollmentFailure]:
        if not consent_confirmed:
            raise PermissionError(
                "Explicit consent_confirmed=True is required before enrollment"
            )
        failures: List[EnrollmentFailure] = []
        accepted = 0
        for image_path in image_paths:
            path = str(image_path)
            try:
                result = self.engine.extract_from_path(path)
                self.gallery.enroll(identity_id, display_name, result.embedding)
                accepted += 1
            except Exception as exc:
                failures.append(
                    EnrollmentFailure(
                        identity_id,
                        path,
                        type(exc).__name__,
                        str(exc),
                    )
                )
        if accepted == 0:
            raise FaceRecognitionError(
                f"No enrollment images were accepted for identity '{identity_id}'"
            )
        return failures

    def process_frame(self, frame: np.ndarray, force_recognition: bool = False) -> List[FaceRecognitionResult]:
        if frame is None or frame.size == 0:
            raise ValueError("Frame is empty")
        self._frame_number += 1
        faces = self.engine.detect_faces(frame)
        tracks = self.tracker.update(
            [face.bounding_box for face in faces],
            self._frame_number,
        )
        results: List[FaceRecognitionResult] = []
        for face, track in zip(faces, tracks):
            refresh = (
                force_recognition
                or track.last_result is None
                or self._frame_number - track.last_recognition_frame
                >= self.config.recognition_refresh_interval
                or (
                    self.pipeline.pad_adapter is not None
                    and self._frame_number - track.last_recognition_frame
                    >= self.config.pad_refresh_interval
                )
            )
            if refresh:
                try:
                    pipeline = self.pipeline.process_face(frame, face)
                    match = self._stabilize_match(track, pipeline.match)
                    track.last_result = FaceRecognitionResult(
                        face.bounding_box,
                        match,
                        face.detection_score,
                        pipeline.identity_latency_ms,
                        track.track_id,
                        pipeline.identity_state,
                        pipeline.pad_real_score,
                        pipeline.pad_spoof_score,
                        pipeline.pad_result.state.value,
                        pipeline.identity_latency_ms,
                        pipeline.pad_latency_ms,
                        pipeline.total_processing_latency_ms,
                        pipeline.arcface_provider,
                        pipeline.pad_provider,
                    )
                    track.last_recognition_frame = self._frame_number
                except Exception as exc:
                    logger.warning("Face recognition failed: %s", exc)
                    track.last_result = FaceRecognitionResult(
                        face.bounding_box,
                        self._unknown_match(),
                        face.detection_score,
                        0.0,
                        track.track_id,
                        "error",
                        None,
                        None,
                        "error",
                    )
                    track.last_recognition_frame = self._frame_number
            result = track.last_result
            if result is not None:
                if not refresh and self.pipeline.pad_adapter is not None:
                    result = replace(
                        result,
                        pad_real_score=None,
                        pad_spoof_score=None,
                        pad_state="unavailable",
                        pad_latency_ms=0.0,
                        total_processing_latency_ms=result.identity_latency_ms,
                    )
                results.append(result)
        return results

    def draw(
        self,
        frame: np.ndarray,
        results: Iterable[FaceRecognitionResult],
        fps: float,
        gpu_active: bool,
    ) -> np.ndarray:
        output = frame.copy()
        for result in results:
            x1, y1, x2, y2 = result.bounding_box
            color = (0, 180, 0) if result.match.is_match else (0, 0, 255)
            if self.config.show_bounding_boxes:
                cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)
            similarity = (
                f"{result.match.similarity:.3f}"
                if result.match.similarity is not None
                else "n/a"
            )
            track = f"Track {result.track_id}" if result.track_id is not None else "Track n/a"
            pad_scores = ""
            if result.pad_real_score is not None and result.pad_spoof_score is not None:
                pad_scores = (
                    f" R:{result.pad_real_score:.2f}"
                    f" S:{result.pad_spoof_score:.2f}"
                )
            label = (
                f"{track} | {result.match.display_name} | "
                f"Similarity: {similarity} | PAD: {result.pad_state}"
                f"{pad_scores} | "
                f"{result.total_processing_latency_ms:.1f} ms"
            )
            cv2.putText(
                output, label, (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA,
            )
        cv2.putText(
            output,
            f"FPS: {fps:.1f} | ArcFace: {'CUDA' if gpu_active else 'CPU/fallback'}",
            (10, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            output,
            f"Enrolled identities: {self.gallery.identity_count} | "
            f"PAD: {self._pad_status()} | Q: quit R: refresh H: help",
            (10, 48),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        return output

    def _pad_status(self) -> str:
        if self.pipeline.pad_adapter is None:
            return "unavailable"
        provider = getattr(self.pipeline.pad_adapter, "execution_provider", None)
        return provider or "configured"
