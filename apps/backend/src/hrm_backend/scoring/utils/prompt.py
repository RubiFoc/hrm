"""Prompt construction helpers for explainable match scoring."""

from __future__ import annotations

import json

from hrm_backend.candidates.models.document import CandidateDocument
from hrm_backend.vacancies.models.vacancy import Vacancy


def build_match_score_prompt(*, vacancy: Vacancy, document: CandidateDocument) -> str:
    """Build a deterministic prompt for vacancy-candidate scoring.

    Args:
        vacancy: Vacancy snapshot used as target profile.
        document: Active candidate document with parsed analysis artifacts.

    Returns:
        str: Prompt instructing the model to return a strict JSON score payload.

    Raises:
        ValueError: If parsed CV analysis artifacts are not ready.
    """
    if (
        document.parsed_profile_json is None
        or document.evidence_json is None
        or document.parsed_at is None
    ):
        raise ValueError("CV analysis is not ready")

    vacancy_snapshot = {
        "title": vacancy.title,
        "description": vacancy.description,
        "department": vacancy.department,
        "status": vacancy.status,
    }
    candidate_snapshot = {
        "parsed_profile": document.parsed_profile_json,
        "evidence": document.evidence_json,
        "detected_language": document.detected_language,
        "parsed_at": document.parsed_at.isoformat(),
    }

    return (
        "You are an HR screening assistant.\n"
        "Compare the vacancy against the parsed CV profile and evidence.\n"
        "Return JSON only.\n"
        "Scoring rules:\n"
        "- score: number from 0 to 100\n"
        "- confidence: number from 0 to 1\n"
        "- summary: concise explanation for recruiter review\n"
        "- matched_requirements: short requirement strings supported by evidence\n"
        "- missing_requirements: short requirement strings not supported by evidence\n"
        "- evidence: array of objects with requirement, snippet, and optional source_field\n"
        "- model_name and model_version: identify the model used\n\n"
        f"Vacancy JSON:\n{json.dumps(vacancy_snapshot, ensure_ascii=False, sort_keys=True)}\n\n"
        "Parsed CV JSON:\n"
        f"{json.dumps(candidate_snapshot, ensure_ascii=False, sort_keys=True)}\n"
    )
