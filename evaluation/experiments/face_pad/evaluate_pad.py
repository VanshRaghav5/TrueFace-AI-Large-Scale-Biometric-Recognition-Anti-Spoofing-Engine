"""Evaluate PAD scores from a JSONL prediction manifest.

The script intentionally consumes predictions rather than downloading a
dataset or model. This keeps dataset licensing, preprocessing, and model
provenance explicit and prevents accidental claims from missing weights.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve


def _counts(records: list[dict]) -> dict[str, int | float]:
    counts = {
        "total_samples": len(records),
        "valid_bona_fide_predictions": 0,
        "valid_attack_predictions": 0,
        "unavailable_samples": 0,
        "error_samples": 0,
        "uncertain_samples": 0,
        "invalid_input_samples": 0,
        "unsupported_label_samples": 0,
        "missing_score_samples": 0,
        "protocol_manifest_exclusions": 0,
    }
    for record in records:
        state = record.get("state")
        label = record.get("label")
        if label not in {None, "bona_fide", "attack"}:
            counts["unsupported_label_samples"] += 1
        if record.get("exclusion_reason"):
            counts["protocol_manifest_exclusions"] += 1
        if state == "unavailable":
            counts["unavailable_samples"] += 1
        elif state == "error":
            counts["error_samples"] += 1
        elif state == "uncertain":
            counts["uncertain_samples"] += 1
        elif state in {"invalid", "invalid_input"}:
            counts["invalid_input_samples"] += 1
        if (
            state in {"bona_fide", "attack"}
            and label in {"bona_fide", "attack"}
            and record.get("bona_fide_score") is None
        ):
            counts["missing_score_samples"] += 1
    return counts


def evaluate(records: list[dict], threshold: float) -> dict:
    counts = _counts(records)
    valid = [
        record
        for record in records
        if record.get("state") in {"bona_fide", "attack"}
        and record.get("bona_fide_score") is not None
        and record.get("label") in {"bona_fide", "attack"}
        and np.isfinite(float(record["bona_fide_score"]))
        and 0.0 <= float(record["bona_fide_score"]) <= 1.0
    ]
    valid_bona_fide = sum(record["label"] == "bona_fide" for record in valid)
    valid_attack = sum(record["label"] == "attack" for record in valid)
    counts["valid_bona_fide_predictions"] = valid_bona_fide
    counts["valid_attack_predictions"] = valid_attack
    counts["valid_predictions"] = len(valid)
    counts["coverage_percentage"] = (
        100.0 * len(valid) / len(records) if records else 0.0
    )
    excluded = len(records) - len(valid)
    counts["bona_fide_metric_denominator"] = valid_bona_fide
    counts["attack_metric_denominator"] = valid_attack
    if not valid:
        return {
            "status": "unavailable",
            "reason": "No valid scored predictions",
            "excluded_predictions": excluded,
            **counts,
        }
    if not valid_bona_fide or not valid_attack:
        missing_class = "bona_fide" if not valid_bona_fide else "attack"
        return {
            "status": "incomplete",
            "reason": f"Missing usable scored predictions for {missing_class} class",
            "excluded_predictions": excluded,
            **counts,
        }

    labels = np.asarray([record["label"] == "bona_fide" for record in valid])
    scores = np.asarray([float(record["bona_fide_score"]) for record in valid])
    predictions = scores >= threshold
    bona_fide = labels
    attack = ~labels
    bpcer = float(np.mean(~predictions[bona_fide])) if np.any(bona_fide) else None
    apcer = float(np.mean(predictions[attack])) if np.any(attack) else None
    result = {
        "status": "evaluated",
        "threshold": threshold,
        "excluded_predictions": excluded,
        "bona_fide_metric_denominator": int(np.sum(bona_fide)),
        "attack_metric_denominator": int(np.sum(attack)),
        "apcer": apcer,
        "bpcer": bpcer,
        "acer": ((apcer + bpcer) / 2) if apcer is not None and bpcer is not None else None,
    }
    if len(np.unique(labels)) == 2:
        result["roc_auc"] = float(roc_auc_score(labels, scores))
        fpr, tpr, _ = roc_curve(labels, scores)
        result["eer_approximation"] = float(
            fpr[np.argmin(np.abs(fpr - (1.0 - tpr)))]
        )
    else:
        result["roc_auc"] = None
        result["eer_approximation"] = None
    return {**result, **counts}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--threshold", type=float, required=True)
    args = parser.parse_args()
    records = [
        json.loads(line)
        for line in args.manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    print(json.dumps(evaluate(records, args.threshold), indent=2))


if __name__ == "__main__":
    main()
