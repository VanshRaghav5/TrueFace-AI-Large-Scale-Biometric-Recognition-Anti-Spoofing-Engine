"""Run the standalone TrueFace AI-X webcam recognition prototype."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path

import cv2

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.app.face.recognition import ArcFaceEngine
from backend.app.face.recognition.exceptions import ModelUnavailableError
from backend.app.face.liveness import AntiSpoofMn3Config, AntiSpoofMn3Engine
from backend.realtime.camera import Camera, CameraError
from backend.realtime.config import RealtimeConfig
from backend.realtime.identity_gallery import IdentityGallery
from backend.realtime.realtime_recognition import RealtimeRecognizer


DEFAULT_ENROLLMENT_DIR = REPOSITORY_ROOT / "Trueface_Dataset"
DEFAULT_PAD_MODEL = REPOSITORY_ROOT / "models" / "liveness" / "anti-spoof-mn3.onnx"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def load_manifest(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    identities = data.get("identities")
    if not isinstance(identities, list):
        raise ValueError("Manifest must contain an 'identities' list")
    return identities


def build_dataset_manifest(dataset_dir: Path) -> list[dict]:
    """Build enrollment groups from identity subfolders or flat filename prefixes.

    Flat files must use ``identity_<sample>.<extension>`` naming, for example
    ``person_a_1.jpg`` and ``person_a_2.jpg``.
    """
    if not dataset_dir.is_dir():
        raise ValueError(f"Enrollment dataset directory does not exist: {dataset_dir}")

    files = sorted(
        path
        for path in dataset_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if not files:
        raise ValueError(f"No supported enrollment images found in {dataset_dir}")

    grouped: dict[str, list[str]] = {}
    for path in files:
        relative_parent = path.parent.relative_to(dataset_dir)
        if relative_parent != Path("."):
            identity_id = str(relative_parent).replace("\\", "/")
        else:
            match = re.match(r"^(?P<identity>.+)_(?P<sample>\d+)$", path.stem)
            if match is None:
                raise ValueError(
                    "Flat enrollment files must use identity_<sample> naming; "
                    f"could not infer identity from {path.name}"
                )
            identity_id = match.group("identity")
        grouped.setdefault(identity_id, []).append(str(path))

    return [
        {
            "id": identity_id,
            "name": identity_id.replace("_", " ").title(),
            "images": image_paths,
        }
        for identity_id, image_paths in sorted(grouped.items())
    ]


def build_gallery(
    recognizer: RealtimeRecognizer,
    manifest_path: Path,
    consent_confirmed: bool,
) -> list[dict]:
    failures = []
    for identity in load_manifest(manifest_path):
        failures.extend(
            recognizer.enroll_images(
                identity_id=str(identity["id"]),
                display_name=str(identity["name"]),
                image_paths=identity["images"],
                consent_confirmed=consent_confirmed,
            )
        )
    return [failure.__dict__ for failure in failures]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--manifest", type=Path)
    source.add_argument(
        "--dataset-dir",
        type=Path,
        default=DEFAULT_ENROLLMENT_DIR,
        help=f"Enrollment folder (default: {DEFAULT_ENROLLMENT_DIR})",
    )
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--threshold", type=float, default=0.75)
    parser.add_argument("--consent-confirmed", action="store_true")
    parser.add_argument(
        "--pad-model",
        type=Path,
        default=DEFAULT_PAD_MODEL,
        help="Authorized anti-spoof-mn3 ONNX path; absent means recognition-only mode",
    )
    parser.add_argument(
        "--pad-threshold",
        type=float,
        default=None,
        help="Validation-selected PAD real-score threshold",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    config = RealtimeConfig(
        camera_index=args.camera_index,
        camera_width=args.width,
        camera_height=args.height,
        similarity_threshold=args.threshold,
    )
    engine = ArcFaceEngine()
    try:
        engine.load_model()
    except ModelUnavailableError as exc:
        print(f"ArcFace model unavailable: {exc}", file=sys.stderr)
        return 2
    pad_engine = None
    if args.pad_model.is_file():
        try:
            pad_engine = AntiSpoofMn3Engine(
                AntiSpoofMn3Config(model_path=args.pad_model)
            )
            pad_engine.load_model()
            print(
                "PAD enabled: anti-spoof-mn3 "
                f"({pad_engine.execution_provider or 'unknown'} provider)"
            )
        except Exception as exc:
            print(f"PAD model unavailable: {exc}", file=sys.stderr)
            return 2
    else:
        print("PAD unavailable: running recognition-only mode.")
    gallery = IdentityGallery(config.similarity_threshold)
    recognizer = RealtimeRecognizer(
        engine,
        gallery,
        config,
        pad_adapter=pad_engine,
        pad_threshold=args.pad_threshold,
    )
    try:
        if not args.consent_confirmed:
            raise PermissionError(
                "Enrollment requires --consent-confirmed for the supplied people"
            )
        if args.manifest is not None:
            failures = build_gallery(
                recognizer, args.manifest, args.consent_confirmed
            )
        else:
            identities = build_dataset_manifest(args.dataset_dir)
            failures = []
            for identity in identities:
                failures.extend(
                    recognizer.enroll_images(
                        identity["id"],
                        identity["name"],
                        identity["images"],
                        consent_confirmed=True,
                    )
                )
    except Exception as exc:
        print(f"Enrollment failed: {exc}", file=sys.stderr)
        return 2
    if failures:
        print(f"Rejected enrollment images: {len(failures)}", file=sys.stderr)
    if gallery.identity_count == 0:
        print("No identities were enrolled; refusing to start camera.", file=sys.stderr)
        return 2

    camera = Camera(config.camera_index, config.camera_width, config.camera_height)
    try:
        camera.open()
        frame_count = 0
        started = time.perf_counter()
        force_refresh = False
        while True:
            frame = camera.read()
            frame_count += 1
            results = recognizer.process_frame(frame, force_recognition=force_refresh)
            force_refresh = False
            elapsed = max(time.perf_counter() - started, 1e-9)
            output = recognizer.draw(
                frame,
                results,
                frame_count / elapsed,
                engine.is_gpu_active,
            )
            cv2.imshow(config.window_name, output)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q")):
                break
            if key in (ord("r"), ord("R")):
                force_refresh = True
            if key in (ord("h"), ord("H")):
                print("Controls: Q quit, R refresh visible faces, H show this help")
    except CameraError as exc:
        print(f"Camera error: {exc}", file=sys.stderr)
        return 3
    finally:
        camera.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
