"""
ArcFace ONNX Recognizer — InsightFace Native ONNX Implementation.

Extracts 512-dimensional L2-normalized facial embeddings using ArcFace
backbone networks (e.g. ResNet-50 / w600k_r50.onnx) with ONNX Runtime.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Sequence, Tuple, Union

import cv2
import numpy as np

from ..alignment.face_align import norm_crop

logger = logging.getLogger(__name__)


class ArcFaceONNX:
    """
    ArcFace ONNX recognition engine.
    """

    def __init__(
        self,
        model_file: Optional[Union[str, Path]] = None,
        session=None,
        providers: Optional[Sequence[Union[str, Tuple[str, dict]]]] = None,
        sess_options=None,
    ):
        self.model_file = str(model_file) if model_file else None
        self.session = session
        self.taskname = "recognition"
        self.input_mean = 127.5
        self.input_std = 127.5

        if self.session is None:
            if self.model_file is None or not Path(self.model_file).exists():
                raise FileNotFoundError(f"ArcFace model file not found: {self.model_file}")

            import onnxruntime
            if providers is None:
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]

            self.session = onnxruntime.InferenceSession(
                self.model_file,
                sess_options=sess_options,
                providers=providers,
            )

        input_cfg = self.session.get_inputs()[0]
        input_shape = input_cfg.shape
        self.input_name = input_cfg.name
        self.input_size = tuple(input_shape[2:4][::-1]) if len(input_shape) >= 4 and isinstance(input_shape[2], int) else (112, 112)
        self.input_shape = input_shape

        outputs = self.session.get_outputs()
        self.output_names = [o.name for o in outputs]
        self.output_shape = outputs[0].shape

    def prepare(self, ctx_id: int = 0, **kwargs):
        if ctx_id < 0:
            self.session.set_providers(["CPUExecutionProvider"])

    def get_feat(self, imgs: Union[np.ndarray, Sequence[np.ndarray]]) -> np.ndarray:
        """
        Extract raw feature embeddings from aligned face images.

        Args:
            imgs: Single or list of aligned (112, 112, 3) BGR face images.

        Returns:
            Embeddings array (N, 512).
        """
        if not isinstance(imgs, (list, tuple)):
            imgs = [imgs]

        blob = cv2.dnn.blobFromImages(
            imgs,
            1.0 / self.input_std,
            self.input_size,
            (self.input_mean, self.input_mean, self.input_mean),
            swapRB=True,
        ).astype(np.float32)

        net_out = self.session.run(self.output_names, {self.input_name: blob})[0]
        return net_out

    def get(self, img: np.ndarray, kps: np.ndarray) -> np.ndarray:
        """
        Align face by 5-point landmarks and extract 512-d normalized embedding.

        Args:
            img: BGR image.
            kps: 5-point facial landmarks (5, 2).

        Returns:
            512-dimensional L2-normalized float32 numpy vector.
        """
        aligned_face = norm_crop(img, landmark=kps, image_size=self.input_size[0])
        raw_feat = self.get_feat(aligned_face).flatten()
        norm = np.linalg.norm(raw_feat)
        if norm > 1e-10:
            normed_feat = raw_feat / norm
        else:
            normed_feat = raw_feat
        return normed_feat.astype(np.float32)

    @staticmethod
    def compute_sim(feat1: np.ndarray, feat2: np.ndarray) -> float:
        """
        Compute cosine similarity between two feature vectors.
        """
        f1 = feat1.ravel().astype(np.float64)
        f2 = feat2.ravel().astype(np.float64)
        norm1 = np.linalg.norm(f1)
        norm2 = np.linalg.norm(f2)
        if norm1 <= 1e-10 or norm2 <= 1e-10:
            return 0.0
        return float(np.dot(f1, f2) / (norm1 * norm2))

