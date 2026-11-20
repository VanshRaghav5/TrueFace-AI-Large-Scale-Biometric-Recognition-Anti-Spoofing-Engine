"""
Face Alignment Module — InsightFace Reference Implementation.

Provides 5-point facial landmark alignment and similarity transform
using the standard ArcFace canonical coordinate space.
"""

from typing import Optional, Tuple
import cv2
import numpy as np

# Canonical ArcFace reference coordinates for 112x112 space
ARCFACE_DST = np.array(
    [
        [38.2946, 51.6963],  # left eye
        [73.5318, 51.5014],  # right eye
        [56.0252, 71.7366],  # nose tip
        [41.5493, 92.3655],  # left mouth corner
        [70.7299, 92.2041],  # right mouth corner
    ],
    dtype=np.float32,
)


def umeyama(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """
    Estimate 2D similarity transform parameters (rotation, scale, translation)
    using the closed-form Umeyama algorithm.

    Args:
        src: Source points (N, 2).
        dst: Destination points (N, 2).

    Returns:
        2x3 affine transformation matrix M.
    """
    src = np.asarray(src, dtype=np.float32)
    dst = np.asarray(dst, dtype=np.float32)

    src_mean = src.mean(axis=0)
    dst_mean = dst.mean(axis=0)

    src_centered = src - src_mean
    dst_centered = dst - dst_mean

    var = np.mean(np.sum(src_centered**2, axis=1))
    if var == 0:
        return np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)

    cov = dst_centered.T @ src_centered / src.shape[0]
    u, s, vh = np.linalg.svd(cov)

    det = np.linalg.det(u) * np.linalg.det(vh)
    d = np.ones(2, dtype=np.float32)
    if det < 0:
        d[1] = -1

    r = u @ np.diag(d) @ vh
    scale = np.sum(s * d) / var
    t = dst_mean - scale * (r @ src_mean)

    return np.hstack([scale * r, t[:, None]])


def estimate_norm(
    landmark: np.ndarray,
    image_size: int = 112,
    mode: str = "arcface",
) -> np.ndarray:
    """
    Estimate similarity transform matrix for standard ArcFace alignment.

    Args:
        landmark: 5x2 array of facial landmarks [[x, y], ...].
        image_size: Target aligned image size (typically 112).
        mode: Alignment mode ("arcface").

    Returns:
        2x3 affine transformation matrix M.
    """
    assert landmark.shape == (5, 2), f"Expected landmark shape (5, 2), got {landmark.shape}"
    assert image_size % 112 == 0 or image_size % 128 == 0

    if image_size % 112 == 0:
        ratio = float(image_size) / 112.0
        diff_x = 0.0
    else:
        ratio = float(image_size) / 128.0
        diff_x = 8.0 * ratio

    dst = ARCFACE_DST * ratio
    dst[:, 0] += diff_x

    try:
        from skimage import transform as trans
        tform = trans.SimilarityTransform()
        tform.estimate(landmark, dst)
        return tform.params[0:2, :].astype(np.float32)
    except (ImportError, Exception):
        return umeyama(landmark, dst).astype(np.float32)


def norm_crop(
    img: np.ndarray,
    landmark: np.ndarray,
    image_size: int = 112,
    mode: str = "arcface",
) -> np.ndarray:
    """
    Align and crop a face image using 5-point facial landmarks.

    Args:
        img: BGR image as numpy array.
        landmark: 5x2 facial landmark coordinates.
        image_size: Output image dimension (square, default 112).
        mode: Alignment mode.

    Returns:
        Aligned and cropped 112x112 face image.
    """
    M = estimate_norm(landmark, image_size=image_size, mode=mode)
    warped = cv2.warpAffine(img, M, (image_size, image_size), borderValue=0.0)
    return warped


def norm_crop2(
    img: np.ndarray,
    landmark: np.ndarray,
    image_size: int = 112,
    mode: str = "arcface",
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Align and crop a face image, returning both the cropped face and transformation matrix.

    Args:
        img: BGR image.
        landmark: 5x2 landmarks.
        image_size: Target dimension.
        mode: Alignment mode.

    Returns:
        Tuple of (warped_face, affine_matrix_2x3).
    """
    M = estimate_norm(landmark, image_size=image_size, mode=mode)
    warped = cv2.warpAffine(img, M, (image_size, image_size), borderValue=0.0)
    return warped, M

