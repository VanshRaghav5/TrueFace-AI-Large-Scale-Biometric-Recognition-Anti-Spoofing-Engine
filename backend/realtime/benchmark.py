"""Measured realtime recognition benchmark using local enrollment images."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.app.face.recognition import ArcFaceEngine
from backend.realtime.camera import Camera
from backend.realtime.config import RealtimeConfig
from backend.realtime.identity_gallery import IdentityGallery
from backend.realtime.realtime_recognition import RealtimeRecognizer
from backend.realtime_demo import build_dataset_manifest


def percentile(values: list[float], value: float) -> float:
    return float(np.percentile(values, value)) if values else 0.0


def _gpu_metadata() -> dict:
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return {}
    return {"nvidia_smi": completed.stdout.strip()}


def run(duration_seconds: float, dataset_dir: Path, camera_index: int) -> dict:
    engine = ArcFaceEngine()
    initialization_started = time.perf_counter()
    engine.load_model()
    initialization_ms = (time.perf_counter() - initialization_started) * 1000
    config = RealtimeConfig(camera_index=camera_index, confirmation_frames=1)
    gallery = IdentityGallery(config.similarity_threshold)
    recognizer = RealtimeRecognizer(engine, gallery, config)
    enrollment_failures = []
    for identity in build_dataset_manifest(dataset_dir):
        enrollment_failures.extend(
            recognizer.enroll_images(
                identity["id"],
                identity["name"],
                identity["images"],
                consent_confirmed=True,
            )
        )

    camera = Camera(camera_index, config.camera_width, config.camera_height)
    camera.open()
    frame_times: list[float] = []
    recognition_times: list[float] = []
    frames = 0
    faces = 0
    started = time.perf_counter()
    try:
        while time.perf_counter() - started < duration_seconds:
            frame = camera.read()
            frame_started = time.perf_counter()
            results = recognizer.process_frame(frame, force_recognition=True)
            frame_times.append((time.perf_counter() - frame_started) * 1000)
            recognition_times.extend(result.processing_time_ms for result in results)
            frames += 1
            faces += len(results)
    finally:
        camera.release()
    elapsed = max(time.perf_counter() - started, 1e-9)
    return {
        "duration_seconds": round(elapsed, 3),
        "frames": frames,
        "faces_processed": faces,
        "average_fps": round(frames / elapsed, 3),
        "minimum_fps_observed": round(1000.0 / max(frame_times), 3) if frame_times else 0.0,
        "average_frame_processing_ms": round(float(np.mean(frame_times)), 3) if frame_times else 0.0,
        "p95_frame_processing_ms": round(percentile(frame_times, 95), 3),
        "average_embedding_and_gallery_ms": round(float(np.mean(recognition_times)), 3)
        if recognition_times else 0.0,
        "model_initialization_ms": round(initialization_ms, 3),
        "enrolled_identities": gallery.identity_count,
        "enrollment_templates": gallery.template_count,
        "enrollment_failures": len(enrollment_failures),
        "providers": engine.active_providers,
        "cuda_active": engine.is_gpu_active,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "gpu": _gpu_metadata(),
        },
        "timing_scope": {
            "frame_processing": "camera read excluded; detection, tracking, and cached recognition included",
            "embedding_and_gallery": "recognition result timing; includes gallery matching and excludes detection",
            "warmup": "not separately excluded by this camera benchmark",
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = run(args.duration, args.dataset_dir, args.camera_index)
    encoded = json.dumps(report, indent=2)
    print(encoded)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded + "\n", encoding="utf-8")
