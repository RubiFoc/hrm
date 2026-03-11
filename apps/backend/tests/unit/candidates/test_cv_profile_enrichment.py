"""Unit tests for structured workplace, education, title, date, and skills enrichment."""

from __future__ import annotations

from pathlib import Path

from hrm_backend.candidates.utils.cv import (
    extract_workplace_entries,
    normalize_date_range,
    normalize_title_value,
    parse_cv_document,
)

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "candidates"
PDF_MIME_TYPE = "application/pdf"
DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _read_fixture_bytes(filename: str) -> bytes:
    """Read one CV fixture payload by filename."""
    return (FIXTURES_DIR / filename).read_bytes()


def test_parse_cv_document_extracts_structured_workplaces_education_and_titles_from_pdf() -> None:
    """Verify structured PDF parsing populates universal workplace and education entries."""
    result = parse_cv_document(
        content=_read_fixture_bytes("sample_cv_structured_en.pdf"),
        mime_type=PDF_MIME_TYPE,
    )

    profile = result.parsed_profile
    workplaces = profile["workplaces"]["entries"]
    education_entries = profile["education"]["entries"]
    titles = profile["titles"]

    assert workplaces == profile["experience"]["entries"]
    assert workplaces[0]["employer"] == "Acme Logistics"
    assert workplaces[0]["position"]["raw"] == "Warehouse Supervisor"
    assert workplaces[0]["position"]["normalized"] == "warehouse supervisor"
    assert workplaces[0]["date_range"] == {
        "raw": "Jan 2022 - Present",
        "start": "2022-01",
        "end": None,
        "is_current": True,
    }
    assert workplaces[1]["position"]["raw"] == "Storekeeper"
    assert workplaces[1]["date_range"]["end"] == "2021"

    assert education_entries[0]["institution"] == "Minsk State College"
    assert education_entries[0]["degree"] == "Logistics Technician"
    assert education_entries[0]["date_range"]["start"] == "2016"
    assert education_entries[0]["date_range"]["end"] == "2019"

    assert titles["current"]["raw"] == "Warehouse Supervisor"
    assert titles["past"] == [{"raw": "Storekeeper", "normalized": "storekeeper"}]
    assert sorted(profile["skills"]) == [
        "forklift operation",
        "inventory control",
        "staff scheduling",
    ]
    assert any(
        item["field"] == "experience.entries[0].position.raw" and item["page"] == 1
        for item in result.evidence
    )
    assert any(
        item["field"].startswith("skills[") and item["page"] == 2 for item in result.evidence
    )


def test_parse_cv_document_extracts_structured_workplaces_education_and_titles_from_docx() -> None:
    """Verify structured DOCX parsing populates universal profession-agnostic sections."""
    result = parse_cv_document(
        content=_read_fixture_bytes("sample_cv_structured_ru.docx"),
        mime_type=DOCX_MIME_TYPE,
    )

    profile = result.parsed_profile
    workplaces = profile["workplaces"]["entries"]
    education_entries = profile["education"]["entries"]
    titles = profile["titles"]

    assert result.detected_language == "ru"
    assert workplaces[0]["employer"] == "ЛогистикСервис"
    assert workplaces[0]["position"]["raw"] == "Старший кладовщик"
    assert workplaces[0]["date_range"] == {
        "raw": "февраль 2021 - по настоящее время",
        "start": "2021-02",
        "end": None,
        "is_current": True,
    }
    assert workplaces[1]["position"]["raw"] == "Кладовщик"
    assert education_entries[0]["institution"] == "Минский государственный колледж"
    assert education_entries[0]["degree"] == "Бухгалтерский учет"
    assert titles["current"]["normalized"] == "старший кладовщик"
    assert titles["past"] == [{"raw": "Кладовщик", "normalized": "кладовщик"}]
    assert sorted(profile["skills"]) == [
        "обслуживание клиентов",
        "работа с кассой",
        "учет товара",
    ]
    assert all(item["page"] is None for item in result.evidence)


def test_extract_workplace_entries_supports_explicit_held_position_labels() -> None:
    """Verify labeled workplace parsing keeps `занимаемая должность` for previous jobs."""
    evidence: list[dict[str, object]] = []
    text = (
        "Опыт работы\n"
        "Работодатель: ТоргСклад\n"
        "Занимаемая должность: Кладовщик\n"
        "Период: 2018 - 2021\n"
        "Прием, хранение и выдача товара.\n"
    )

    entries = extract_workplace_entries(text, evidence)

    assert len(entries) == 1
    assert entries[0].employer is not None
    assert entries[0].position is not None
    assert entries[0].date_range is not None
    assert entries[0].employer.value == "ТоргСклад"
    assert entries[0].position.value == "Кладовщик"
    assert entries[0].date_range.start == "2018"
    assert entries[0].date_range.end == "2021"
    assert entries[0].summary is not None
    assert entries[0].summary.value == "Прием, хранение и выдача товара."
    assert any(item["field"] == "experience.entries[0].position.raw" for item in evidence)


def test_normalize_date_range_rejects_ambiguous_numeric_dates() -> None:
    """Verify ambiguous day-month numeric values stay unnormalized instead of being guessed."""
    assert normalize_date_range("03/04/2020 - 05/06/2021") == (None, None, False)
    assert normalize_date_range("04.05.2020") == (None, None, False)


def test_normalize_title_value_expands_neutral_abbreviations() -> None:
    """Verify title normalization stays profession-agnostic for common abbreviations."""
    assert normalize_title_value("Sr. Warehouse Mgr") == "senior warehouse manager"
