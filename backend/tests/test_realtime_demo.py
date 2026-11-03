from pathlib import Path

import numpy as np
import pytest

from backend.realtime.config import RealtimeConfig
from backend.realtime.identity_gallery import GalleryMatch, IdentityGallery
from backend.realtime.realtime_recognition import FaceRecognitionResult, RealtimeRecognizer
from backend.realtime_demo import build_dataset_manifest


def test_flat_dataset_groups_identity_prefixes(tmp_path):
    for name in ("person_a_1.jpg", "person_a_2.jpg", "person_b_1.jpg"):
        (tmp_path / name).write_bytes(b"fixture")

    manifest = build_dataset_manifest(tmp_path)

    assert manifest == [
        {
            "id": "person_a",
            "name": "Person A",
            "images": [
                str(tmp_path / "person_a_1.jpg"),
                str(tmp_path / "person_a_2.jpg"),
            ],
        },
        {
            "id": "person_b",
            "name": "Person B",
            "images": [str(tmp_path / "person_b_1.jpg")],
        },
    ]


def test_dataset_subfolders_define_identities(tmp_path):
    path = tmp_path / "alice" / "sample.jpg"
    path.parent.mkdir()
    path.write_bytes(b"fixture")

    manifest = build_dataset_manifest(tmp_path)

    assert manifest[0]["id"] == "alice"
    assert manifest[0]["images"] == [str(path)]


def test_flat_dataset_requires_identity_sample_naming(tmp_path):
    (tmp_path / "unknown.jpg").write_bytes(b"fixture")

    with pytest.raises(ValueError, match="identity_<sample>"):
        build_dataset_manifest(tmp_path)


def test_draw_includes_track_and_processing_latency():
    recognizer = RealtimeRecognizer(
        engine=object(),
        gallery=IdentityGallery(),
        config=RealtimeConfig(),
    )
    result = FaceRecognitionResult(
        bounding_box=[10, 10, 40, 40],
        match=GalleryMatch("person_a", "Person A", 0.9, True),
        detection_score=0.99,
        processing_time_ms=12.34,
        track_id=7,
    )

    output = recognizer.draw(
        np.zeros((80, 80, 3), dtype=np.uint8),
        [result],
        fps=30.0,
        gpu_active=True,
    )

    assert output.shape == (80, 80, 3)
