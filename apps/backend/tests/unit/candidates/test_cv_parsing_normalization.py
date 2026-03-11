"""Unit tests for RU/EN CV normalization and evidence extraction."""

from __future__ import annotations

from pathlib import Path

from hrm_backend.candidates.utils.cv import parse_cv_document

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "candidates"
PDF_MIME_TYPE = "application/pdf"
DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _read_fixture_bytes(filename: str) -> bytes:
    """Read one CV fixture payload by filename."""
    return (FIXTURES_DIR / filename).read_bytes()


def test_parse_cv_document_extracts_english_pdf_profile_and_page_evidence() -> None:
    """Verify PDF parsing returns canonical profile fields and page-aware evidence."""
    result = parse_cv_document(
        content=_read_fixture_bytes("sample_cv_en.pdf"),
        mime_type=PDF_MIME_TYPE,
    )
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
    assert "sql" in skills
    assert experience["years_total"] == 5
    assert any(item["field"] == "contact.emails" for item in result.evidence)
    assert any(
        item["field"].startswith("skills[")
        and item["snippet"] == "Docker SQL"
        and item["page"] == 2
        for item in result.evidence
    )


def test_parse_cv_document_extracts_russian_docx_profile_and_skill_normalization() -> None:
    """Verify DOCX parsing maps RU terms into canonical skill identifiers."""
    result = parse_cv_document(
        content=_read_fixture_bytes("sample_cv_ru.docx"),
        mime_type=DOCX_MIME_TYPE,
    )
    profile = result.parsed_profile
    skills = profile["skills"]
    experience = profile["experience"]
    personal = profile["personal"]
    contact = profile["contact"]
    assert isinstance(skills, list)
    assert isinstance(experience, dict)
    assert isinstance(personal, dict)
    assert isinstance(contact, dict)

    assert result.detected_language == "ru"
    assert personal["full_name"] == "Иван Иванов"
    assert contact["emails"] == ["ivan@example.com"]
    assert "python" in skills
    assert "docker" in skills
    assert "sql" in skills
    assert "machine_learning" in skills
    assert experience["years_total"] == 3
    assert any(item["field"] == "experience.years_total" for item in result.evidence)
    assert any(item["field"].startswith("skills[") for item in result.evidence)
    assert all(item["page"] is None for item in result.evidence)


def test_parse_cv_document_detects_mixed_language_from_docx() -> None:
    """Verify parser marks mixed language when DOCX text contains RU and EN fragments."""
    result = parse_cv_document(
        content=_read_fixture_bytes("sample_cv_mixed.docx"),
        mime_type=DOCX_MIME_TYPE,
    )

    assert result.detected_language == "mixed"
    assert result.evidence
