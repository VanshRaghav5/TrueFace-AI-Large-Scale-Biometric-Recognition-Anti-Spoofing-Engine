from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
import numpy as np

class VectorStore(ABC):
    """Abstract interface for biometric vector store implementations."""

    @abstractmethod
    def add_vector(self, embedding: np.ndarray, subject_id: str) -> int:
        """Add a single embedding vector associated with a subject ID."""
        pass

    @abstractmethod
    def search(self, query_embedding: np.ndarray, top_k: int = 1) -> List[Tuple[str, float]]:
        """Search top-k nearest neighbors, returning (subject_id, similarity) pairs."""
        pass

    @abstractmethod
    def delete(self, subject_id: str) -> bool:
        """Remove a subject's vector and rebuild/compact the index."""
        pass

    @abstractmethod
    def save(self, file_path: str) -> None:
        """Persist index state to disk."""
        pass

    @abstractmethod
    def load(self, file_path: str) -> None:
        """Load index state from disk."""
        pass

