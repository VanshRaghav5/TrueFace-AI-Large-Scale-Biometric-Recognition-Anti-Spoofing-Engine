"""Metrics for face-verification experiments.

Threshold selection must be performed on validation scores, never on the
held-out test scores.
"""

from typing import Iterable

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    roc_auc_score,
    roc_curve,
)


def select_threshold(genuine_scores: Iterable[float], impostor_scores: Iterable[float]) -> float:
    genuine = np.asarray(list(genuine_scores), dtype=float)
    impostor = np.asarray(list(impostor_scores), dtype=float)
    if genuine.size == 0 or impostor.size == 0:
        raise ValueError(
            "Validation threshold selection requires genuine and impostor scores"
        )
    candidates = np.unique(
        np.concatenate((genuine, impostor, np.array([0.0, 1.0], dtype=float)))
    )
    candidates = candidates[(candidates >= 0.0) & (candidates <= 1.0)]
    labels = np.concatenate((np.ones(genuine.size), np.zeros(impostor.size)))
    scores = np.concatenate((genuine, impostor))
    best = max(
        candidates,
        key=lambda threshold: (
            accuracy_score(labels, scores >= threshold),
            -float(threshold),
        ),
    )
    return float(best)


def evaluate_scores(
    scores: Iterable[float],
    labels: Iterable[int],
    threshold: float,
) -> dict[str, float]:
    """Return verification and ROC metrics for a labelled score set."""
    values = np.asarray(list(scores), dtype=float)
    expected = np.asarray(list(labels), dtype=int)
    if values.size == 0 or values.size != expected.size:
        raise ValueError("Scores and labels must be non-empty and have equal length")
    if set(expected.tolist()) != {0, 1}:
        raise ValueError("Scores must contain both genuine and impostor labels")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Evaluation threshold must be between 0.0 and 1.0")

    fpr, tpr, roc_thresholds = roc_curve(expected, values)
    fnr = 1.0 - tpr
    eer_index = int(np.argmin(np.abs(fpr - fnr)))
    genuine = values[expected == 1]
    impostor = values[expected == 0]
    predicted = values >= threshold
    return {
        "accuracy": float(accuracy_score(expected, predicted)),
        "far": float(np.mean(impostor >= threshold)),
        "frr": float(np.mean(genuine < threshold)),
        "tar": float(np.mean(genuine >= threshold)),
        "roc_auc": float(roc_auc_score(expected, values)),
        "eer": float((fpr[eer_index] + fnr[eer_index]) / 2.0),
        "eer_threshold": float(roc_thresholds[eer_index]),
    }


def summarize(scores: Iterable[float], labels: Iterable[int], threshold: float) -> dict[str, float]:
    values = np.asarray(list(scores), dtype=float)
    expected = np.asarray(list(labels), dtype=int)
    if values.size == 0 or values.size != expected.size:
        raise ValueError("Scores and labels must be non-empty and have equal length")
    predicted = (values >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        expected, predicted, average="binary", zero_division=0
    )
    genuine = values[expected == 1]
    impostor = values[expected == 0]
    far = float(np.mean(impostor >= threshold)) if impostor.size else 0.0
    frr = float(np.mean(genuine < threshold)) if genuine.size else 0.0
    return {
        "accuracy": float(accuracy_score(expected, predicted)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "far": far,
        "frr": frr,
        "roc_auc": float(roc_auc_score(expected, values)),
    }
