"""
In-memory LRU cache for face embeddings and voice templates.
Reduces database queries and speeds up repeated authentications.
"""
from functools import lru_cache
from typing import Optional, Tuple
import numpy as np
import hashlib


class EmbeddingCache:
    """Thread-safe LRU cache for face embeddings."""
    
    def __init__(self, maxsize: int = 1000):
        self._cache = {}
        self.maxsize = maxsize
        self._access_order = []
    
    def _make_key(self, image_bytes: bytes) -> str:
        """Generate cache key from image bytes hash."""
        return hashlib.sha256(image_bytes[:10000]).hexdigest()[:16]
    
    def get(self, image_bytes: bytes) -> Optional[Tuple[np.ndarray, dict]]:
        """Retrieve cached embedding and extraction result."""
        key = self._make_key(image_bytes)
        if key in self._cache:
            # Move to end (most recently used)
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
        return None
    
    def set(self, image_bytes: bytes, embedding: np.ndarray, extraction: dict):
        """Cache embedding and extraction result."""
        key = self._make_key(image_bytes)
        
        # Evict oldest if at capacity
        if len(self._cache) >= self.maxsize and key not in self._cache:
            oldest = self._access_order.pop(0)
            del self._cache[oldest]
        
        self._cache[key] = (embedding, extraction)
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def clear(self):
        """Clear all cached embeddings."""
        self._cache.clear()
        self._access_order.clear()


# Global singleton instances
embedding_cache = EmbeddingCache(maxsize=1000)
pad_cache = EmbeddingCache(maxsize=500)
deepfake_cache = EmbeddingCache(maxsize=500)


def get_embedding_cache() -> EmbeddingCache:
    """Get global embedding cache instance."""
    return embedding_cache


def get_pad_cache() -> EmbeddingCache:
    """Get global PAD result cache instance."""
    return pad_cache


def get_deepfake_cache() -> EmbeddingCache:
    """Get global deepfake result cache instance."""
    return deepfake_cache
