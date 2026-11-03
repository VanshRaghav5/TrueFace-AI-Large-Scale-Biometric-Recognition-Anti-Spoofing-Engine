"""In-memory identity gallery for the webcam prototype."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import numpy as np


@dataclass(frozen=True)
class GalleryMatch:
    identity_id: Optional[str]
    display_name: str
    similarity: Optional[float]
    is_match: bool


class IdentityGallery:
    """Store normalized templates only for the lifetime of the process."""

    def __init__(self, threshold: float = 0.75) -> None:
        self._validate_threshold(threshold)
        self.threshold = float(threshold)
        self._templates: Dict[str, List[np.ndarray]] = {}
        self._names: Dict[str, str] = {}

    @staticmethod
    def _validate_threshold(value: float) -> None:
        if not np.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {value}")

    @staticmethod
    def _normalize_embedding(embedding: np.ndarray) -> np.ndarray:
        vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
        if vector.shape != (512,):
            raise ValueError(f"Embedding must contain 512 values, got {vector.size}")
        if not np.all(np.isfinite(vector)):
            raise ValueError("Embedding contains non-finite values")
        norm = float(np.linalg.norm(vector))
        if norm <= np.finfo(np.float32).eps:
            raise ValueError("Embedding must have a non-zero norm")
        return (vector / norm).astype(np.float32)

    def enroll(
        self,
        identity_id: str,
        display_name: str,
        embedding: np.ndarray,
    ) -> None:
        if not identity_id or not display_name:
            raise ValueError("identity_id and display_name are required")
        normalized = self._normalize_embedding(embedding)
        self._templates.setdefault(identity_id, []).append(normalized)
        self._names[identity_id] = display_name

    def enroll_many(
        self,
        identity_id: str,
        display_name: str,
        embeddings: Iterable[np.ndarray],
    ) -> None:
        values = list(embeddings)
        if not values:
            raise ValueError("At least one enrollment embedding is required")
        for embedding in values:
            self.enroll(identity_id, display_name, embedding)

    def match(self, embedding: np.ndarray) -> GalleryMatch:
        query = self._normalize_embedding(embedding)
        if not self._templates:
            return GalleryMatch(None, "Unknown", None, False)

        best_id: Optional[str] = None
        best_similarity = -1.0
        for identity_id, templates in self._templates.items():
            similarity = max(float(np.dot(query, template)) for template in templates)
            if similarity > best_similarity:
                best_id = identity_id
                best_similarity = similarity

        if best_id is None or best_similarity < self.threshold:
            return GalleryMatch(None, "Unknown", best_similarity, False)
        return GalleryMatch(
            best_id,
            self._names[best_id],
            best_similarity,
            True,
        )

    def remove(self, identity_id: str) -> bool:
        removed = identity_id in self._templates
        self._templates.pop(identity_id, None)
        self._names.pop(identity_id, None)
        return removed

    def clear(self) -> None:
        self._templates.clear()
        self._names.clear()

    @property
    def identity_count(self) -> int:
        return len(self._templates)

    @property
    def template_count(self) -> int:
        return sum(len(values) for values in self._templates.values())

    def __len__(self) -> int:
        return self.identity_count
