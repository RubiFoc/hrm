"""Unit tests for Ollama adapter mapping and score schema validation."""

from __future__ import annotations

import json

import pytest

from hrm_backend.scoring.infra.ollama.adapter import decode_ollama_generate_response


def test_decode_ollama_response_infers_model_identity_from_top_level_metadata() -> None:
    """Verify adapter mapping injects `model_name` and `model_version` when omitted by LLM JSON."""
    payload = {
        "model": "llama3.2:latest",
        "response": json.dumps(
            {
                "score": 88,
                "confidence": 0.81,
                "summary": "Strong backend fit with clear Python evidence.",
                "matched_requirements": ["Python", "REST APIs"],
                "missing_requirements": ["Kubernetes"],
                "evidence": [
                    {
                        "requirement": "Python",
                        "snippet": "5 years of Python backend engineering",
                        "source_field": "skills",
                    }
                ],
            }
        ),
    }

    result = decode_ollama_generate_response(payload, fallback_model="mistral:latest")

    assert result.model_name == "llama3.2"
    assert result.model_version == "latest"
    assert result.score == 88
    assert result.confidence == 0.81
    assert result.evidence[0].requirement == "Python"


def test_decode_ollama_response_rejects_invalid_score_schema() -> None:
    """Verify invalid generated payloads fail schema validation."""
    payload = {
        "model": "llama3.2:latest",
        "response": json.dumps(
            {
                "score": 101,
                "confidence": 1.4,
                "summary": "",
                "matched_requirements": ["Python"],
                "missing_requirements": [],
                "evidence": [],
            }
        ),
    }

    with pytest.raises(ValueError):
        decode_ollama_generate_response(payload, fallback_model="llama3.2:latest")

