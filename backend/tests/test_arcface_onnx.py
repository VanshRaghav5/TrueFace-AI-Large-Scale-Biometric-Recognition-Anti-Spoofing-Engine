import numpy as np
import pytest

from backend.app.face.recognition.arcface_onnx import ArcFaceONNX


def test_arcface_onnx_compute_sim_identical():
    v = np.ones(512, dtype=np.float32)
    sim = ArcFaceONNX.compute_sim(v, v)
    assert np.isclose(sim, 1.0)


def test_arcface_onnx_compute_sim_orthogonal():
    v1 = np.zeros(512, dtype=np.float32)
    v1[0] = 1.0
    v2 = np.zeros(512, dtype=np.float32)
    v2[1] = 1.0
    sim = ArcFaceONNX.compute_sim(v1, v2)
    assert np.isclose(sim, 0.0)


def test_arcface_onnx_compute_sim_zero_norm():
    v1 = np.zeros(512, dtype=np.float32)
    v2 = np.ones(512, dtype=np.float32)
    sim = ArcFaceONNX.compute_sim(v1, v2)
    assert sim == 0.0

