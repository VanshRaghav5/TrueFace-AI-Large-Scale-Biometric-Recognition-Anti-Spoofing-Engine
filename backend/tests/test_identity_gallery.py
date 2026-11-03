import numpy as np
import pytest

from backend.realtime.identity_gallery import IdentityGallery


def vector(index: int = 0) -> np.ndarray:
    value = np.zeros(512, dtype=np.float32)
    value[index] = 1.0
    return value


def test_multiple_templates_select_best_identity():
    gallery = IdentityGallery(threshold=0.75)
    gallery.enroll("a", "Person A", vector(0))
    gallery.enroll("a", "Person A", vector(1))
    gallery.enroll("b", "Person B", vector(2))

    match = gallery.match(vector(1))

    assert match.identity_id == "a"
    assert match.display_name == "Person A"
    assert match.is_match is True
    assert match.similarity == pytest.approx(1.0)
    assert gallery.template_count == 3


def test_below_threshold_is_unknown():
    gallery = IdentityGallery(threshold=0.75)
    gallery.enroll("a", "Person A", vector(0))

    match = gallery.match(vector(1))

    assert match.identity_id is None
    assert match.display_name == "Unknown"
    assert match.is_match is False
    assert match.similarity == pytest.approx(0.0)


def test_empty_gallery_and_invalid_embeddings():
    gallery = IdentityGallery()
    assert gallery.match(vector(0)).display_name == "Unknown"

    with pytest.raises(ValueError):
        gallery.enroll("a", "Person A", np.zeros(511))
    with pytest.raises(ValueError):
        gallery.enroll("a", "Person A", np.full(512, np.nan))
    with pytest.raises(ValueError):
        gallery.enroll("a", "Person A", np.zeros(512))


def test_threshold_boundary_and_removal():
    gallery = IdentityGallery(threshold=1.0)
    gallery.enroll("a", "Person A", vector(0))

    assert gallery.match(vector(0)).is_match is True
    assert gallery.remove("a") is True
    assert gallery.remove("a") is False
    assert len(gallery) == 0
