import numpy as np
import pytest

from backend.app.face.detection.scrfd import distance2bbox, distance2kps, nms


def test_distance2bbox():
    points = np.array([[100, 100], [200, 200]], dtype=np.float32)
    distance = np.array([[10, 20, 30, 40], [15, 25, 35, 45]], dtype=np.float32)
    bboxes = distance2bbox(points, distance)
    assert bboxes.shape == (2, 4)
    # [x - l, y - t, x + r, y + b]
    assert np.allclose(bboxes[0], [90, 80, 130, 140])
    assert np.allclose(bboxes[1], [185, 175, 235, 245])


def test_distance2bbox_clamping():
    points = np.array([[10, 10]], dtype=np.float32)
    distance = np.array([[50, 50, 100, 100]], dtype=np.float32)
    bboxes = distance2bbox(points, distance, max_shape=(80, 80))
    # Clamped to [0, 80]
    assert bboxes[0, 0] == 0  # 10 - 50 clamped to 0
    assert bboxes[0, 1] == 0  # 10 - 50 clamped to 0
    assert bboxes[0, 2] == 80  # 10 + 100 clamped to 80
    assert bboxes[0, 3] == 80  # 10 + 100 clamped to 80


def test_distance2kps():
    points = np.array([[100, 100]], dtype=np.float32)
    distance = np.tile([10, 15], 5).reshape(1, 10).astype(np.float32)
    kps = distance2kps(points, distance)
    assert kps.shape == (1, 10)
    kps_reshaped = kps.reshape((kps.shape[0], -1, 2))
    assert kps_reshaped.shape == (1, 5, 2)
    for i in range(5):
        assert np.allclose(kps_reshaped[0, i], [110, 115])


def test_nms_suppression():
    dets = np.array(
        [
            [10, 10, 50, 50, 0.9],
            [12, 12, 48, 48, 0.8],  # Overlapping significantly with first
            [100, 100, 150, 150, 0.85],  # Separate detection
        ],
        dtype=np.float32,
    )
    keep = nms(dets, thresh=0.4)
    assert keep == [0, 2]


def test_nms_empty():
    dets = np.zeros((0, 5), dtype=np.float32)
    keep = nms(dets)
    assert keep == []
