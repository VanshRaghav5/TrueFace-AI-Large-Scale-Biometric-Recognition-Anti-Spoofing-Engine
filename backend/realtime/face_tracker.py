"""Small IoU-based tracker for cached display results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence


BBox = List[int]


@dataclass
class Track:
    track_id: int
    bounding_box: BBox
    last_seen_frame: int
    last_result: Optional[Any] = None
    last_recognition_frame: int = -1
    current_identity_id: Optional[str] = None
    recognition_history: List[Any] = None
    candidate_identity_id: Optional[str] = None
    candidate_count: int = 0

    def __post_init__(self) -> None:
        if self.recognition_history is None:
            self.recognition_history = []


def _iou(first: Sequence[int], second: Sequence[int]) -> float:
    left = max(first[0], second[0])
    top = max(first[1], second[1])
    right = min(first[2], second[2])
    bottom = min(first[3], second[3])
    intersection = max(0, right - left) * max(0, bottom - top)
    first_area = max(0, first[2] - first[0]) * max(0, first[3] - first[1])
    second_area = max(0, second[2] - second[0]) * max(0, second[3] - second[1])
    union = first_area + second_area - intersection
    return intersection / union if union else 0.0


class FaceTracker:
    def __init__(self, timeout_frames: int = 15, iou_threshold: float = 0.3):
        if timeout_frames < 1:
            raise ValueError("timeout_frames must be positive")
        if not 0.0 <= iou_threshold <= 1.0:
            raise ValueError("iou_threshold must be between 0.0 and 1.0")
        self.timeout_frames = timeout_frames
        self.iou_threshold = iou_threshold
        self._tracks: Dict[int, Track] = {}
        self._next_id = 1

    def update(self, boxes: Sequence[BBox], frame_number: int) -> List[Track]:
        updated: List[Track] = []
        used_ids = set()
        for box in boxes:
            candidates = [
                track
                for track in self._tracks.values()
                if track.track_id not in used_ids
                and _iou(track.bounding_box, box) >= self.iou_threshold
            ]
            track = max(
                candidates,
                key=lambda value: _iou(value.bounding_box, box),
                default=None,
            )
            if track is None:
                track = Track(self._next_id, list(box), frame_number)
                self._next_id += 1
            else:
                track.bounding_box = list(box)
                track.last_seen_frame = frame_number
            used_ids.add(track.track_id)
            self._tracks[track.track_id] = track
            updated.append(track)

        self._tracks = {
            track_id: track
            for track_id, track in self._tracks.items()
            if frame_number - track.last_seen_frame <= self.timeout_frames
        }
        return updated

    def clear(self) -> None:
        self._tracks.clear()

    @property
    def active_track_count(self) -> int:
        return len(self._tracks)
