"""Deterministic metric helpers for the scoring quality harness."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence


def normalize_requirement_label(value: str) -> str:
    """Normalize one requirement label for case-insensitive metric comparisons.

    Args:
        value: Raw requirement label.

    Returns:
        str: Whitespace-collapsed, case-folded label.
    """

    return " ".join(value.strip().casefold().split())


def match_precision(predicted: Iterable[str], expected: Iterable[str]) -> float:
    """Compute set-based precision for matched requirements.

    Precision is defined over normalized unique labels. The empty/empty case returns `1.0`
    because the prediction contains no false positives.

    Args:
        predicted: Predicted matched requirement labels.
        expected: Expected matched requirement labels.

    Returns:
        float: Precision value in the `0..1` range.
    """

    predicted_set = {normalize_requirement_label(item) for item in predicted if item.strip()}
    expected_set = {normalize_requirement_label(item) for item in expected if item.strip()}
    if not predicted_set:
        return 1.0 if not expected_set else 0.0
    true_positives = predicted_set & expected_set
    return len(true_positives) / len(predicted_set)


def match_recall(predicted: Iterable[str], expected: Iterable[str]) -> float:
    """Compute set-based recall for matched requirements.

    Recall is defined over normalized unique labels. When the expected set is empty, the helper
    returns `1.0` because there are no missing positives to recover.

    Args:
        predicted: Predicted matched requirement labels.
        expected: Expected matched requirement labels.

    Returns:
        float: Recall value in the `0..1` range.
    """

    predicted_set = {normalize_requirement_label(item) for item in predicted if item.strip()}
    expected_set = {normalize_requirement_label(item) for item in expected if item.strip()}
    if not expected_set:
        return 1.0
    true_positives = predicted_set & expected_set
    return len(true_positives) / len(expected_set)


def sort_scored_candidate_ids(scores_by_candidate: Mapping[str, float]) -> list[str]:
    """Sort candidate ids deterministically by score descending and candidate id ascending.

    Args:
        scores_by_candidate: Candidate-to-score mapping.

    Returns:
        list[str]: Ranked candidate identifiers.
    """

    return [
        candidate_id
        for candidate_id, _ in sorted(
            scores_by_candidate.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]


def ndcg(
    relevance_by_candidate: Mapping[str, int],
    ranked_candidate_ids: Sequence[str],
) -> float:
    """Compute normalized discounted cumulative gain for one ranked scenario.

    Args:
        relevance_by_candidate: Candidate-to-relevance mapping in the `0..3` range.
        ranked_candidate_ids: Ranked candidate ids.

    Returns:
        float: NDCG value in the `0..1` range, or `0.0` when no relevant documents exist.
    """

    def _dcg(candidate_ids: Sequence[str]) -> float:
        score = 0.0
        for index, candidate_id in enumerate(candidate_ids, start=1):
            relevance = relevance_by_candidate.get(candidate_id, 0)
            if relevance <= 0:
                continue
            gain = (2**relevance) - 1
            score += gain / math.log2(index + 1)
        return score

    ideal_ranking = [
        candidate_id
        for candidate_id, _ in sorted(
            relevance_by_candidate.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
    ideal_score = _dcg(ideal_ranking)
    if ideal_score == 0:
        return 0.0
    return _dcg(ranked_candidate_ids) / ideal_score


def mrr(
    relevance_by_candidate: Mapping[str, int],
    ranked_candidate_ids: Sequence[str],
) -> float:
    """Compute reciprocal rank using the first positively relevant candidate.

    Args:
        relevance_by_candidate: Candidate-to-relevance mapping in the `0..3` range.
        ranked_candidate_ids: Ranked candidate ids.

    Returns:
        float: Reciprocal-rank value, or `0.0` when no relevant candidate exists.
    """

    for index, candidate_id in enumerate(ranked_candidate_ids, start=1):
        if relevance_by_candidate.get(candidate_id, 0) > 0:
            return 1.0 / index
    return 0.0


def jaccard_similarity(left: Iterable[str], right: Iterable[str]) -> float:
    """Compute normalized Jaccard similarity between two requirement sets.

    Args:
        left: First requirement collection.
        right: Second requirement collection.

    Returns:
        float: Similarity value in the `0..1` range, returning `1.0` for the empty/empty case.
    """

    left_set = {normalize_requirement_label(item) for item in left if item.strip()}
    right_set = {normalize_requirement_label(item) for item in right if item.strip()}
    if not left_set and not right_set:
        return 1.0
    union = left_set | right_set
    if not union:
        return 1.0
    return len(left_set & right_set) / len(union)


__all__ = [
    "jaccard_similarity",
    "match_precision",
    "match_recall",
    "mrr",
    "ndcg",
    "normalize_requirement_label",
    "sort_scored_candidate_ids",
]
