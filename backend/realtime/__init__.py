"""Standalone webcam recognition prototype."""

from .config import RealtimeConfig
from .identity_gallery import GalleryMatch, IdentityGallery

__all__ = ["GalleryMatch", "IdentityGallery", "RealtimeConfig"]
