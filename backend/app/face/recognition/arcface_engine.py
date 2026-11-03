"""
ArcFace Recognition Engine for TrueFace AI-X.

Provides face detection, alignment, and 512-dimensional ArcFace embedding
extraction using the InsightFace library with ONNX Runtime GPU inference.

Model: InsightFace buffalo_l model pack (includes SCRFD detector + ArcFace recognizer)
License: The buffalo_l model pack is released under a non-commercial research license
         by InsightFace (https://github.com/deepinsight/insightface/tree/master/model_zoo).
         Check https://github.com/deepinsight/insightface/blob/master/LICENSE for details.
         For commercial use, obtain appropriate licensing from InsightFace/ArcSoft.
Source:  InsightFace model zoo, version buffalo_l
Output:  512-dimensional L2-normalized ArcFace embedding
"""

import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from .exceptions import (
    FaceNotDetectedError,
    FaceRecognitionError,
    InvalidImageError,
    ModelUnavailableError,
    MultipleFacesDetectedError,
)

logger = logging.getLogger(__name__)


@dataclass
class DetectedFace:
    """Structured result from face detection."""

    bounding_box: List[int]  # [x1, y1, x2, y2]
    detection_score: float
    landmarks: Optional[np.ndarray] = None  # 5-point facial landmarks
    aligned_face: Optional[np.ndarray] = None  # Aligned and cropped face image
    embedding: Optional[np.ndarray] = None  # Internal 512-d ArcFace embedding


@dataclass
class EmbeddingResult:
    """Structured result from embedding extraction."""

    embedding: np.ndarray  # 512-d L2-normalized embedding
    bounding_box: List[int]  # [x1, y1, x2, y2]
    detection_score: float
    model_name: str = "arcface_buffalo_l"
    inference_time_ms: float = 0.0
    aligned_face_path: Optional[str] = None


@dataclass
class VerificationResult:
    """Structured result from 1:1 face verification."""

    similarity: float
    threshold: float
    is_match: bool
    model_name: str = "arcface_buffalo_l"
    embedding_1_time_ms: float = 0.0
    embedding_2_time_ms: float = 0.0
    total_time_ms: float = 0.0


