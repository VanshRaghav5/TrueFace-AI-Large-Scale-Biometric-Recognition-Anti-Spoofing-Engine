"""Configuration for the standalone webcam recognition prototype."""

from dataclasses import dataclass


DEMO_THRESHOLD_UNCALIBRATED = 0.75


@dataclass(frozen=True)
class RealtimeConfig:
    camera_index: int = 0
    camera_width: int = 640
    camera_height: int = 480
    detection_frame_interval: int = 1
    recognition_refresh_interval: int = 5
    pad_refresh_interval: int = 1
    confirmation_frames: int = 2
    similarity_threshold: float = DEMO_THRESHOLD_UNCALIBRATED
    display_fps: bool = True
    show_bounding_boxes: bool = True
    diagnostic_logging: bool = False
    enable_tracking: bool = True
    track_timeout_frames: int = 15
    window_name: str = "TrueFace AI-X - Real-Time Recognition"

    def __post_init__(self) -> None:
        if self.camera_width < 1 or self.camera_height < 1:
            raise ValueError("Camera dimensions must be positive")
        if self.detection_frame_interval < 1:
            raise ValueError("detection_frame_interval must be positive")
        if self.recognition_refresh_interval < 1:
            raise ValueError("recognition_refresh_interval must be positive")
        if self.pad_refresh_interval < 1:
            raise ValueError("pad_refresh_interval must be positive")
        if self.confirmation_frames < 1:
            raise ValueError("confirmation_frames must be positive")
        if not 0.0 <= self.similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be between 0.0 and 1.0")
        if self.track_timeout_frames < 1:
            raise ValueError("track_timeout_frames must be positive")
