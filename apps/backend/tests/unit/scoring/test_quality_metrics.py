"""Unit tests for scoring quality-harness metric helpers."""

from __future__ import annotations

import pytest

from hrm_backend.scoring.evaluation.metrics import (
    jaccard_similarity,
    match_precision,
    match_recall,
    mrr,
    ndcg,
    sort_scored_candidate_ids,
)


def test_match_metrics_return_one_for_identical_requirement_sets() -> None:
    """Perfect matched-requirement overlap should yield full precision and recall."""

    predicted = ["Python", "REST APIs"]
    expected = ["python", "REST APIs"]

    assert match_precision(predicted, expected) == pytest.approx(1.0)
    assert match_recall(predicted, expected) == pytest.approx(1.0)


def test_match_metrics_penalize_partial_overlap() -> None:
    """Partial requirement overlap should reduce precision while keeping recall intact."""

    predicted = ["Python", "REST APIs"]
    expected = ["Python"]

    assert match_precision(predicted, expected) == pytest.approx(0.5)
    assert match_recall(predicted, expected) == pytest.approx(1.0)


def test_match_metrics_handle_empty_requirement_sets() -> None:
    """Empty matched-requirement sets should fail closed without division errors."""

    assert match_precision([], []) == pytest.approx(1.0)
    assert match_recall([], []) == pytest.approx(1.0)
    assert match_precision([], ["Python"]) == pytest.approx(0.0)
    assert match_recall([], ["Python"]) == pytest.approx(0.0)


def test_sort_scored_candidate_ids_breaks_ties_by_candidate_id() -> None:
    """Score ties should keep ranking deterministic via candidate id ordering."""

    ranked = sort_scored_candidate_ids(
        {
            "candidate-b": 77.0,
            "candidate-a": 77.0,
            "candidate-c": 66.0,
        }
    )

    assert ranked == ["candidate-a", "candidate-b", "candidate-c"]


def test_ranking_metrics_cover_perfect_and_no_relevant_cases() -> None:
    """Ranking helpers should return perfect scores or fail-closed zeros deterministically."""

    perfect_relevance = {
        "candidate-a": 3,
        "candidate-b": 1,
        "candidate-c": 0,
    }
    perfect_ranking = ["candidate-a", "candidate-b", "candidate-c"]

    assert ndcg(perfect_relevance, perfect_ranking) == pytest.approx(1.0)
    assert mrr(perfect_relevance, perfect_ranking) == pytest.approx(1.0)

    no_relevant = {
        "candidate-a": 0,
        "candidate-b": 0,
    }
    assert ndcg(no_relevant, ["candidate-a", "candidate-b"]) == pytest.approx(0.0)
    assert mrr(no_relevant, ["candidate-a", "candidate-b"]) == pytest.approx(0.0)


def test_jaccard_similarity_handles_empty_and_partial_sets() -> None:
    """Paraphrase robustness helpers should stay deterministic for empty and partial sets."""

    assert jaccard_similarity([], []) == pytest.approx(1.0)
    assert jaccard_similarity(["Python", "Docker"], ["python"]) == pytest.approx(0.5)
