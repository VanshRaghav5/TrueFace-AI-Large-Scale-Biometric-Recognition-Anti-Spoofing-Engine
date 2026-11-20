"""
SCRFD Face Detector — InsightFace Native ONNX Implementation.

Sample and Computation Redistribution for Face Detection (SCRFD)
with multi-stride feature pyramid anchor decoding, 5-point facial landmark regression,
and Non-Maximum Suppression (NMS).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def softmax(z: np.ndarray) -> np.ndarray:
    assert len(z.shape) == 2
    s = np.max(z, axis=1, keepdims=True)
    e_x = np.exp(z - s)
    return e_x / np.sum(e_x, axis=1, keepdims=True)


def distance2bbox(points: np.ndarray, distance: np.ndarray, max_shape: Optional[Tuple[int, int]] = None) -> np.ndarray:
    """
    Decode distance prediction to bounding box.

    Args:
        points: Shape (n, 2), [x, y].
        distance: Distance from anchor point to 4 boundaries [l, t, r, b].
        max_shape: (height, width) clamp bounds.

    Returns:
        Decoded bounding boxes [x1, y1, x2, y2].
    """
    x1 = points[:, 0] - distance[:, 0]
    y1 = points[:, 1] - distance[:, 1]
    x2 = points[:, 0] + distance[:, 2]
    y2 = points[:, 1] + distance[:, 3]
    if max_shape is not None:
        x1 = np.clip(x1, 0, max_shape[1])
        y1 = np.clip(y1, 0, max_shape[0])
        x2 = np.clip(x2, 0, max_shape[1])
        y2 = np.clip(y2, 0, max_shape[0])
    return np.stack([x1, y1, x2, y2], axis=-1)


def distance2kps(points: np.ndarray, distance: np.ndarray, max_shape: Optional[Tuple[int, int]] = None) -> np.ndarray:
    """
    Decode distance prediction to 5-point facial keypoints.

    Args:
        points: Shape (n, 2), [x, y].
        distance: Distance predictions for keypoints (n, 10).
        max_shape: (height, width) clamp bounds.

    Returns:
        Decoded keypoints (n, 5, 2).
    """
    preds = []
    for i in range(0, distance.shape[1], 2):
        px = points[:, i % 2] + distance[:, i]
        py = points[:, (i + 1) % 2] + distance[:, i + 1]
        if max_shape is not None:
            px = np.clip(px, 0, max_shape[1])
            py = np.clip(py, 0, max_shape[0])
        preds.append(px)
        preds.append(py)
    return np.stack(preds, axis=-1)


def nms(dets: np.ndarray, thresh: float = 0.4) -> List[int]:
    """
    Standard greedy Non-Maximum Suppression (NMS).

    Args:
        dets: Detection array with shape (N, 5): [x1, y1, x2, y2, score].
        thresh: IoU overlap threshold.

    Returns:
        List of selected indices.
    """
    if dets.shape[0] == 0:
        return []

    x1 = dets[:, 0]
    y1 = dets[:, 1]
    x2 = dets[:, 2]
    y2 = dets[:, 3]
    scores = dets[:, 4]

    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        ovr = inter / (areas[i] + areas[order[1:]] - inter)

        inds = np.where(ovr <= thresh)[0]
        order = order[inds + 1]

    return keep


class SCRFD:
    """
    InsightFace SCRFD detector engine using ONNX Runtime.
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
        self.taskname = "detection"
        self.batched = False
        self.center_cache: Dict[Tuple[int, int, int], np.ndarray] = {}
        self.nms_thresh = 0.4
        self.det_thresh = 0.5
        self.input_mean = 127.5
        self.input_std = 128.0

        if self.session is None:
            if self.model_file is None or not Path(self.model_file).exists():
                raise FileNotFoundError(f"SCRFD model file not found: {self.model_file}")

            import onnxruntime
            if providers is None:
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]

            self.session = onnxruntime.InferenceSession(
                self.model_file,
                sess_options=sess_options,
                providers=providers,
            )

        self._init_vars()

    def _init_vars(self):
        input_cfg = self.session.get_inputs()[0]
        input_shape = input_cfg.shape
        if isinstance(input_shape[2], str):
            self.input_size = None
        else:
            self.input_size = tuple(input_shape[2:4][::-1])

        self.input_name = input_cfg.name
        self.input_shape = input_shape
        outputs = self.session.get_outputs()
        if len(outputs[0].shape) == 3:
            self.batched = True
        self.output_names = [o.name for o in outputs]

        self.use_kps = False
        self._anchor_ratio = 1.0
        self._num_anchors = 1

        n_outputs = len(outputs)
        if n_outputs == 6:
            self.fmc = 3
            self._feat_stride_fpn = [8, 16, 32]
            self._num_anchors = 2
        elif n_outputs == 9:
            self.fmc = 3
            self._feat_stride_fpn = [8, 16, 32]
            self._num_anchors = 2
            self.use_kps = True
        elif n_outputs == 10:
            self.fmc = 5
            self._feat_stride_fpn = [8, 16, 32, 64, 128]
            self._num_anchors = 1
        elif n_outputs == 15:
            self.fmc = 5
            self._feat_stride_fpn = [8, 16, 32, 64, 128]
            self._num_anchors = 1
            self.use_kps = True

    def prepare(self, ctx_id: int = 0, **kwargs):
        if ctx_id < 0:
            self.session.set_providers(["CPUExecutionProvider"])
        if "nms_thresh" in kwargs and kwargs["nms_thresh"] is not None:
            self.nms_thresh = kwargs["nms_thresh"]
        if "det_thresh" in kwargs and kwargs["det_thresh"] is not None:
            self.det_thresh = kwargs["det_thresh"]
        if "input_size" in kwargs and kwargs["input_size"] is not None:
            self.input_size = kwargs["input_size"]

    def forward(self, img: np.ndarray, threshold: float):
        scores_list = []
        bboxes_list = []
        kpss_list = []
        input_size = tuple(img.shape[0:2][::-1])

        blob = cv2.dnn.blobFromImage(
            img,
            1.0 / self.input_std,
            input_size,
            (self.input_mean, self.input_mean, self.input_mean),
            swapRB=True,
        )
        net_outs = self.session.run(self.output_names, {self.input_name: blob})

        input_height = blob.shape[2]
        input_width = blob.shape[3]
        fmc = self.fmc

        for idx, stride in enumerate(self._feat_stride_fpn):
            if self.batched:
                scores = net_outs[idx][0]
                bbox_preds = net_outs[idx + fmc][0] * stride
                if self.use_kps:
                    kps_preds = net_outs[idx + fmc * 2][0] * stride
            else:
                scores = net_outs[idx]
                bbox_preds = net_outs[idx + fmc] * stride
                if self.use_kps:
                    kps_preds = net_outs[idx + fmc * 2] * stride

            height = input_height // stride
            width = input_width // stride
            key = (height, width, stride)
            if key in self.center_cache:
                anchor_centers = self.center_cache[key]
            else:
                anchor_centers = np.stack(
                    np.mgrid[:height, :width][::-1], axis=-1
                ).astype(np.float32)
                anchor_centers = (anchor_centers * stride).reshape((-1, 2))
                if self._num_anchors > 1:
                    anchor_centers = np.stack(
                        [anchor_centers] * self._num_anchors, axis=1
                    ).reshape((-1, 2))
                if len(self.center_cache) < 100:
                    self.center_cache[key] = anchor_centers

            pos_inds = np.where(scores >= threshold)[0]
            bboxes = distance2bbox(anchor_centers, bbox_preds)
            pos_scores = scores[pos_inds]
            pos_bboxes = bboxes[pos_inds]
            scores_list.append(pos_scores)
            bboxes_list.append(pos_bboxes)

            if self.use_kps:
                kpss = distance2kps(anchor_centers, kps_preds)
                kpss = kpss.reshape((kpss.shape[0], -1, 2))
                pos_kpss = kpss[pos_inds]
                kpss_list.append(pos_kpss)

        return scores_list, bboxes_list, kpss_list

    def detect(
        self,
        img: np.ndarray,
        input_size: Optional[Tuple[int, int]] = None,
        thresh: Optional[float] = None,
        max_num: int = 0,
        metric: str = "default",
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Detect faces in image.

        Args:
            img: BGR image.
            input_size: Detection resolution (width, height), e.g. (640, 640).
            thresh: Detection confidence threshold.
            max_num: Maximum number of faces to return (0 for all).
            metric: Selection metric ('max' for area, 'default' for centered-area).

        Returns:
            Tuple of (dets, kpss):
                dets: (N, 5) float32 array: [x1, y1, x2, y2, score].
                kpss: (N, 5, 2) float32 array: 5 keypoints per face or None.
        """
        assert input_size is not None or self.input_size is not None
        input_size = self.input_size if input_size is None else input_size

        im_ratio = float(img.shape[0]) / img.shape[1]
        model_ratio = float(input_size[1]) / input_size[0]

        if im_ratio > model_ratio:
            new_height = input_size[1]
            new_width = int(new_height / im_ratio)
        else:
            new_width = input_size[0]
            new_height = int(new_width * im_ratio)

        det_scale = float(new_height) / img.shape[0]
        resized_img = cv2.resize(img, (new_width, new_height))
        det_img = np.zeros((input_size[1], input_size[0], 3), dtype=np.uint8)
        det_img[:new_height, :new_width, :] = resized_img
        det_thresh = thresh if thresh is not None else self.det_thresh

        scores_list, bboxes_list, kpss_list = self.forward(det_img, det_thresh)

        if not scores_list or sum(len(s) for s in scores_list) == 0:
            empty_det = np.zeros((0, 5), dtype=np.float32)
            empty_kps = np.zeros((0, 5, 2), dtype=np.float32) if self.use_kps else None
            return empty_det, empty_kps

        scores = np.vstack(scores_list)
        scores_ravel = scores.ravel()
        order = scores_ravel.argsort()[::-1]
        bboxes = np.vstack(bboxes_list) / det_scale

        if self.use_kps:
            kpss = np.vstack(kpss_list) / det_scale
        else:
            kpss = None

        pre_det = np.hstack((bboxes, scores)).astype(np.float32, copy=False)
        pre_det = pre_det[order, :]
        keep = nms(pre_det, thresh=self.nms_thresh)
        det = pre_det[keep, :]

        if self.use_kps and kpss is not None:
            kpss = kpss[order, :, :]
            kpss = kpss[keep, :, :]

        if max_num > 0 and det.shape[0] > max_num:
            area = (det[:, 2] - det[:, 0]) * (det[:, 3] - det[:, 1])
            img_center = img.shape[0] // 2, img.shape[1] // 2
            offsets = np.vstack(
                [
                    (det[:, 0] + det[:, 2]) / 2 - img_center[1],
                    (det[:, 1] + det[:, 3]) / 2 - img_center[0],
                ]
            )
            offset_dist_squared = np.sum(np.power(offsets, 2.0), 0)
            if metric == "max":
                values = area
            else:
                values = area - offset_dist_squared * 2.0
            bindex = np.argsort(values)[::-1]
            bindex = bindex[0:max_num]
            det = det[bindex, :]
            if kpss is not None:
                kpss = kpss[bindex, :]

        return det, kpss

