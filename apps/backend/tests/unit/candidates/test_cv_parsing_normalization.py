"""Unit tests for RU/EN CV normalization and evidence extraction."""

from __future__ import annotations

import pytest

from hrm_backend.candidates.utils.cv import parse_cv_document


def test_parse_cv_document_extracts_english_profile_and_evidence() -> None:
    """Verify English CV parsing returns canonical profile and evidence records."""
    payload = (
        b"John Doe\n"
        b"Email: john.doe@example.com\n"
        b"Phone: +1 (415) 555-0188\n"
        b"Experience: 5 years in Python, React, Docker and SQL.\n"
    )

    result = parse_cv_document(content=payload, mime_type="application/pdf")
    profile = result.parsed_profile
    personal = profile["personal"]
    contact = profile["contact"]
    skills = profile["skills"]
    experience = profile["experience"]
    assert isinstance(personal, dict)
    assert isinstance(contact, dict)
    assert isinstance(skills, list)
    assert isinstance(experience, dict)

    assert result.detected_language == "en"
    assert personal["full_name"] == "John Doe"
    assert contact["emails"] == ["john.doe@example.com"]
    assert "python" in skills
    assert "react" in skills
    assert "docker" in skills
    assert experience["years_total"] == 5
    assert any(item["field"] == "contact.emails" for item in result.evidence)
    assert any(item["field"].startswith("skills.") for item in result.evidence)


def test_parse_cv_document_extracts_russian_profile_and_skill_normalization() -> None:
    """Verify Russian CV parsing maps RU terms into canonical skill identifiers."""
    payload = (
        "Иван Иванов\n"
        "Почта: ivan@example.com\n"
        "Опыт: 3 года\n"
        "Навыки: Питон, Докер, машинное обучение.\n"
    ).encode()

    result = parse_cv_document(content=payload, mime_type="application/pdf")
    profile = result.parsed_profile
    skills = profile["skills"]
    experience = profile["experience"]
    assert isinstance(skills, list)
    assert isinstance(experience, dict)

    assert result.detected_language == "ru"
    assert "python" in skills
    assert "docker" in skills
    assert "machine_learning" in skills
    assert experience["years_total"] == 3
    assert any(item["field"] == "experience.years_total" for item in result.evidence)


def test_parse_cv_document_detects_mixed_language() -> None:
    """Verify parser marks mixed language when RU and EN text are both substantial."""
    payload = (
        "Мария Smith\n"
        "Skills: Python, SQL\n"
        "Опыт: 4 года разработки backend services.\n"
    ).encode()

    result = parse_cv_document(content=payload, mime_type="application/pdf")

    assert result.detected_language == "mixed"
    assert result.evidence


def test_parse_cv_document_rejects_empty_text_payload() -> None:
    """Verify parser fails fast when CV has no decodable text content."""
    with pytest.raises(ValueError, match="empty textual payload"):
        parse_cv_document(content=b"\x00\x00\x00", mime_type="application/pdf")
