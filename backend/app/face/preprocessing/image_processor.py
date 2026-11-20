"""
Image preprocessing and validation utilities for face recognition.
"""

from pathlib import Path
from typing import Set, Tuple, Union
import cv2
import numpy as np

from ..recognition.exceptions import InvalidImageError

SUPPORTED_IMAGE_EXTENSIONS: Set[str] = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tiff",
    ".tif",
    ".webp",
}


def load_image(image_path: Union[str, Path]) -> np.ndarray:
    """
    Load an image from disk and validate format and dimensions.

    Args:
        image_path: Path to the image file.

    Returns:
        BGR image array.

    Raises:
        InvalidImageError: If the path does not exist, format is unsupported, or decoding fails.
    """
    path = Path(image_path)
    if not path.exists():
        raise InvalidImageError(f"Image file not found: {image_path}")

    if not path.is_file():
        raise InvalidImageError(f"Path is not a file: {image_path}")

    if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        raise InvalidImageError(
            f"Unsupported image format: {path.suffix}. "
            f"Supported: {', '.join(sorted(SUPPORTED_IMAGE_EXTENSIONS))}"
        )

    image = cv2.imread(str(path))
    if image is None:
        raise InvalidImageError(
            f"Failed to decode image file: {image_path}. "
            "File may be corrupt or in an unsupported format."
        )

    if image.size == 0:
        raise InvalidImageError(f"Image is empty (0 pixels): {image_path}")

    h, w = image.shape[:2]
    if h < 10 or w < 10:
        raise InvalidImageError(
            f"Image too small ({w}x{h}). Minimum 10x10 pixels required."
        )

    return image


def load_image_from_bytes(image_bytes: bytes) -> np.ndarray:
    """
    Decode raw image bytes into a BGR numpy array with validation.

    Args:
        image_bytes: Raw bytes of an encoded image.

    Returns:
        BGR image array.

    Raises:
        InvalidImageError: If bytes are empty or cannot be decoded.
    """
    if not image_bytes or len(image_bytes) == 0:
        raise InvalidImageError("Empty image bytes provided")

    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        raise InvalidImageError(
            "Failed to decode image from bytes. "
            "Data may be corrupt or in an unsupported format."
        )

    if image.size == 0:
        raise InvalidImageError("Decoded image is empty (0 pixels)")

    h, w = image.shape[:2]
    if h < 10 or w < 10:
        raise InvalidImageError(
            f"Image too small ({w}x{h}). Minimum 10x10 pixels required."
        )

    return image


def preprocess_face_blob(
    aligned_face: np.ndarray,
    target_size: Tuple[int, int] = (112, 112),
    mean: float = 127.5,
    std: float = 127.5,
) -> np.ndarray:
    """
    Convert an aligned BGR face image to an NCHW normalized float32 tensor blob.

    Args:
        aligned_face: BGR face image (H, W, 3).
        target_size: (width, height) expected by model.
        mean: Normalization mean.
        std: Normalization standard deviation.

    Returns:
        4D numpy array (1, 3, H, W) normalized and RGB swapped.
    """
    blob = cv2.dnn.blobFromImage(
        aligned_face,
        scalefactor=1.0 / std,
        size=target_size,
        mean=(mean, mean, mean),
        swapRB=True,
    )
    return blob.astype(np.float32)

