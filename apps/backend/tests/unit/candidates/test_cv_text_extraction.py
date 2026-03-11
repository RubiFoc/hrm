"""Unit tests for native PDF/DOCX CV text extraction."""

from __future__ import annotations

from pathlib import Path

import pytest

from hrm_backend.candidates.utils.cv import extract_docx_text, extract_pdf_text, parse_cv_document

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "candidates"
PDF_MIME_TYPE = "application/pdf"
DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _read_fixture_bytes(filename: str) -> bytes:
    """Read one CV fixture payload by filename."""
    return (FIXTURES_DIR / filename).read_bytes()


def test_extract_pdf_text_returns_text_and_page_mapping() -> None:
    """Verify PDF extractor returns unified text with stable page spans."""
    result = extract_pdf_text(content=_read_fixture_bytes("sample_cv_en.pdf"))

    assert "John Doe" in result.text
    assert "Docker SQL" in result.text
    assert result.resolve_page(start_offset=0, end_offset=len("John Doe")) == 1
    docker_start = result.text.index("Docker SQL")
    assert result.resolve_page(start_offset=docker_start, end_offset=docker_start + 6) == 2


def test_extract_pdf_text_rejects_broken_pdf() -> None:
    """Verify PDF extractor fails closed for unreadable payloads."""
    with pytest.raises(ValueError, match="unreadable PDF|PDF parser error"):
        extract_pdf_text(content=_read_fixture_bytes("broken_cv.pdf"))


def test_extract_docx_text_returns_text() -> None:
    """Verify DOCX extractor returns body text without fallback byte decoding."""
    result = extract_docx_text(content=_read_fixture_bytes("sample_cv_ru.docx"))

    assert "Иван Иванов" in result.text
    assert "машинное обучение" in result.text
    assert all(span.page is None for span in result.page_spans)


def test_extract_docx_text_rejects_broken_docx() -> None:
    """Verify DOCX extractor fails closed for unreadable archives."""
    with pytest.raises(ValueError, match="unreadable DOCX archive"):
        extract_docx_text(content=_read_fixture_bytes("broken_cv.docx"))


def test_parse_cv_document_rejects_empty_extracted_text() -> None:
    """Verify parser rejects valid documents that yield no extractable text."""
    with pytest.raises(ValueError, match="empty textual payload"):
        parse_cv_document(
            content=_read_fixture_bytes("empty_cv.docx"),
            mime_type=DOCX_MIME_TYPE,
        )
