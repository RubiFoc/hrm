"""Integration-style tests for the scoring quality-harness CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hrm_backend.scoring.cli.quality_harness import main

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "scoring_quality"


def test_quality_harness_cli_emits_deterministic_fixture_report(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Fixture mode should render a stable JSON report with ranking and robustness metrics."""

    exit_code = main(
        [
            "--dataset",
            str(FIXTURES_DIR / "baseline.json"),
            "--mode",
            "fixture",
            "--format",
            "json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["dataset_id"] == "scoring-quality-baseline"
    assert payload["mode"] == "fixture"
    assert payload["ranking_metrics"] == {
        "scenario_count": 2,
        "ndcg": 1.0,
        "mrr": 1.0,
    }
    assert payload["requirement_metrics"] == {
        "candidate_count": 6,
        "match_precision": pytest.approx(0.916667),
        "match_recall": 1.0,
    }
    assert payload["paraphrase_robustness"]["pair_count"] == 1
    assert payload["paraphrase_robustness"]["top_1_stability_rate"] == 1.0
    assert payload["paraphrase_robustness"]["full_ranking_stability_rate"] == 1.0
    assert payload["paraphrase_robustness"]["mean_matched_requirement_jaccard"] == pytest.approx(
        0.833333
    )
    assert payload["paraphrase_robustness"]["mean_missing_requirement_jaccard"] == pytest.approx(
        0.888889
    )
    assert payload["paraphrase_robustness"]["mean_absolute_score_delta"] == pytest.approx(
        2.333333
    )
    assert [scenario["scenario_id"] for scenario in payload["scenarios"]] == [
        "backend-engineer-base",
        "backend-engineer-paraphrase",
    ]
    assert payload["scenarios"][0]["ranked_candidate_ids"] == [
        "candidate-alex",
        "candidate-ira",
        "candidate-zoe",
    ]
