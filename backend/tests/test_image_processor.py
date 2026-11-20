import numpy as np
import pytest
import cv2

from backend.app.face.preprocessing import (
    load_image_from_bytes,
    preprocess_face_blob,
)
from backend.app.face.recognition.exceptions import InvalidImageError


def test_load_image_from_bytes_valid():
    img = np.zeros((50, 50, 3), dtype=np.uint8)
    _, encoded = cv2.imencode(".jpg", img)
    decoded = load_image_from_bytes(encoded.tobytes())
    assert decoded.shape == (50, 50, 3)


def test_load_image_from_bytes_empty():
    with pytest.raises(InvalidImageError):
        load_image_from_bytes(b"")


def test_load_image_from_bytes_corrupt():
    with pytest.raises(InvalidImageError):
        load_image_from_bytes(b"not-a-valid-image-format")


def test_load_image_from_bytes_too_small():
    img = np.zeros((8, 8, 3), dtype=np.uint8)
    _, encoded = cv2.imencode(".png", img)
    with pytest.raises(InvalidImageError):
        load_image_from_bytes(encoded.tobytes())


def test_preprocess_face_blob():
    face = np.full((112, 112, 3), 127.5, dtype=np.uint8)
    blob = preprocess_face_blob(face, target_size=(112, 112), mean=127.5, std=127.5)
    assert blob.shape == (1, 3, 112, 112)
    assert blob.dtype == np.float32
    assert np.allclose(blob, 0.0, atol=1e-2)

