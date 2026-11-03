import numpy as np
import pytest

from evaluation.experiments.face_recognition.evaluate_arcface import (
    ImageRecord,
    generate_pairs,
    split_identities,
)
from evaluation.experiments.face_recognition.metrics import (
    evaluate_scores,
    select_threshold,
)


def _records():
    return [
        ImageRecord(identity, f"{identity}/{index}.jpg")
        for identity in ("alice", "bob", "carol", "dave", "erin")
        for index in range(3)
    ]


def test_identity_split_is_reproducible_and_disjoint():
    first = split_identities(["alice", "bob", "carol", "dave", "erin"], seed=42)
    second = split_identities(["alice", "bob", "carol", "dave", "erin"], seed=42)

    assert first == second
    assert not set(first["train"]) & set(first["validation"])
    assert not set(first["train"]) & set(first["test"])
    assert not set(first["validation"]) & set(first["test"])


def test_pair_generation_preserves_labels_and_seed():
    records = _records()
    identities = ["alice", "bob", "carol"]
    first = generate_pairs(records, identities, seed=7, max_impostor=4)
    second = generate_pairs(records, identities, seed=7, max_impostor=4)

    assert first == second
    assert all(
        (pair.label == 1 and pair.identity and pair.first.split("/")[0] == pair.identity
         and pair.second.split("/")[0] == pair.identity)
        or (pair.label == 0 and pair.first.split("/")[0] != pair.second.split("/")[0])
        for pair in first
    )


def test_split_requires_three_identities():
    with pytest.raises(ValueError, match="three identities"):
        split_identities(["alice", "bob"])


def test_metrics_include_verification_and_eer_values():
    scores = [0.91, 0.88, 0.12, 0.22]
    labels = [1, 1, 0, 0]
    threshold = select_threshold([0.91, 0.88], [0.12, 0.22])
    metrics = evaluate_scores(scores, labels, threshold)

    assert threshold == 0.88
    assert metrics["far"] == 0.0
    assert metrics["frr"] == 0.0
    assert metrics["tar"] == 1.0
    assert metrics["roc_auc"] == 1.0
    assert 0.0 <= metrics["eer"] <= 1.0

