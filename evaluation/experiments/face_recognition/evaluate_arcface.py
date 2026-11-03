"""Reproducible, identity-disjoint ArcFace verification evaluation.

Dataset files, embeddings, ROC outputs, and reports are written outside the
repository by default. The expected dataset layout is:

    dataset_root/<identity>/<image files>

The evaluator does not download datasets and does not treat failed image
processing as an impostor pair.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import subprocess
import time
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from sklearn.metrics import roc_curve

try:
    from .metrics import evaluate_scores, select_threshold
except ImportError:
    from metrics import evaluate_scores, select_threshold


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
DEFAULT_THRESHOLD = 0.75


@dataclass(frozen=True)
class ImageRecord:
    identity: str
    path: str


@dataclass(frozen=True)
class PairRecord:
    first: str
    second: str
    identity: str
    label: int


def discover_images(dataset_root: Path) -> list[ImageRecord]:
    """Discover images whose immediate parent directory is the identity."""
    if not dataset_root.is_dir():
        raise ValueError(f"Dataset directory does not exist: {dataset_root}")
    records = [
        ImageRecord(path.parent.name, str(path.resolve()))
        for path in dataset_root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    ]
    records.sort(key=lambda item: (item.identity, item.path))
    if not records:
        raise ValueError(f"No supported images found below {dataset_root}")
    return records


def split_identities(
    identities: Iterable[str],
    seed: int = 42,
    train_fraction: float = 0.6,
    validation_fraction: float = 0.2,
) -> dict[str, list[str]]:
    """Split identities, not images, so identities cannot cross partitions."""
    names = sorted(set(identities))
    if len(names) < 3:
        raise ValueError(
            "At least three identities are required for train/validation/test "
            "splits; provide a benchmark dataset rather than a two-person demo set."
        )
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("Split fractions must be between zero and one")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("Train and validation fractions must leave test identities")

    rng = np.random.default_rng(seed)
    shuffled = list(np.asarray(names)[rng.permutation(len(names))])
    train_count = max(1, int(len(names) * train_fraction))
    validation_count = max(1, int(len(names) * validation_fraction))
    if train_count + validation_count >= len(names):
        validation_count = 1
        train_count = len(names) - 2
    return {
        "train": shuffled[:train_count],
        "validation": shuffled[train_count : train_count + validation_count],
        "test": shuffled[train_count + validation_count :],
    }


def _records_for_split(
    records: Sequence[ImageRecord], identities: Sequence[str]
) -> list[ImageRecord]:
    allowed = set(identities)
    return [record for record in records if record.identity in allowed]


def _validate_pair_capacity(
    records: Sequence[ImageRecord], identities: Sequence[str], split_name: str
) -> None:
    split_records = _records_for_split(records, identities)
    by_identity: dict[str, int] = {}
    for record in split_records:
        by_identity[record.identity] = by_identity.get(record.identity, 0) + 1
    if len(by_identity) < 2:
        raise ValueError(
            f"{split_name} split needs at least two identities for impostor pairs"
        )
    if any(count < 2 for count in by_identity.values()):
        raise ValueError(
            f"{split_name} split needs at least two images per identity for genuine pairs"
        )


def generate_pairs(
    records: Sequence[ImageRecord],
    identities: Sequence[str],
    *,
    seed: int = 42,
    max_genuine_per_identity: int | None = None,
    max_impostor: int | None = None,
) -> list[PairRecord]:
    """Generate deterministic genuine and impostor pairs for one split."""
    split_records = _records_for_split(records, identities)
    by_identity: dict[str, list[str]] = {}
    for record in split_records:
        by_identity.setdefault(record.identity, []).append(record.path)
    rng = np.random.default_rng(seed)

    genuine: list[PairRecord] = []
    for identity in sorted(by_identity):
        candidates = list(combinations(sorted(by_identity[identity]), 2))
        if max_genuine_per_identity is not None:
            if max_genuine_per_identity < 1:
                raise ValueError("max_genuine_per_identity must be positive")
            rng.shuffle(candidates)
            candidates = candidates[:max_genuine_per_identity]
        genuine.extend(
            PairRecord(first, second, identity, 1)
            for first, second in sorted(candidates)
        )

    impostor_candidates = [
        PairRecord(first, second, "", 0)
        for left, right in combinations(sorted(by_identity), 2)
        for first in by_identity[left]
        for second in by_identity[right]
    ]
    rng.shuffle(impostor_candidates)
    if max_impostor is not None:
        if max_impostor < 1:
            raise ValueError("max_impostor must be positive")
        impostor_candidates = impostor_candidates[:max_impostor]
    return genuine + sorted(impostor_candidates, key=lambda pair: (pair.first, pair.second))


def dataset_manifest(records: Sequence[ImageRecord]) -> str:
    payload = "\n".join(
        f"{record.identity}\t{record.path}" for record in records
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _external_directory(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(_repository_root())
    except ValueError:
        return resolved
    raise ValueError(
        f"Biometric outputs must be outside the repository: {resolved}"
    )


def _load_cache(cache_path: Path) -> dict[str, np.ndarray]:
    if not cache_path.is_file():
        return {}
    with np.load(cache_path, allow_pickle=False) as data:
        return {key: np.asarray(data[key], dtype=np.float32) for key in data.files}


def _save_cache(cache_path: Path, embeddings: dict[str, np.ndarray]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache_path, **embeddings)


def _extract_embeddings(
    records: Sequence[ImageRecord],
    engine,
    cache_path: Path,
) -> tuple[dict[str, np.ndarray], list[dict[str, str]], dict[str, float]]:
    embeddings = _load_cache(cache_path)
    failures: list[dict[str, str]] = []
    timings: list[float] = []
    first_ms = None

    for record in records:
        if record.path in embeddings:
            continue
        started = time.perf_counter()
        try:
            result = engine.extract_from_path(record.path)
            embedding = np.asarray(result.embedding, dtype=np.float32)
            norm = float(np.linalg.norm(embedding))
            if embedding.shape != (512,) or not np.all(np.isfinite(embedding)):
                raise ValueError("embedding is not finite and 512-dimensional")
            if not np.isclose(norm, 1.0, atol=0.01):
                raise ValueError(f"embedding norm is {norm:.6f}, expected 1.0")
            embeddings[record.path] = embedding
            elapsed_ms = (time.perf_counter() - started) * 1000
            first_ms = elapsed_ms if first_ms is None else first_ms
            timings.append(elapsed_ms)
        except Exception as exc:
            failures.append(
                {"path": record.path, "error_type": type(exc).__name__, "error": str(exc)}
            )
    _save_cache(cache_path, embeddings)
    return embeddings, failures, {
        "first_inference_ms": round(first_ms, 3) if first_ms is not None else 0.0,
        "average_embedding_ms": round(float(np.mean(timings)), 3) if timings else 0.0,
        "warm_embedding_ms": (
            round(float(np.mean(timings[1:])), 3) if len(timings) > 1 else 0.0
        ),
        "embedding_count": float(len(embeddings)),
    }


def _score_pairs(
    pairs: Sequence[PairRecord], embeddings: dict[str, np.ndarray]
) -> tuple[list[float], list[int], list[dict[str, str]], float]:
    started = time.perf_counter()
    scores: list[float] = []
    labels: list[int] = []
    failures: list[dict[str, str]] = []
    for pair in pairs:
        if pair.first not in embeddings or pair.second not in embeddings:
            failures.append(
                {
                    "first": pair.first,
                    "second": pair.second,
                    "error_type": "EmbeddingUnavailable",
                    "error": "Pair excluded because image extraction failed",
                }
            )
            continue
        first = embeddings[pair.first]
        second = embeddings[pair.second]
        scores.append(float(np.dot(first, second)))
        labels.append(pair.label)
    return scores, labels, failures, (time.perf_counter() - started) * 1000


def _distribution(scores: Sequence[float], labels: Sequence[int]) -> dict[str, dict[str, float]]:
    result = {}
    for name, label in (("genuine", 1), ("impostor", 0)):
        values = np.asarray(
            [score for score, item_label in zip(scores, labels) if item_label == label],
            dtype=float,
        )
        if values.size == 0:
            raise ValueError(f"No {name} scores are available for this split")
        result[name] = {
            "count": float(values.size),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
        }
    return result


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _gpu_memory_mb() -> tuple[float | None, str]:
    """Read current NVIDIA memory usage when nvidia-smi is available."""
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        values = [float(line.strip()) for line in completed.stdout.splitlines() if line.strip()]
        return (max(values), "nvidia-smi") if values else (None, "nvidia-smi-empty")
    except FileNotFoundError:
        return None, "nvidia-smi-unavailable"
    except (subprocess.CalledProcessError, ValueError):
        return None, "nvidia-smi-error"


def run_evaluation(
    dataset_root: Path,
    output_dir: Path,
    cache_dir: Path,
    *,
    dataset_name: str,
    seed: int = 42,
    max_genuine_per_identity: int | None = None,
    max_impostor: int | None = None,
) -> dict:
    """Run extraction, validation calibration, and held-out test evaluation."""
    repository_root = _repository_root()
    if str(repository_root) not in sys.path:
        sys.path.insert(0, str(repository_root))
    records = discover_images(dataset_root)
    splits = split_identities([record.identity for record in records], seed)
    _validate_pair_capacity(records, splits["validation"], "validation")
    _validate_pair_capacity(records, splits["test"], "test")
    output_dir = _external_directory(output_dir)
    cache_dir = _external_directory(cache_dir)
    engine_started = time.perf_counter()
    from backend.app.face.recognition import ArcFaceEngine

    gpu_before_mb, gpu_memory_source = _gpu_memory_mb()
    engine = ArcFaceEngine()
    engine.load_model()
    initialization_ms = (time.perf_counter() - engine_started) * 1000
    embeddings, extraction_failures, timing = _extract_embeddings(
        records, engine, cache_dir / f"{dataset_name.lower()}_embeddings.npz"
    )
    gpu_after_mb, _ = _gpu_memory_mb()

    split_results = {}
    pair_verification_ms = 0.0
    all_failures = list(extraction_failures)
    for split_name in ("validation", "test"):
        pairs = generate_pairs(
            records,
            splits[split_name],
            seed=seed,
            max_genuine_per_identity=max_genuine_per_identity,
            max_impostor=max_impostor,
        )
        scores, labels, pair_failures, elapsed_ms = _score_pairs(pairs, embeddings)
        pair_verification_ms += elapsed_ms
        all_failures.extend(pair_failures)
        split_results[split_name] = {
            "pair_count": len(scores),
            "genuine_pairs": sum(labels),
            "impostor_pairs": len(labels) - sum(labels),
            "scores": scores,
            "labels": labels,
        }
        if split_name in ("validation", "test"):
            split_results[split_name]["distribution"] = _distribution(scores, labels)

    validation = split_results["validation"]
    threshold = select_threshold(
        [score for score, label in zip(validation["scores"], validation["labels"]) if label],
        [score for score, label in zip(validation["scores"], validation["labels"]) if not label],
    )
    test = split_results["test"]
    test_metrics = evaluate_scores(test["scores"], test["labels"], threshold)
    placeholder_metrics = evaluate_scores(
        test["scores"], test["labels"], DEFAULT_THRESHOLD
    )
    fpr, tpr, roc_thresholds = roc_curve(test["labels"], test["scores"])
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "roc_curve.csv").write_text(
        "threshold,fpr,tpr\n"
        + "\n".join(
            f"{threshold_value},{false_positive_rate},{true_positive_rate}"
            for threshold_value, false_positive_rate, true_positive_rate in zip(
                roc_thresholds, fpr, tpr
            )
        )
        + "\n",
        encoding="utf-8",
    )
    report = {
        "dataset": {
            "name": dataset_name,
            "root": str(dataset_root.resolve()),
            "image_count": len(records),
            "identity_count": len(set(record.identity for record in records)),
            "manifest_sha256": dataset_manifest(records),
        },
        "split": splits,
        "random_seed": seed,
        "model": {"pack": "buffalo_l", "embedding_dimension": 512},
        "threshold": {
            "selected_from": "validation",
            "selected": threshold,
            "placeholder_comparison": DEFAULT_THRESHOLD,
        },
        "validation": {
            "pair_count": validation["pair_count"],
            "genuine_pairs": validation["genuine_pairs"],
            "impostor_pairs": validation["impostor_pairs"],
        },
        "test": {
            "pair_count": test["pair_count"],
            "genuine_pairs": test["genuine_pairs"],
            "impostor_pairs": test["impostor_pairs"],
            "similarity_distributions": test["distribution"],
            "metrics": test_metrics,
            "placeholder_metrics": placeholder_metrics,
        },
        "performance": {
            "model_initialization_ms": round(initialization_ms, 3),
            **timing,
            "pair_verification_ms": round(pair_verification_ms, 3),
            "gpu_memory_before_mb": gpu_before_mb,
            "gpu_memory_after_mb": gpu_after_mb,
            "gpu_memory_peak_observed_mb": (
                max(value for value in (gpu_before_mb, gpu_after_mb) if value is not None)
                if gpu_before_mb is not None or gpu_after_mb is not None
                else None
            ),
            "gpu_memory_source": gpu_memory_source,
        },
        "runtime": {
            "active_providers": engine.active_providers,
            "cuda_provider_active": engine.is_gpu_active,
        },
        "failures": {
            "count": len(all_failures),
            "path": str(output_dir / "failures.jsonl"),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    }
    _write_json(output_dir / "report.json", report)
    (output_dir / "failures.jsonl").write_text(
        "".join(json.dumps(item) + "\n" for item in all_failures),
        encoding="utf-8",
    )
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dataset-name", default="custom")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / ".cache" / "trueface-ai" / "evaluations",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.home() / ".cache" / "trueface-ai" / "arcface",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-genuine-per-identity", type=int)
    parser.add_argument("--max-impostor", type=int)
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    print(
        json.dumps(
            run_evaluation(
                args.dataset,
                args.output_dir,
                args.cache_dir,
                dataset_name=args.dataset_name,
                seed=args.seed,
                max_genuine_per_identity=args.max_genuine_per_identity,
                max_impostor=args.max_impostor,
            ),
            indent=2,
        )
    )
