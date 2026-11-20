import numpy as np
import pytest
import cv2

from backend.app.face.alignment import ARCFACE_DST, estimate_norm, norm_crop, norm_crop2, umeyama


def test_umeyama_identity_transformation():
    # Source and destination are identical
    pts = np.array(
        [[10, 10], [50, 10], [30, 30], [20, 50], [40, 50]],
        dtype=np.float32,
    )
    M = umeyama(pts, pts)
    expected = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)
    assert np.allclose(M, expected, atol=1e-5)


def test_umeyama_matches_known_landmarks():
    lmk = np.array(
        [[30, 40], [70, 42], [50, 60], [35, 80], [65, 82]],
        dtype=np.float32,
    )
    dst = ARCFACE_DST.copy()
    M = umeyama(lmk, dst)
    assert M.shape == (2, 3)
    # Check transformed points are close to destination
    pts_homo = np.hstack([lmk, np.ones((5, 1), dtype=np.float32)])
    projected = (M @ pts_homo.T).T
    assert np.mean(np.linalg.norm(projected - dst, axis=1)) < 15.0


def test_estimate_norm_dimensions():
    lmk = np.array(
        [[30, 40], [70, 42], [50, 60], [35, 80], [65, 82]],
        dtype=np.float32,
    )
    M112 = estimate_norm(lmk, image_size=112)
    assert M112.shape == (2, 3)

    M128 = estimate_norm(lmk, image_size=128)
    assert M128.shape == (2, 3)


def test_norm_crop_output_shape():
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    lmk = np.array(
        [[60, 60], [140, 60], [100, 100], [70, 140], [130, 140]],
        dtype=np.float32,
    )
    warped = norm_crop(img, lmk, image_size=112)
    assert warped.shape == (112, 112, 3)

    warped2, M = norm_crop2(img, lmk, image_size=112)
    assert warped2.shape == (112, 112, 3)
    assert M.shape == (2, 3)

