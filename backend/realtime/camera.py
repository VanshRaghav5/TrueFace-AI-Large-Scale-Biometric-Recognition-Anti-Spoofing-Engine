"""Safe OpenCV webcam capture for the standalone prototype."""

from __future__ import annotations

from typing import Optional

import cv2
import numpy as np


class CameraError(RuntimeError):
    """Raised when a camera cannot be opened or stops producing frames."""


class Camera:
    """Single-owner webcam capture with explicit cleanup."""

    def __init__(
        self,
        camera_index: int = 0,
        width: int = 640,
        height: int = 480,
    ) -> None:
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self._capture: Optional[cv2.VideoCapture] = None

    @property
    def is_opened(self) -> bool:
        return bool(self._capture is not None and self._capture.isOpened())

    def open(self) -> None:
        if self._capture is not None:
            raise CameraError("Camera is already open")
        capture = cv2.VideoCapture(self.camera_index)
        if not capture.isOpened():
            capture.release()
            raise CameraError(
                f"Unable to open camera index {self.camera_index}. "
                "Check camera permissions and that no other application owns it."
            )
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._capture = capture

    def read(self) -> np.ndarray:
        if not self.is_opened:
            raise CameraError("Camera is not open")
        ok, frame = self._capture.read()  # type: ignore[union-attr]
        if not ok or frame is None or frame.size == 0:
            raise CameraError("Camera did not provide a valid frame")
        return frame

    def release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self) -> "Camera":
        self.open()
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback) -> None:
        self.release()
