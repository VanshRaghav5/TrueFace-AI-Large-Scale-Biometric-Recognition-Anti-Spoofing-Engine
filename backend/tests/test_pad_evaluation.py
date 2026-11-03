import pytest

from evaluation.experiments.face_pad.evaluate_pad import evaluate


def test_pad_evaluation_excludes_unavailable_predictions():
    result = evaluate(
        [
            {"state": "unavailable", "label": "bona_fide"},
            {
                "state": "bona_fide",
                "label": "bona_fide",
                "bona_fide_score": 0.9,
            },
            {"state": "attack", "label": "attack", "bona_fide_score": 0.1},
        ],
        threshold=0.5,
    )

    assert result["status"] == "evaluated"
    assert result["valid_predictions"] == 2
    assert result["coverage_percentage"] == pytest.approx((2 / 3) * 100)
    assert result["excluded_predictions"] == 1
    assert result["bona_fide_metric_denominator"] == 1
    assert result["attack_metric_denominator"] == 1
    assert result["apcer"] == 0.0
    assert result["bpcer"] == 0.0


def test_pad_evaluation_is_unavailable_without_scored_predictions():
    result = evaluate([{"state": "unavailable"}], threshold=0.5)
    assert result["status"] == "unavailable"


def test_pad_evaluation_coverage_uses_metric_valid_predictions():
    records = [
        {"state": "bona_fide", "label": "bona_fide", "bona_fide_score": 0.9},
        {"state": "attack", "label": "attack", "bona_fide_score": 0.1},
        {"state": "bona_fide", "label": "bona_fide", "bona_fide_score": 0.8},
        {"state": "attack", "label": "attack", "bona_fide_score": None},
        {"state": "unavailable", "label": "bona_fide"},
        {"state": "error", "label": "attack"},
        {"state": "uncertain", "label": "attack"},
        {"state": "invalid_input", "label": "attack"},
        {"state": "attack", "label": "unknown", "bona_fide_score": 0.1},
    ]
    result = evaluate(records, threshold=0.5)
    assert result["valid_predictions"] == 3
    assert result["missing_score_samples"] == 1
    assert result["coverage_percentage"] == pytest.approx((3 / 9) * 100)
    assert result["bona_fide_metric_denominator"] == 2
    assert result["attack_metric_denominator"] == 1


@pytest.mark.parametrize(
    ("records", "missing_class"),
    [
        ([{"state": "bona_fide", "label": "bona_fide", "bona_fide_score": 0.9}], "attack"),
        ([{"state": "attack", "label": "attack", "bona_fide_score": 0.1}], "bona_fide"),
    ],
)
def test_pad_evaluation_requires_both_classes(records, missing_class):
    result = evaluate(records, threshold=0.5)
    assert result["status"] == "incomplete"
    assert missing_class in result["reason"]


def test_pad_evaluation_with_both_classes_is_evaluated():
    result = evaluate(
        [
            {"state": "bona_fide", "label": "bona_fide", "bona_fide_score": 0.9},
            {"state": "attack", "label": "attack", "bona_fide_score": 0.1},
        ],
        threshold=0.5,
    )
    assert result["status"] == "evaluated"


def test_pad_evaluation_missing_one_class_after_score_exclusion_is_incomplete():
    result = evaluate(
        [
            {"state": "bona_fide", "label": "bona_fide", "bona_fide_score": 0.9},
            {"state": "attack", "label": "attack", "bona_fide_score": None},
        ],
        threshold=0.5,
    )
    assert result["status"] == "incomplete"
    assert result["valid_predictions"] == 1
