"""Ollama adapter for explainable vacancy-candidate match scoring."""

from __future__ import annotations

import json
from typing import Protocol
from urllib import error, request

from hrm_backend.candidates.models.document import CandidateDocument
from hrm_backend.scoring.utils.prompt import build_match_score_prompt
from hrm_backend.scoring.utils.result import MatchScoreResult
from hrm_backend.vacancies.models.vacancy import Vacancy


class MatchScoringAdapter(Protocol):
    """Protocol implemented by match scoring model adapters."""

    def score_candidate(self, *, vacancy: Vacancy, document: CandidateDocument) -> MatchScoreResult:
        """Score one candidate against one vacancy using parsed CV analysis."""


class OllamaMatchScoringAdapter:
    """HTTP adapter that requests structured scoring output from Ollama."""

    def __init__(
        self,
        *,
        base_url: str,
        model_name: str,
        timeout_seconds: int,
    ) -> None:
        """Initialize adapter configuration."""
        self._base_url = base_url.rstrip("/")
        self._model_name = model_name.strip()
        self._timeout_seconds = timeout_seconds

    def score_candidate(self, *, vacancy: Vacancy, document: CandidateDocument) -> MatchScoreResult:
        """Request one structured score payload from Ollama."""
        prompt = build_match_score_prompt(vacancy=vacancy, document=document)
        payload = {
            "model": self._model_name,
            "stream": False,
            "format": MatchScoreResult.model_json_schema(),
            "prompt": prompt,
        }
        raw_request = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            url=f"{self._base_url}/api/generate",
            data=raw_request,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                raw_response = response.read().decode("utf-8")
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore").strip()
            detail = body or exc.reason
            raise RuntimeError(f"Ollama request failed with status {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Ollama request failed: {exc.reason}") from exc

        try:
            decoded = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise ValueError("Ollama response was not valid JSON") from exc
        if not isinstance(decoded, dict):
            raise ValueError("Ollama response must be a JSON object")
        return decode_ollama_generate_response(decoded, fallback_model=self._model_name)


def decode_ollama_generate_response(
    payload: dict[str, object],
    *,
    fallback_model: str,
) -> MatchScoreResult:
    """Decode one Ollama generate response into validated canonical score payload.

    Args:
        payload: Top-level JSON response from Ollama `/api/generate`.
        fallback_model: Requested model identifier used when response omits model identity.

    Returns:
        MatchScoreResult: Validated canonical score result.

    Raises:
        ValueError: If generated payload cannot be parsed or validated.
    """
    raw_generated = payload.get("response")
    if not isinstance(raw_generated, str) or not raw_generated.strip():
        raise ValueError("Ollama response did not contain generated JSON")

    try:
        parsed_payload = json.loads(raw_generated)
    except json.JSONDecodeError as exc:
        raise ValueError("Generated Ollama payload was not valid JSON") from exc
    if not isinstance(parsed_payload, dict):
        raise ValueError("Generated Ollama payload must be a JSON object")

    model_identifier = str(payload.get("model") or fallback_model).strip()
    model_name, model_version = parse_model_identifier(model_identifier)
    parsed_payload.setdefault("model_name", model_name)
    parsed_payload.setdefault("model_version", model_version)
    return MatchScoreResult.model_validate(parsed_payload)


def parse_model_identifier(model_identifier: str) -> tuple[str, str]:
    """Split `name:version` model identifier into UI fields."""
    normalized = model_identifier.strip()
    if ":" in normalized:
        name, version = normalized.split(":", 1)
        return name.strip() or normalized, version.strip() or "unknown"
    if normalized:
        return normalized, "unknown"
    return "unknown", "unknown"