class ArcFaceEngine:
    """
    ArcFace-based face recognition engine.

    Uses InsightFace's FaceAnalysis with the buffalo_l model pack for:
    - Face detection (SCRFD)
    - Face alignment (5-point landmark-based)
    - Embedding extraction (ArcFace, 512-d)

    The engine uses ONNX Runtime with CUDAExecutionProvider for GPU inference
    on the NVIDIA RTX 3050.

    Usage:
        engine = ArcFaceEngine()
        engine.load_model()
        result = engine.extract_embedding(image)
    """

    _instance: Optional["ArcFaceEngine"] = None
    _initialized: bool = False

    def __new__(cls, *args, **kwargs):
        """Singleton pattern — ensures only one model instance in memory."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        model_pack: str = "buffalo_l",
        det_size: Tuple[int, int] = (640, 640),
        det_thresh: float = 0.5,
        gpu_id: int = 0,
        enable_profiling: bool = False,
        profiling_dir: Optional[str] = None,
        diagnostic_dir: Optional[str] = None,
    ):
        """
        Initialize engine configuration (model is loaded lazily via load_model()).

        Args:
            model_pack: InsightFace model pack name. Default: buffalo_l.
            det_size: Detection input size (width, height).
            det_thresh: Minimum detection confidence threshold.
            gpu_id: CUDA device ID.
            enable_profiling: Enable opt-in ONNX Runtime profiling.
            profiling_dir: Directory for profiling output files.
            diagnostic_dir: Directory for opt-in aligned-face crops.
        """
        self._validate_detection_threshold(det_thresh)
        if self._initialized:
            return

        self.model_pack = model_pack
        self.det_size = det_size
        self.det_thresh = det_thresh
        self.gpu_id = gpu_id
        self.enable_profiling = enable_profiling
        self.profiling_dir = Path(profiling_dir) if profiling_dir else None
        self.diagnostic_dir = Path(diagnostic_dir) if diagnostic_dir else None
        self._app = None
        self._providers: List[str] = []
        self._model_loaded = False

    @staticmethod
    def _validate_detection_threshold(value: float) -> None:
        if not np.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(
                f"Detection threshold must be between 0.0 and 1.0, got {value}"
            )

    def load_model(self) -> None:
        """
        Load the InsightFace model pack with GPU acceleration.

        Downloads the model pack on first use (~300 MB for buffalo_l).
        The model is stored at ~/.insightface/models/<model_pack>/.

        Raises:
            ModelUnavailableError: If the model cannot be loaded.
        """
        if self._model_loaded:
            logger.info("ArcFace model already loaded, skipping.")
            return

        try:
            import insightface
            from insightface.app import FaceAnalysis

            logger.info(
                f"Loading InsightFace model pack: {self.model_pack} "
                f"(det_size={self.det_size}, gpu_id={self.gpu_id})"
            )

            # Set up NVIDIA DLL paths for ONNX Runtime CUDA provider
            self._configure_cuda_dll_paths()

            # Configure execution providers — prefer CUDA, fall back to CPU
            providers = [
                ("CUDAExecutionProvider", {"device_id": self.gpu_id}),
                "CPUExecutionProvider",
            ]
            session_options = self._create_session_options()

            self._app = FaceAnalysis(
                name=self.model_pack,
                providers=providers,
                **({"sess_options": session_options} if session_options else {}),
            )
            self._app.prepare(
                ctx_id=self.gpu_id,
                det_thresh=self.det_thresh,
                det_size=self.det_size,
            )

            # Record which providers are actually active
            # InsightFace wraps multiple ONNX sessions; check the recognition model
            self._providers = self._get_active_providers()

            self._model_loaded = True
            self._initialized = True

            logger.info(
                f"ArcFace model loaded successfully. "
                f"Active providers: {self._providers}"
            )

        except Exception as e:
            logger.error(f"Failed to load ArcFace model: {e}")
            raise ModelUnavailableError(
                f"Failed to load InsightFace model pack '{self.model_pack}': {e}"
            ) from e

    def _create_session_options(self):
        """Create profiling options only when explicitly requested."""
        if not self.enable_profiling:
            return None

        import onnxruntime

        profile_dir = self.profiling_dir or Path.cwd() / "logs" / "onnxruntime"
        profile_dir.mkdir(parents=True, exist_ok=True)
        options = onnxruntime.SessionOptions()
        options.enable_profiling = True
        options.profile_file_prefix = str(profile_dir / "arcface")
        return options

    def _configure_cuda_dll_paths(self) -> None:
        """
        Add NVIDIA pip package DLL directories to PATH.

        When CUDA Toolkit is not installed system-wide, ONNX Runtime needs
        the CUDA DLLs from pip-installed nvidia-* packages on PATH.
        """
        try:
            import nvidia
            nvidia_base = Path(nvidia.__file__).parent

            dll_dirs = []
            for subdir in nvidia_base.iterdir():
                bin_dir = subdir / "bin"
                if bin_dir.is_dir():
                    dll_dirs.append(str(bin_dir))

            if dll_dirs:
                current_path = os.environ.get("PATH", "")
                new_entries = os.pathsep.join(dll_dirs)
                os.environ["PATH"] = new_entries + os.pathsep + current_path
                logger.debug(f"Added {len(dll_dirs)} NVIDIA DLL dirs to PATH")

        except ImportError:
            logger.debug(
                "nvidia package not found; assuming system CUDA Toolkit is available"
            )
        except Exception as e:
            logger.warning(f"Could not configure NVIDIA DLL paths: {e}")

    def _get_active_providers(self) -> List[str]:
        """Inspect active execution providers from the loaded ONNX sessions."""
        providers = []
        try:
            if self._app and hasattr(self._app, "models"):
                for model in self._app.models.values():
                    if hasattr(model, "session"):
                        session_providers = model.session.get_providers()
                        for p in session_providers:
                            if p not in providers:
                                providers.append(p)
        except Exception:
            pass

        if not providers:
            # Fallback: check via onnxruntime directly
            try:
                import onnxruntime
                providers = onnxruntime.get_available_providers()
            except Exception:
                pass

        return providers

    def end_profiling(self) -> Dict[str, str]:
        """Finalize enabled session profiles and return their output paths."""
        if not self.enable_profiling or not self._app:
            return {}

        profile_paths: Dict[str, str] = {}
        for name, model in self._app.models.items():
            session = getattr(model, "session", None)
            if session is None or not hasattr(session, "end_profiling"):
                continue
            source_path = Path(session.end_profiling())
            destination = source_path.with_name(
                f"{source_path.stem}_{name}{source_path.suffix}"
            )
            if source_path != destination:
                shutil.copyfile(source_path, destination)
            profile_paths[name] = str(destination)
        return profile_paths

    @property
    def is_loaded(self) -> bool:
        """Whether the model has been loaded."""
        return self._model_loaded

    @property
    def is_gpu_active(self) -> bool:
        """Whether CUDAExecutionProvider is among the active providers."""
        return "CUDAExecutionProvider" in self._providers

    @property
    def active_providers(self) -> List[str]:
        """Return the list of active ONNX execution providers."""
        return list(self._providers)

    def load_image(self, image_path: str) -> np.ndarray:
        """
        Load an image from disk and validate it.

        Args:
            image_path: Path to the image file.

        Returns:
            BGR image as numpy array (OpenCV format, as expected by InsightFace).

        Raises:
            InvalidImageError: If the path doesn't exist or image is unreadable.
        """
        path = Path(image_path)

        if not path.exists():
            raise InvalidImageError(f"Image file not found: {image_path}")

        if not path.is_file():
            raise InvalidImageError(f"Path is not a file: {image_path}")

        # Check file extension
        valid_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}
        if path.suffix.lower() not in valid_extensions:
            raise InvalidImageError(
                f"Unsupported image format: {path.suffix}. "
                f"Supported: {', '.join(sorted(valid_extensions))}"
            )

        image = cv2.imread(str(path))

        if image is None:
            raise InvalidImageError(
                f"Failed to decode image file: {image_path}. "
                "File may be corrupt or in an unsupported format."
            )

        if image.size == 0:
            raise InvalidImageError(f"Image is empty (0 pixels): {image_path}")

        # Basic dimension sanity check
        h, w = image.shape[:2]
        if h < 10 or w < 10:
            raise InvalidImageError(
                f"Image too small ({w}x{h}). Minimum 10x10 pixels required."
            )

        logger.debug(f"Loaded image: {image_path} ({w}x{h}, {image.dtype})")
        return image

    def load_image_from_bytes(self, image_bytes: bytes) -> np.ndarray:
        """
        Load an image from raw bytes and validate it.

        Args:
            image_bytes: Raw image bytes (e.g., from file upload).

        Returns:
            BGR image as numpy array.

        Raises:
            InvalidImageError: If the bytes cannot be decoded as an image.
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

        logger.debug(f"Loaded image from bytes: {w}x{h}, {image.dtype}")
        return image

    def detect_faces(self, image: np.ndarray) -> List[DetectedFace]:
        """
        Detect all faces in the image.

        Args:
            image: BGR image as numpy array.

        Returns:
            List of DetectedFace objects.

        Raises:
            ModelUnavailableError: If the model is not loaded.
            FaceRecognitionError: If detection fails.
        """
        if not self._model_loaded or self._app is None:
            raise ModelUnavailableError(
                "Model not loaded. Call load_model() first."
            )

        try:
            faces = self._app.get(image)
        except Exception as e:
            raise FaceRecognitionError(
                f"Face detection failed: {e}"
            ) from e

        results = []
        for face in faces:
            bbox = face.bbox.astype(int).tolist()  # [x1, y1, x2, y2]
            det_score = float(face.det_score)
            landmarks = face.kps if hasattr(face, "kps") else None
            embedding = getattr(face, "normed_embedding", None)
            if embedding is not None:
                embedding = np.asarray(embedding, dtype=np.float32).flatten()

            results.append(
                DetectedFace(
                    bounding_box=bbox,
                    detection_score=det_score,
                    landmarks=landmarks,
                    embedding=embedding,
                )
            )

        return results

    def extract_embedding(
        self,
        image: np.ndarray,
        allow_multiple: bool = False,
        diagnostic_name: Optional[str] = None,
    ) -> EmbeddingResult:
        """
        Detect a face and extract its 512-d ArcFace embedding.

        Expects exactly one face in the image unless allow_multiple is True,
        in which case the face with the highest detection score is used.

        Args:
            image: BGR image as numpy array.
            allow_multiple: If True, use the highest-confidence face when
                            multiple are detected. If False, raise an error.
            diagnostic_name: Optional crop filename stem. Crops are saved only
                             when diagnostic_dir was explicitly configured.

        Returns:
            EmbeddingResult with the 512-d L2-normalized embedding.

        Raises:
            ModelUnavailableError: If the model is not loaded.
            FaceNotDetectedError: If no face is detected.
            MultipleFacesDetectedError: If multiple faces detected and
                                        allow_multiple is False.
            FaceRecognitionError: If embedding extraction fails.
        """
        if not self._model_loaded or self._app is None:
            raise ModelUnavailableError(
                "Model not loaded. Call load_model() first."
            )

        start_time = time.perf_counter()

        try:
            faces = self._app.get(image)
        except Exception as e:
            raise FaceRecognitionError(
                f"Face analysis failed: {e}"
            ) from e

        if len(faces) == 0:
            raise FaceNotDetectedError()

        if len(faces) > 1 and not allow_multiple:
            raise MultipleFacesDetectedError(face_count=len(faces))

        # Select the face with the highest detection score
        best_face = max(faces, key=lambda f: f.det_score)

        # Extract embedding — InsightFace computes it during .get()
        if not hasattr(best_face, "normed_embedding") or best_face.normed_embedding is None:
            # Fallback: check raw embedding
            if not hasattr(best_face, "embedding") or best_face.embedding is None:
                raise FaceRecognitionError(
                    "Face detected but embedding extraction failed. "
                    "The recognition model may not be available in the model pack."
                )
            # Manually normalize
            embedding = best_face.embedding
            norm = np.linalg.norm(embedding)
            if norm < 1e-10:
                raise FaceRecognitionError(
                    "Embedding has near-zero norm — model output is degenerate."
                )
            embedding = embedding / norm
        else:
            embedding = best_face.normed_embedding

        embedding = embedding.astype(np.float32).flatten()

        # Validate embedding
        if embedding.shape[0] != 512:
            raise FaceRecognitionError(
                f"Unexpected embedding dimension: {embedding.shape[0]}. "
                "Expected 512."
            )

        if not np.all(np.isfinite(embedding)):
            raise FaceRecognitionError(
                "Embedding contains non-finite values (NaN or Inf)."
            )

        # Verify L2 normalization (should be ~1.0)
        norm = float(np.linalg.norm(embedding))
        if abs(norm - 1.0) > 0.01:
            logger.warning(
                f"Embedding norm is {norm:.4f}, expected ~1.0. Re-normalizing."
            )
            embedding = embedding / norm

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        bbox = best_face.bbox.astype(int).tolist()
        det_score = float(best_face.det_score)
        aligned_face_path = self._save_aligned_face(
            image,
            best_face,
            diagnostic_name=diagnostic_name,
        )

        return EmbeddingResult(
            embedding=embedding,
            bounding_box=bbox,
            detection_score=det_score,
            model_name=f"arcface_{self.model_pack}",
            inference_time_ms=round(elapsed_ms, 2),
            aligned_face_path=aligned_face_path,
        )

    def _save_aligned_face(
        self,
        image: np.ndarray,
        face,
        diagnostic_name: Optional[str],
    ) -> Optional[str]:
        """Save the same 112x112 landmark crop used by ArcFace, when enabled."""
        if self.diagnostic_dir is None:
            return None
        if not hasattr(face, "kps") or face.kps is None:
            raise FaceRecognitionError(
                "Cannot save aligned diagnostic crop: facial landmarks unavailable."
            )

        try:
            from insightface.utils import face_align

            self.diagnostic_dir.mkdir(parents=True, exist_ok=True)
            stem = Path(diagnostic_name or "face").stem
            crop_path = self.diagnostic_dir / f"{stem}_aligned.jpg"
            aligned_face = face_align.norm_crop(
                image,
                landmark=face.kps,
                image_size=112,
            )
            if not cv2.imwrite(str(crop_path), aligned_face):
                raise FaceRecognitionError(
                    f"Failed to write aligned diagnostic crop: {crop_path}"
                )
            return str(crop_path)
        except FaceRecognitionError:
            raise
        except Exception as exc:
            raise FaceRecognitionError(
                f"Failed to create aligned diagnostic crop: {exc}"
            ) from exc

    def extract_from_path(
        self,
        image_path: str,
        allow_multiple: bool = False,
    ) -> EmbeddingResult:
        """
        Convenience method: load image from path and extract embedding.

        Args:
            image_path: Path to the image file.
            allow_multiple: If True, use highest-confidence face when multiple detected.

        Returns:
            EmbeddingResult with the 512-d L2-normalized embedding.
        """
        image = self.load_image(image_path)
        return self.extract_embedding(
            image,
            allow_multiple=allow_multiple,
            diagnostic_name=Path(image_path).stem,
        )

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None
        cls._initialized = False
