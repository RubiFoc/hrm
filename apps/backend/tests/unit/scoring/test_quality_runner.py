"""Unit tests for scoring quality-harness runner behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from hrm_backend.scoring.evaluation.dataset import load_scoring_quality_dataset
from hrm_backend.scoring.evaluation.runner import run_quality_harness

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "scoring_quality"


def test_ollama_mode_requires_adapter() -> None:
    """Runner should fail closed when optional Ollama mode has no adapter configured."""

    dataset = load_scoring_quality_dataset(FIXTURES_DIR / "baseline.json", mode="ollama")

    with pytest.raises(ValueError, match="ollama mode requires a scoring adapter"):
        run_quality_harness(dataset=dataset, mode="ollama")
