"""Unit tests for scoring quality-harness dataset validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hrm_backend.scoring.evaluation.dataset import load_scoring_quality_dataset


def _base_dataset_payload() -> dict[str, object]:
    """Build the smallest valid dataset payload for dataset-validation tests."""

    return {
        "dataset_id": "unit-dataset",
        "scenarios": [
            {
                "scenario_id": "base",
                "vacancy": {
                    "title": "Backend Engineer",
                    "description": "Build Python services.",
                    "department": "Engineering",
                    "status": "open",
                },
                "candidates": [
                    {
                        "candidate_id": "candidate-a",
                        "document": {
                            "filename": "candidate-a.pdf",
                            "mime_type": "application/pdf",
                            "detected_language": "en",
                            "parsed_at": "2026-03-12T10:00:00+00:00",
                            "parsed_profile_json": {
                                "summary": "Python engineer",
                                "skills": ["Python"],
                            },
                            "evidence_json": [],
                        },
                        "expected_relevance": 3,
                        "expected_matched_requirements": ["Python"],
                        "expected_missing_requirements": ["Docker"],
                        "fixture_prediction": {
                            "score": 90,
                            "confidence": 0.8,
                            "summary": "Strong Python fit.",
                            "matched_requirements": ["Python"],
                            "missing_requirements": ["Docker"],
                            "evidence": [],
                            "model_name": "fixture",
                            "model_version": "v1",
                        },
                    }
                ],
            }
        ],
    }


def _write_dataset(tmp_path: Path, payload: dict[str, object]) -> Path:
    """Write one dataset payload to a temporary JSON file."""

    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps(payload), encoding="utf-8")
    return dataset_path


def test_fixture_mode_requires_fixture_predictions(tmp_path: Path) -> None:
    """Fixture mode should reject datasets missing deterministic predictions."""

    payload = _base_dataset_payload()
    payload["scenarios"][0]["candidates"][0]["fixture_prediction"] = None

    dataset_path = _write_dataset(tmp_path, payload)

    with pytest.raises(ValueError, match="fixture mode requires fixture_prediction"):
        load_scoring_quality_dataset(dataset_path, mode="fixture")


def test_ollama_mode_allows_missing_fixture_predictions(tmp_path: Path) -> None:
    """Optional Ollama mode should accept datasets without fixture predictions."""

    payload = _base_dataset_payload()
    payload["scenarios"][0]["candidates"][0]["fixture_prediction"] = None

    dataset_path = _write_dataset(tmp_path, payload)
    dataset = load_scoring_quality_dataset(dataset_path, mode="ollama")

    assert dataset.dataset_id == "unit-dataset"


def test_dataset_rejects_duplicate_candidate_ids(tmp_path: Path) -> None:
    """Scenario validation should fail closed when candidate ids are duplicated."""

    payload = _base_dataset_payload()
    duplicate_candidate = json.loads(json.dumps(payload["scenarios"][0]["candidates"][0]))
    payload["scenarios"][0]["candidates"].append(duplicate_candidate)

    dataset_path = _write_dataset(tmp_path, payload)

    with pytest.raises(ValueError, match="duplicate candidate ids"):
        load_scoring_quality_dataset(dataset_path, mode="fixture")


def test_dataset_rejects_paraphrase_candidate_mismatch(tmp_path: Path) -> None:
    """Paraphrase scenarios should require the same candidate id set as the base scenario."""

    payload = _base_dataset_payload()
    payload["scenarios"].append(
        {
            "scenario_id": "paraphrase",
            "paraphrase_of": "base",
            "vacancy": {
                "title": "Platform Engineer",
                "description": "Maintain Python services.",
                "department": "Engineering",
                "status": "open",
            },
            "candidates": [
                {
                    "candidate_id": "candidate-b",
                    "document": {
                        "filename": "candidate-b.pdf",
                        "mime_type": "application/pdf",
                        "detected_language": "en",
                        "parsed_at": "2026-03-12T10:05:00+00:00",
                        "parsed_profile_json": {
                            "summary": "Python engineer",
                            "skills": ["Python"],
                        },
                        "evidence_json": [],
                    },
                    "expected_relevance": 2,
                    "expected_matched_requirements": ["Python"],
                    "expected_missing_requirements": ["Docker"],
                    "fixture_prediction": {
                        "score": 70,
                        "confidence": 0.7,
                        "summary": "Partial Python fit.",
                        "matched_requirements": ["Python"],
                        "missing_requirements": ["Docker"],
                        "evidence": [],
                        "model_name": "fixture",
                        "model_version": "v1",
                    },
                }
            ],
        }
    )

    dataset_path = _write_dataset(tmp_path, payload)

    with pytest.raises(
        ValueError,
        match="paraphrase scenario candidate ids must match the referenced base scenario",
    ):
        load_scoring_quality_dataset(dataset_path, mode="fixture")
