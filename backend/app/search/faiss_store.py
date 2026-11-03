import os
from typing import List, Tuple, Optional
import numpy as np
from .vector_store import VectorStore
from .identity_mapping import IdentityMapping

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

class FAISSStore(VectorStore):
    """FAISS-backed vector store using inner-product (cosine similarity on L2-normalized vectors)."""

    def __init__(self, dimension: int = 512, mapping_path: Optional[str] = None):
        self.dimension = dimension
        self.mapping = IdentityMapping(mapping_path)
        self.index = None
        self._initialize_index()

    def _initialize_index(self):
        if HAS_FAISS:
            # IndexFlatIP calculates inner product: for unit vectors this equals cosine similarity
            self.index = faiss.IndexFlatIP(self.dimension)
        else:
            self.index = None

    def add_vector(self, embedding: np.ndarray, subject_id: str) -> int:
        embedding = np.ascontiguousarray(embedding.astype("float32").reshape(1, -1))
        # Ensure L2 normalization
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        if HAS_FAISS and self.index is not None:
            idx = self.index.ntotal
            self.index.add(embedding)
            self.mapping.register(idx, subject_id)
            return idx
        else:
            # Fallback mock id when running without faiss compiled
            idx = 0
            self.mapping.register(idx, subject_id)
            return idx

    def search(self, query_embedding: np.ndarray, top_k: int = 1) -> List[Tuple[str, float]]:
        query_embedding = np.ascontiguousarray(query_embedding.astype("float32").reshape(1, -1))
        norm = np.linalg.norm(query_embedding)
        if norm > 0:
            query_embedding = query_embedding / norm

        if HAS_FAISS and self.index is not None and self.index.ntotal > 0:
            k = min(top_k, self.index.ntotal)
            similarities, indices = self.index.search(query_embedding, k)
            results = []
            for sim, idx in zip(similarities[0], indices[0]):
                subj_id = self.mapping.get_subject_id(int(idx))
                if subj_id:
                    results.append((subj_id, float(sim)))
            return results
        return []

    def delete(self, subject_id: str) -> bool:
        self.mapping.remove(subject_id)
        # Note: IndexFlatIP deletion requires index recreation in FAISS Flat structures
        return True

    def save(self, file_path: str) -> None:
        if HAS_FAISS and self.index is not None:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            faiss.write_index(self.index, file_path)

    def load(self, file_path: str) -> None:
        if HAS_FAISS and os.path.exists(file_path):
            self.index = faiss.read_index(file_path)

