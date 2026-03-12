"""Deterministic JSON reporting helpers for the scoring quality harness."""

from __future__ import annotations

import json
from typing import Any

from hrm_backend.scoring.evaluation.runner import QualityHarnessReport


def build_quality_report_payload(report: QualityHarnessReport) -> dict[str, Any]:
    """Build a deterministic machine-readable payload from a harness report.

    Args:
        report: Completed harness report.

    Returns:
        dict[str, Any]: Ordered JSON-serializable payload.
    """

    pair_count = len(report.paraphrase_pairs)
    return {
        "dataset_id": report.dataset_id,
        "mode": report.mode,
        "ranking_metrics": {
            "scenario_count": len(report.scenarios),
            "ndcg": _round_metric(report.ranking_ndcg),
            "mrr": _round_metric(report.ranking_mrr),
        },
        "requirement_metrics": {
            "candidate_count": sum(len(scenario.candidates) for scenario in report.scenarios),
            "match_precision": _round_metric(report.match_precision),
            "match_recall": _round_metric(report.match_recall),
        },
        "paraphrase_robustness": {
            "pair_count": pair_count,
            "top_1_stability_rate": _round_optional_metric(
                _mean_or_none(1.0 if pair.top_1_stable else 0.0 for pair in report.paraphrase_pairs)
            ),
            "full_ranking_stability_rate": _round_optional_metric(
                _mean_or_none(
                    1.0 if pair.full_ranking_stable else 0.0 for pair in report.paraphrase_pairs
                )
            ),
            "mean_matched_requirement_jaccard": _round_optional_metric(
                _mean_or_none(
                    pair.mean_matched_requirement_jaccard for pair in report.paraphrase_pairs
                )
            ),
            "mean_missing_requirement_jaccard": _round_optional_metric(
                _mean_or_none(
                    pair.mean_missing_requirement_jaccard for pair in report.paraphrase_pairs
                )
            ),
            "mean_absolute_score_delta": _round_optional_metric(
                _mean_or_none(pair.mean_absolute_score_delta for pair in report.paraphrase_pairs)
            ),
            "pairs": [
                {
                    "base_scenario_id": pair.base_scenario_id,
                    "paraphrase_scenario_id": pair.paraphrase_scenario_id,
                    "base_top_candidate_id": pair.base_top_candidate_id,
                    "paraphrase_top_candidate_id": pair.paraphrase_top_candidate_id,
                    "top_1_stable": pair.top_1_stable,
                    "full_ranking_stable": pair.full_ranking_stable,
                    "mean_matched_requirement_jaccard": _round_metric(
                        pair.mean_matched_requirement_jaccard
                    ),
                    "mean_missing_requirement_jaccard": _round_metric(
                        pair.mean_missing_requirement_jaccard
                    ),
                    "mean_absolute_score_delta": _round_metric(pair.mean_absolute_score_delta),
                }
                for pair in report.paraphrase_pairs
            ],
        },
        "scenarios": [
            {
                "scenario_id": scenario.scenario_id,
                "paraphrase_of": scenario.paraphrase_of,
                "ranking_metrics": {
                    "ndcg": _round_metric(scenario.ranking_ndcg),
                    "mrr": _round_metric(scenario.ranking_mrr),
                },
                "requirement_metrics": {
                    "match_precision": _round_metric(scenario.match_precision),
                    "match_recall": _round_metric(scenario.match_recall),
                },
                "ranked_candidate_ids": list(scenario.ranked_candidate_ids),
                "candidates": [
                    {
                        "candidate_id": candidate.candidate_id,
                        "expected_relevance": candidate.expected_relevance,
                        "predicted_score": candidate.predicted_score,
                        "predicted_confidence": candidate.predicted_confidence,
                        "summary": candidate.summary,
                        "match_precision": _round_metric(candidate.match_precision),
                        "match_recall": _round_metric(candidate.match_recall),
                        "predicted_matched_requirements": list(
                            candidate.predicted_matched_requirements
                        ),
                        "expected_matched_requirements": list(
                            candidate.expected_matched_requirements
                        ),
                        "predicted_missing_requirements": list(
                            candidate.predicted_missing_requirements
                        ),
                        "expected_missing_requirements": list(
                            candidate.expected_missing_requirements
                        ),
                        "model_name": candidate.model_name,
                        "model_version": candidate.model_version,
                    }
                    for candidate in scenario.candidates
                ],
            }
            for scenario in report.scenarios
        ],
    }


def render_quality_report_json(report: QualityHarnessReport) -> str:
    """Render a quality-harness report as deterministic JSON text.

    Args:
        report: Completed harness report.

    Returns:
        str: Pretty-printed JSON payload terminated with a trailing newline.
    """

    return json.dumps(build_quality_report_payload(report), indent=2, ensure_ascii=True) + "\n"


def _round_metric(value: float) -> float:
    """Round one metric to a stable report precision."""

    return round(value, 6)


def _round_optional_metric(value: float | None) -> float | None:
    """Round optional metrics without changing `None` values."""

    if value is None:
        return None
    return _round_metric(value)


def _mean_or_none(values) -> float | None:
    """Return the arithmetic mean for a generator, or `None` when it is empty."""

    materialized = tuple(values)
    if not materialized:
        return None
    return sum(materialized) / len(materialized)


__all__ = [
    "build_quality_report_payload",
    "render_quality_report_json",
]
