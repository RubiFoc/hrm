"""Validation, extraction, and structured parsing helpers for candidate CV processing."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Literal
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException, status
from pypdf import PdfReader
from pypdf.errors import PdfReadError


@dataclass(frozen=True)
class CVValidationResult:
    """Validated file envelope returned by CV validator.

    Attributes:
        content: Uploaded binary payload.
        mime_type: Validated MIME type.
        checksum_sha256: Calculated SHA-256 checksum.
        size_bytes: Uploaded payload size in bytes.
    """

    content: bytes
    mime_type: str
    checksum_sha256: str
    size_bytes: int


DetectedCVLanguage = Literal["ru", "en", "mixed", "unknown"]
PDF_MIME_TYPE = "application/pdf"
DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DOCX_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


@dataclass(frozen=True)
class CVParseResult:
    """Normalized CV parsing output consumed by background worker.

    Attributes:
        parsed_profile: Canonical structured candidate profile.
        evidence: Evidence links from extracted fields to source snippets.
        detected_language: Detected source language marker.
    """

    parsed_profile: dict[str, object]
    evidence: list[dict[str, object]]
    detected_language: DetectedCVLanguage


@dataclass(frozen=True)
class ExtractedTextSpan:
    """Offset range in extracted text that maps back to a source page.

    Attributes:
        start_offset: Inclusive start offset in unified extracted text.
        end_offset: Exclusive end offset in unified extracted text.
        page: One-based source page number when known.
    """

    start_offset: int
    end_offset: int
    page: int | None


@dataclass(frozen=True)
class ExtractedDocumentText:
    """Unified document text returned by native PDF/DOCX extraction.

    Attributes:
        text: Text content passed to downstream normalization and evidence mapping.
        page_spans: Ordered offset ranges that preserve page traceability when available.
    """

    text: str
    page_spans: tuple[ExtractedTextSpan, ...]

    def resolve_page(self, *, start_offset: int, end_offset: int) -> int | None:
        """Resolve one evidence range back to its source page when known.

        Args:
            start_offset: Inclusive evidence start offset.
            end_offset: Exclusive evidence end offset.

        Returns:
            int | None: One-based page number for overlapping text, otherwise `None`.
        """
        return resolve_page_number(
            self.page_spans,
            start_offset=start_offset,
            end_offset=end_offset,
        )


@dataclass(frozen=True)
class TextLine:
    """One stripped line with offsets in the normalized extracted text."""

    text: str
    start_offset: int
    end_offset: int


@dataclass(frozen=True)
class LocatedValue:
    """Text value anchored to offsets in the normalized extracted text."""

    value: str
    start_offset: int
    end_offset: int


@dataclass(frozen=True)
class ParsedDateRange:
    """Normalized date range derived from one raw CV fragment."""

    raw: LocatedValue
    start: str | None
    end: str | None
    is_current: bool


@dataclass(frozen=True)
class WorkplaceEntry:
    """Structured workplace history entry extracted from the CV."""

    employer: LocatedValue | None
    position: LocatedValue | None
    date_range: ParsedDateRange | None
    summary: LocatedValue | None


@dataclass(frozen=True)
class EducationEntry:
    """Structured education entry extracted from the CV."""

    institution: LocatedValue | None
    degree: LocatedValue | None
    date_range: ParsedDateRange | None
    summary: LocatedValue | None


SKILL_SYNONYMS: dict[str, tuple[str, ...]] = {
    "python": ("python", "питон"),
    "java": ("java", "джава"),
    "javascript": ("javascript", "js", "javascript/typescript"),
    "typescript": ("typescript", "ts", "тайпскрипт"),
    "react": ("react", "react.js", "reactjs"),
    "sql": ("sql", "postgresql", "mysql"),
    "docker": ("docker", "докер"),
    "kubernetes": ("kubernetes", "k8s"),
    "machine_learning": ("machine learning", "ml", "машинное обучение"),
}

SECTION_HEADERS: dict[str, tuple[str, ...]] = {
    "workplaces": (
        "experience",
        "work experience",
        "employment",
        "employment history",
        "work history",
        "career",
        "professional experience",
        "опыт",
        "опыт работы",
        "места работы",
        "трудовая деятельность",
        "профессиональный опыт",
    ),
    "education": (
        "education",
        "academic background",
        "qualifications",
        "образование",
        "обучение",
        "квалификация",
    ),
    "skills": (
        "skills",
        "key skills",
        "competencies",
        "competency",
        "qualifications",
        "навыки",
        "ключевые навыки",
        "компетенции",
        "квалификация",
    ),
}
WORKPLACE_EMPLOYER_LABELS = (
    "employer",
    "company",
    "organization",
    "workplace",
    "работодатель",
    "компания",
    "организация",
    "место работы",
)
WORKPLACE_POSITION_LABELS = (
    "position",
    "title",
    "role",
    "job title",
    "должность",
    "занимаемая должность",
    "позиция",
    "роль",
)
WORKPLACE_DATE_LABELS = (
    "dates",
    "period",
    "date range",
    "employment dates",
    "период",
    "даты",
    "период работы",
    "срок работы",
)
EDUCATION_INSTITUTION_LABELS = (
    "institution",
    "school",
    "college",
    "university",
    "education provider",
    "учебное заведение",
    "учреждение",
    "колледж",
    "университет",
    "институт",
    "школа",
)
EDUCATION_DEGREE_LABELS = (
    "degree",
    "qualification",
    "specialization",
    "major",
    "диплом",
    "специальность",
    "квалификация",
    "степень",
)
EDUCATION_DATE_LABELS = (
    "dates",
    "period",
    "date range",
    "study dates",
    "период",
    "даты",
    "период обучения",
    "срок обучения",
)
TITLE_ABBREVIATIONS = {
    "sr": "senior",
    "jr": "junior",
    "mgr": "manager",
    "asst": "assistant",
}
MONTH_ALIASES = {
    "jan": 1,
    "january": 1,
    "янв": 1,
    "январь": 1,
    "января": 1,
    "feb": 2,
    "february": 2,
    "фев": 2,
    "февраль": 2,
    "февраля": 2,
    "mar": 3,
    "march": 3,
    "мар": 3,
    "март": 3,
    "марта": 3,
    "apr": 4,
    "april": 4,
    "апр": 4,
    "апрель": 4,
    "апреля": 4,
    "may": 5,
    "май": 5,
    "мая": 5,
    "jun": 6,
    "june": 6,
    "июн": 6,
    "июнь": 6,
    "июня": 6,
    "jul": 7,
    "july": 7,
    "июл": 7,
    "июль": 7,
    "июля": 7,
    "aug": 8,
    "august": 8,
    "авг": 8,
    "август": 8,
    "августа": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "сен": 9,
    "сент": 9,
    "сентябрь": 9,
    "сентября": 9,
    "oct": 10,
    "october": 10,
    "окт": 10,
    "октябрь": 10,
    "октября": 10,
    "nov": 11,
    "november": 11,
    "ноя": 11,
    "нояб": 11,
    "ноябрь": 11,
    "ноября": 11,
    "dec": 12,
    "december": 12,
    "дек": 12,
    "декабрь": 12,
    "декабря": 12,
}
CURRENT_DATE_MARKERS = {
    "present",
    "current",
    "now",
    "ongoing",
    "today",
    "по настоящее время",
    "настоящее время",
    "по нв",
    "по н.в",
    "по н.в.",
    "нв",
    "н.в",
    "н.в.",
    "по сей день",
    "текущее время",
    "по текущий момент",
}
SECTION_HEADER_PATTERN = re.compile(r"\s+")
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d[\d\-\s\(\)]{7,}\d)")
EXPERIENCE_PATTERN = re.compile(r"(?P<years>\d{1,2})\+?\s*(?:years?|лет|года|год)\b", re.IGNORECASE)
DATE_WITH_MONTH_PATTERN = re.compile(
    r"^(?P<month>[A-Za-zА-Яа-яЁё\.]+)\s+(?P<year>\d{4})$|^(?P<year_first>\d{4})\s+"
    r"(?P<month_first>[A-Za-zА-Яа-яЁё\.]+)$"
)
MONTH_YEAR_NUMERIC_PATTERN = re.compile(r"^(?P<first>\d{1,4})[./-](?P<second>\d{1,4})$")
THREE_PART_DATE_PATTERN = re.compile(r"^\d{1,2}[./-]\d{1,2}[./-]\d{2,4}$")
RANGE_SEPARATOR_PATTERN = re.compile(r"\s+(?:to|until|по|до)\s+|\s*[-–—]\s*")


def validate_cv_payload(
    *,
    filename: str,
    mime_type: str,
    content: bytes,
    checksum_sha256: str,
    allowed_mime_types: tuple[str, ...],
    max_size_bytes: int,
) -> CVValidationResult:
    """Validate CV upload payload.

    Args:
        filename: Uploaded filename.
        mime_type: Uploaded MIME type.
        content: Uploaded binary content.
        checksum_sha256: Client-provided SHA-256 checksum.
        allowed_mime_types: Allowed MIME type whitelist.
        max_size_bytes: Maximum payload size.

    Returns:
        CVValidationResult: Normalized and validated CV payload.

    Raises:
        HTTPException: If validation fails.
    """
    normalized_filename = filename.strip()
    if not normalized_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must be non-empty",
        )

    normalized_mime = mime_type.strip().lower()
    if normalized_mime not in {item.lower() for item in allowed_mime_types}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported CV MIME type: {normalized_mime}",
        )

    size_bytes = len(content)
    if size_bytes <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CV file is empty",
        )
    if size_bytes > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"CV exceeds max size ({max_size_bytes} bytes)",
        )

    expected_checksum = checksum_sha256.strip().lower()
    calculated_checksum = hashlib.sha256(content).hexdigest()
    if expected_checksum != calculated_checksum:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="CV checksum mismatch",
        )

    return CVValidationResult(
        content=content,
        mime_type=normalized_mime,
        checksum_sha256=calculated_checksum,
        size_bytes=size_bytes,
    )


def extract_document_text(*, content: bytes, mime_type: str) -> ExtractedDocumentText:
    """Extract native text from one supported CV document.

    Args:
        content: Raw CV binary payload.
        mime_type: Validated document MIME type.

    Returns:
        ExtractedDocumentText: Unified extracted text plus page traceability metadata.

    Raises:
        ValueError: If the document cannot be parsed or yields no text.
    """
    normalized_mime = mime_type.strip().lower()
    if normalized_mime == PDF_MIME_TYPE:
        return extract_pdf_text(content=content)
    if normalized_mime == DOCX_MIME_TYPE:
        return extract_docx_text(content=content)
    raise ValueError(f"CV text extraction failed: unsupported MIME type {normalized_mime}")


def extract_pdf_text(*, content: bytes) -> ExtractedDocumentText:
    """Extract text from one PDF payload using native PDF parsing.

    Args:
        content: Raw PDF binary payload.

    Returns:
        ExtractedDocumentText: Unified extracted text with per-page offset mapping.

    Raises:
        ValueError: If the PDF is unreadable or does not contain extractable text.
    """
    try:
        reader = PdfReader(BytesIO(content), strict=False)
    except PdfReadError as exc:
        raise ValueError("CV text extraction failed: unreadable PDF") from exc
    except Exception as exc:  # noqa: BLE001
        raise ValueError("CV text extraction failed: PDF parser error") from exc

    page_fragments: list[tuple[int | None, str]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        try:
            raw_text = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001
            raise ValueError(
                f"CV text extraction failed: unreadable PDF page {page_number}"
            ) from exc
        normalized_text = _normalize_extracted_text(raw_text)
        if normalized_text:
            page_fragments.append((page_number, normalized_text))

    return _build_extracted_document_text(page_fragments)


def extract_docx_text(*, content: bytes) -> ExtractedDocumentText:
    """Extract text from one DOCX payload using native OOXML parsing.

    Args:
        content: Raw DOCX binary payload.

    Returns:
        ExtractedDocumentText: Unified extracted text ready for downstream normalization.

    Raises:
        ValueError: If the DOCX archive is invalid or does not contain extractable text.
    """
    try:
        with ZipFile(BytesIO(content)) as archive:
            part_names = _list_docx_text_parts(archive.namelist())
            fragments: list[tuple[int | None, str]] = []
            for part_name in part_names:
                normalized_text = _normalize_extracted_text(
                    _extract_docx_part_text(archive.read(part_name))
                )
                if normalized_text:
                    fragments.append((None, normalized_text))
    except BadZipFile as exc:
        raise ValueError("CV text extraction failed: unreadable DOCX archive") from exc
    except ElementTree.ParseError as exc:
        raise ValueError("CV text extraction failed: invalid DOCX XML") from exc

    return _build_extracted_document_text(fragments)


def parse_cv_document(*, content: bytes, mime_type: str) -> CVParseResult:
    """Parse CV bytes into canonical profile and evidence payload.

    Args:
        content: CV binary payload.
        mime_type: Document MIME type.

    Returns:
        CVParseResult: Canonical profile + evidence and language marker.

    Raises:
        ValueError: If parsing fails.
    """
    extracted_text = extract_document_text(content=content, mime_type=mime_type)
    normalized_text = extracted_text.text

    detected_language = detect_cv_language(normalized_text)
    evidence: list[dict[str, object]] = []

    full_name = extract_full_name(
        normalized_text,
        evidence,
        page_spans=extracted_text.page_spans,
    )
    emails = extract_emails(
        normalized_text,
        evidence,
        page_spans=extracted_text.page_spans,
    )
    phones = extract_phones(
        normalized_text,
        evidence,
        page_spans=extracted_text.page_spans,
    )
    years_total = extract_years_of_experience(
        normalized_text,
        evidence,
        page_spans=extracted_text.page_spans,
    )
    workplace_entries = extract_workplace_entries(
        normalized_text,
        evidence,
        page_spans=extracted_text.page_spans,
    )
    education_entries = extract_education_entries(
        normalized_text,
        evidence,
        page_spans=extracted_text.page_spans,
    )
    titles = build_titles(
        workplace_entries,
        normalized_text,
        evidence,
        page_spans=extracted_text.page_spans,
    )
    skills = extract_skills(
        normalized_text,
        evidence,
        page_spans=extracted_text.page_spans,
    )

    serialized_workplaces = [_serialize_workplace_entry(entry) for entry in workplace_entries]
    parsed_profile: dict[str, object] = {
        "document": {
            "mime_type": mime_type,
            "size_bytes": len(content),
            "detected_language": detected_language,
        },
        "personal": {
            "full_name": full_name,
        },
        "contact": {
            "emails": emails,
            "phones": phones,
        },
        "skills": skills,
        "experience": {
            "years_total": years_total,
            "entries": serialized_workplaces,
        },
        "workplaces": {
            "entries": serialized_workplaces,
        },
        "education": {
            "entries": [_serialize_education_entry(entry) for entry in education_entries],
        },
        "titles": titles,
        "summary": build_summary(normalized_text),
    }
    if not evidence:
        summary = parsed_profile["summary"]
        if isinstance(summary, str) and summary:
            append_evidence(
                evidence,
                field="summary",
                snippet=summary,
                start_offset=0,
                end_offset=min(len(summary), len(normalized_text)),
                page=extracted_text.resolve_page(
                    start_offset=0,
                    end_offset=min(len(summary), len(normalized_text)),
                ),
            )
    return CVParseResult(
        parsed_profile=parsed_profile,
        evidence=evidence,
        detected_language=detected_language,
    )


def _build_extracted_document_text(
    fragments: list[tuple[int | None, str]],
) -> ExtractedDocumentText:
    """Build unified extracted text and offset mapping from ordered fragments.

    Args:
        fragments: Ordered `(page, text)` fragments from a native extractor.

    Returns:
        ExtractedDocumentText: Unified text plus offset spans.

    Raises:
        ValueError: If no non-empty fragments are available.
    """
    if not fragments:
        raise ValueError("CV text extraction failed: empty textual payload")

    parts: list[str] = []
    spans: list[ExtractedTextSpan] = []
    cursor = 0
    for page, text in fragments:
        if parts:
            parts.append("\n\n")
            cursor += 2
        start_offset = cursor
        parts.append(text)
        cursor += len(text)
        spans.append(
            ExtractedTextSpan(
                start_offset=start_offset,
                end_offset=cursor,
                page=page,
            )
        )
    return ExtractedDocumentText(text="".join(parts), page_spans=tuple(spans))


def _normalize_extracted_text(text: str) -> str:
    """Normalize extractor output into stable text for downstream parsing.

    Args:
        text: Raw text emitted by document extractor.

    Returns:
        str: Trimmed text with normalized line endings and blank-line runs.
    """
    normalized = (
        text.replace("\x00", " ")
        .replace("\xa0", " ")
        .replace("\r", "\n")
        .replace("\x0c", "\n")
    )
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _list_docx_text_parts(part_names: list[str]) -> list[str]:
    """Return DOCX XML parts that may contain user-visible text.

    Args:
        part_names: Archive member names from one DOCX file.

    Returns:
        list[str]: Ordered XML part names to read for text extraction.

    Raises:
        ValueError: If the required main document part is missing.
    """
    if "word/document.xml" not in part_names:
        raise ValueError("CV text extraction failed: DOCX document part is missing")
    headers = sorted(name for name in part_names if re.fullmatch(r"word/header\d+\.xml", name))
    footers = sorted(name for name in part_names if re.fullmatch(r"word/footer\d+\.xml", name))
    extras = [name for name in ("word/footnotes.xml", "word/endnotes.xml") if name in part_names]
    return [*headers, "word/document.xml", *footers, *extras]


def _extract_docx_part_text(xml_bytes: bytes) -> str:
    """Extract ordered paragraph text from one DOCX XML part.

    Args:
        xml_bytes: Raw XML bytes from one DOCX archive member.

    Returns:
        str: Joined paragraph text from the XML part.
    """
    root = ElementTree.fromstring(xml_bytes)
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", DOCX_NAMESPACE):
        paragraph_text = _extract_docx_paragraph_text(paragraph)
        if paragraph_text.strip():
            paragraphs.append(paragraph_text.strip())
    return "\n".join(paragraphs)


def _extract_docx_paragraph_text(paragraph: ElementTree.Element) -> str:
    """Extract visible text from one DOCX paragraph element.

    Args:
        paragraph: DOCX paragraph XML element.

    Returns:
        str: Visible paragraph text with line/tab markers preserved.
    """
    chunks: list[str] = []
    for element in paragraph.iter():
        local_name = element.tag.rsplit("}", 1)[-1]
        if local_name == "t" and element.text:
            chunks.append(element.text)
        elif local_name == "tab":
            chunks.append("\t")
        elif local_name in {"br", "cr"}:
            chunks.append("\n")
    return "".join(chunks)


def resolve_page_number(
    page_spans: tuple[ExtractedTextSpan, ...],
    *,
    start_offset: int,
    end_offset: int,
) -> int | None:
    """Resolve evidence offsets to a page number when extracted text is paginated.

    Args:
        page_spans: Ordered page-to-offset mapping spans.
        start_offset: Inclusive evidence start offset.
        end_offset: Exclusive evidence end offset.

    Returns:
        int | None: One-based page number if the range overlaps a page span.
    """
    for span in page_spans:
        if start_offset < span.end_offset and end_offset > span.start_offset:
            return span.page
    return None


def detect_cv_language(text: str) -> DetectedCVLanguage:
    """Detect dominant CV language from alphabet distribution.

    Args:
        text: Decoded CV text.

    Returns:
        DetectedCVLanguage: One of `ru`, `en`, `mixed`, `unknown`.
    """
    sanitized = EMAIL_PATTERN.sub(" ", text.lower())
    cyr_count = sum(1 for char in sanitized if "а" <= char <= "я" or char == "ё")
    lat_count = sum(1 for char in sanitized if "a" <= char <= "z")
    if cyr_count == 0 and lat_count == 0:
        return "unknown"
    if cyr_count == 0:
        return "en"
    if lat_count == 0:
        return "ru"
    ratio = min(cyr_count, lat_count) / max(cyr_count, lat_count)
    if min(cyr_count, lat_count) >= 15 and ratio >= 0.35:
        return "mixed"
    return "ru" if cyr_count > lat_count else "en"


def extract_full_name(
    text: str,
    evidence: list[dict[str, object]],
    *,
    page_spans: tuple[ExtractedTextSpan, ...] = (),
) -> str | None:
    """Extract likely full name from CV header lines.

    Args:
        text: Decoded CV text.
        evidence: Mutable evidence accumulator.
        page_spans: Optional source page mapping for evidence ranges.

    Returns:
        str | None: Extracted full name candidate.
    """
    offset = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        line_start = offset + raw_line.find(line) if line else offset
        line_end = line_start + len(line)
        offset += len(raw_line) + 1
        if not line or "@" in line:
            continue
        words = [token for token in re.split(r"\s+", line) if token]
        if not 2 <= len(words) <= 4:
            continue
        if not re.fullmatch(r"[A-Za-zА-Яа-яЁё'\- ]{3,120}", line):
            continue
        append_evidence(
            evidence,
            field="personal.full_name",
            snippet=line,
            start_offset=line_start,
            end_offset=line_end,
            page=resolve_page_number(
                page_spans,
                start_offset=line_start,
                end_offset=line_end,
            ),
        )
        return line
    return None


def extract_emails(
    text: str,
    evidence: list[dict[str, object]],
    *,
    page_spans: tuple[ExtractedTextSpan, ...] = (),
) -> list[str]:
    """Extract and normalize e-mail addresses from CV text.

    Args:
        text: Decoded CV text.
        evidence: Mutable evidence accumulator.
        page_spans: Optional source page mapping for evidence ranges.

    Returns:
        list[str]: Distinct normalized e-mail values.
    """
    unique: list[str] = []
    seen: set[str] = set()
    for match in EMAIL_PATTERN.finditer(text):
        normalized = match.group(0).strip().lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
        append_evidence(
            evidence,
            field="contact.emails",
            snippet=build_line_snippet(text, match.start(), match.end()),
            start_offset=match.start(),
            end_offset=match.end(),
            page=resolve_page_number(
                page_spans,
                start_offset=match.start(),
                end_offset=match.end(),
            ),
        )
    return unique


def extract_phones(
    text: str,
    evidence: list[dict[str, object]],
    *,
    page_spans: tuple[ExtractedTextSpan, ...] = (),
) -> list[str]:
    """Extract and normalize phone numbers from CV text.

    Args:
        text: Decoded CV text.
        evidence: Mutable evidence accumulator.
        page_spans: Optional source page mapping for evidence ranges.

    Returns:
        list[str]: Distinct normalized phone values.
    """
    unique: list[str] = []
    seen: set[str] = set()
    for match in PHONE_PATTERN.finditer(text):
        if _looks_like_date_fragment(match.group(0)):
            continue
        normalized = normalize_phone(match.group(0))
        if len(normalized) < 8 or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
        append_evidence(
            evidence,
            field="contact.phones",
            snippet=build_line_snippet(text, match.start(), match.end()),
            start_offset=match.start(),
            end_offset=match.end(),
            page=resolve_page_number(
                page_spans,
                start_offset=match.start(),
                end_offset=match.end(),
            ),
        )
    return unique


def extract_years_of_experience(
    text: str,
    evidence: list[dict[str, object]],
    *,
    page_spans: tuple[ExtractedTextSpan, ...] = (),
) -> int | None:
    """Extract total experience years from CV text.

    Args:
        text: Decoded CV text.
        evidence: Mutable evidence accumulator.
        page_spans: Optional source page mapping for evidence ranges.

    Returns:
        int | None: Parsed years value when present.
    """
    match = EXPERIENCE_PATTERN.search(text)
    if match is None:
        return None
    years = int(match.group("years"))
    append_evidence(
        evidence,
        field="experience.years_total",
        snippet=build_line_snippet(text, match.start(), match.end()),
        start_offset=match.start(),
        end_offset=match.end(),
        page=resolve_page_number(
            page_spans,
            start_offset=match.start(),
            end_offset=match.end(),
        ),
    )
    return years


def extract_workplace_entries(
    text: str,
    evidence: list[dict[str, object]],
    *,
    page_spans: tuple[ExtractedTextSpan, ...] = (),
) -> list[WorkplaceEntry]:
    """Extract structured workplace history from CV text.

    Args:
        text: Decoded CV text.
        evidence: Mutable evidence accumulator.
        page_spans: Optional source page mapping for evidence ranges.

    Returns:
        list[WorkplaceEntry]: Parsed workplace entries in source order.
    """
    section_lines = _extract_section_lines(text, "workplaces")
    if not section_lines:
        return []

    entries: list[WorkplaceEntry] = []
    groups = _group_section_lines(section_lines, _is_workplace_entry_start)
    for index, group in enumerate(groups):
        entry = _parse_workplace_group(group)
        if entry is None:
            continue
        entries.append(entry)
        _append_workplace_entry_evidence(
            text=text,
            evidence=evidence,
            entry=entry,
            page_spans=page_spans,
            index=index,
            prefixes=(
                f"experience.entries[{index}]",
                f"workplaces.entries[{index}]",
            ),
        )
    return entries


def extract_education_entries(
    text: str,
    evidence: list[dict[str, object]],
    *,
    page_spans: tuple[ExtractedTextSpan, ...] = (),
) -> list[EducationEntry]:
    """Extract structured education history from CV text.

    Args:
        text: Decoded CV text.
        evidence: Mutable evidence accumulator.
        page_spans: Optional source page mapping for evidence ranges.

    Returns:
        list[EducationEntry]: Parsed education entries in source order.
    """
    section_lines = _extract_section_lines(text, "education")
    if not section_lines:
        return []

    entries: list[EducationEntry] = []
    groups = _group_section_lines(section_lines, _is_education_entry_start)
    for index, group in enumerate(groups):
        entry = _parse_education_group(group)
        if entry is None:
            continue
        entries.append(entry)
        _append_education_entry_evidence(
            text=text,
            evidence=evidence,
            entry=entry,
            page_spans=page_spans,
            index=index,
        )
    return entries


def build_titles(
    workplace_entries: list[WorkplaceEntry],
    text: str,
    evidence: list[dict[str, object]],
    *,
    page_spans: tuple[ExtractedTextSpan, ...] = (),
) -> dict[str, object]:
    """Build aggregated current and past titles from workplace positions.

    Args:
        workplace_entries: Parsed workplace entries.
        text: Decoded CV text.
        evidence: Mutable evidence accumulator.
        page_spans: Optional source page mapping for evidence ranges.

    Returns:
        dict[str, object]: Current and past normalized title payload.
    """
    current_position: LocatedValue | None = None
    past_positions: list[LocatedValue] = []

    for entry in workplace_entries:
        if entry.position is None:
            continue
        if (
            current_position is None
            and entry.date_range is not None
            and entry.date_range.is_current
        ):
            current_position = entry.position
            continue
        past_positions.append(entry.position)

    if current_position is None and past_positions:
        current_position = past_positions.pop(0)

    if current_position is not None:
        _append_located_evidence(
            text=text,
            evidence=evidence,
            located=current_position,
            field="titles.current.raw",
            page_spans=page_spans,
        )
    for index, position in enumerate(past_positions):
        _append_located_evidence(
            text=text,
            evidence=evidence,
            located=position,
            field=f"titles.past[{index}].raw",
            page_spans=page_spans,
        )

    return {
        "current": None if current_position is None else _serialize_position(current_position),
        "past": [_serialize_position(position) for position in past_positions],
    }


def extract_skills(
    text: str,
    evidence: list[dict[str, object]],
    *,
    page_spans: tuple[ExtractedTextSpan, ...] = (),
) -> list[str]:
    """Extract profession-agnostic skills with backward-safe IT fallback matching.

    Args:
        text: Decoded CV text.
        evidence: Mutable evidence accumulator.
        page_spans: Optional source page mapping for evidence ranges.

    Returns:
        list[str]: Sorted normalized skill identifiers or phrases.
    """
    extracted: dict[str, LocatedValue] = {}
    section_lines = _extract_section_lines(text, "skills")
    for line in section_lines:
        if not line.text:
            continue
        for item in _extract_skill_items_from_line(line):
            normalized = normalize_skill_value(item.value)
            if normalized is None or normalized in extracted:
                continue
            extracted[normalized] = item

    for canonical_skill, synonyms in SKILL_SYNONYMS.items():
        for synonym in synonyms:
            pattern = build_skill_pattern(synonym)
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match is None or canonical_skill in extracted:
                continue
            extracted[canonical_skill] = LocatedValue(
                value=match.group(0).strip(),
                start_offset=match.start(),
                end_offset=match.end(),
            )
            break

    skills = sorted(extracted)
    for index, skill in enumerate(skills):
        located = extracted[skill]
        _append_located_evidence(
            text=text,
            evidence=evidence,
            located=located,
            field=f"skills[{index}]",
            page_spans=page_spans,
        )
    return skills


def build_skill_pattern(synonym: str) -> str:
    """Create regex boundary-safe pattern for one skill synonym.

    Args:
        synonym: Skill token or phrase.

    Returns:
        str: Regex pattern string.
    """
    escaped = re.escape(synonym.strip().lower())
    return rf"(?<!\w){escaped}(?!\w)"


def normalize_phone(raw_phone: str) -> str:
    """Normalize phone value to compact sign+digits representation.

    Args:
        raw_phone: Raw phone fragment from CV text.

    Returns:
        str: Normalized phone number.
    """
    has_plus = raw_phone.strip().startswith("+")
    digits = "".join(char for char in raw_phone if char.isdigit())
    if not digits:
        return ""
    return f"+{digits}" if has_plus else digits


def build_summary(text: str) -> str:
    """Build compact summary snippet from first textual lines.

    Args:
        text: Decoded CV text.

    Returns:
        str: Truncated summary text.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    summary = " ".join(lines[:3]).strip()
    return summary[:280]


def build_line_snippet(text: str, start_offset: int, end_offset: int) -> str:
    """Extract line-level snippet around one match interval.

    Args:
        text: Source text.
        start_offset: Match start offset in source text.
        end_offset: Match end offset in source text.

    Returns:
        str: Human-readable line snippet for explainability.
    """
    line_start = text.rfind("\n", 0, start_offset)
    line_end = text.find("\n", end_offset)
    if line_start < 0:
        line_start = 0
    else:
        line_start += 1
    if line_end < 0:
        line_end = len(text)
    snippet = text[line_start:line_end].strip()
    if snippet:
        return snippet[:400]
    return text[start_offset:end_offset].strip()[:400]


def append_evidence(
    evidence: list[dict[str, object]],
    *,
    field: str,
    snippet: str,
    start_offset: int,
    end_offset: int,
    page: int | None = None,
) -> None:
    """Append one evidence record to mutable accumulator.

    Args:
        evidence: Mutable evidence list.
        field: Canonical field path in parsed profile.
        snippet: Source snippet proving extracted field value.
        start_offset: Source start offset.
        end_offset: Source end offset.
        page: One-based source page number when known.
    """
    evidence.append(
        {
            "field": field,
            "snippet": snippet,
            "start_offset": start_offset,
            "end_offset": end_offset,
            "page": page,
        }
    )


def _build_text_lines(text: str) -> list[TextLine]:
    """Split normalized text into stripped lines while preserving offsets."""
    lines: list[TextLine] = []
    cursor = 0
    raw_lines = text.split("\n")
    for index, raw_line in enumerate(raw_lines):
        stripped = raw_line.strip()
        if stripped:
            start_offset = cursor + raw_line.find(stripped)
            end_offset = start_offset + len(stripped)
        else:
            start_offset = cursor
            end_offset = cursor
        lines.append(
            TextLine(
                text=stripped,
                start_offset=start_offset,
                end_offset=end_offset,
            )
        )
        cursor += len(raw_line)
        if index < len(raw_lines) - 1:
            cursor += 1
    return lines


def _extract_section_lines(text: str, section_name: str) -> tuple[TextLine, ...]:
    """Extract lines belonging to the first matching named section."""
    lines = _build_text_lines(text)
    collected: list[TextLine] = []
    inside_target = False
    for line in lines:
        matched_section, inline_content = _identify_section_header(line)
        if matched_section is not None:
            if inside_target:
                break
            if matched_section == section_name:
                inside_target = True
                if inline_content is not None and inline_content.text:
                    collected.append(inline_content)
            continue
        if inside_target:
            collected.append(line)
    return tuple(collected)


def _identify_section_header(line: TextLine) -> tuple[str | None, TextLine | None]:
    """Return matched section name and inline content when one line contains both."""
    if not line.text:
        return None, None
    normalized = _normalize_header_value(line.text)
    for section_name, aliases in SECTION_HEADERS.items():
        if normalized in aliases:
            return section_name, None
    for section_name, aliases in SECTION_HEADERS.items():
        for alias in aliases:
            match = re.match(
                rf"^{re.escape(alias)}\s*[:\-–—]\s*(?P<content>.+?)\s*$",
                line.text,
                flags=re.IGNORECASE,
            )
            if match is None:
                continue
            content = match.group("content").strip()
            if not content:
                return section_name, None
            return (
                section_name,
                TextLine(
                    text=content,
                    start_offset=line.start_offset + match.start("content"),
                    end_offset=line.start_offset + match.end("content"),
                ),
            )
    return None, None


def _normalize_header_value(value: str) -> str:
    """Normalize a section header string for alias matching."""
    normalized = value.strip().lower()
    normalized = normalized.rstrip(":")
    normalized = SECTION_HEADER_PATTERN.sub(" ", normalized)
    return normalized.strip()


def _group_section_lines(
    section_lines: tuple[TextLine, ...],
    entry_start_predicate,
) -> list[tuple[TextLine, ...]]:
    """Group section lines into entry-sized blocks using blank lines and obvious starts."""
    groups: list[tuple[TextLine, ...]] = []
    current: list[TextLine] = []
    for line in section_lines:
        if not line.text:
            if current:
                groups.append(tuple(current))
                current = []
            continue
        if current and entry_start_predicate(line):
            groups.append(tuple(current))
            current = [line]
            continue
        current.append(line)
    if current:
        groups.append(tuple(current))
    return groups


def _is_workplace_entry_start(line: TextLine) -> bool:
    """Return whether a line looks like the first line of a workplace entry."""
    return _is_compact_entry_line(line) or _extract_labeled_value(
        line,
        WORKPLACE_EMPLOYER_LABELS,
    ) is not None


def _is_education_entry_start(line: TextLine) -> bool:
    """Return whether a line looks like the first line of an education entry."""
    return _is_compact_entry_line(line) or _extract_labeled_value(
        line,
        EDUCATION_INSTITUTION_LABELS,
    ) is not None


def _is_compact_entry_line(line: TextLine) -> bool:
    """Return whether a line contains a pipe-separated record with a date component."""
    segments = _split_pipe_segments(line)
    if len(segments) < 3:
        return False
    return any(_looks_like_date_fragment(segment.value) for segment in segments)


def _parse_workplace_group(group: tuple[TextLine, ...]) -> WorkplaceEntry | None:
    """Parse one grouped workplace block into a structured entry."""
    employer: LocatedValue | None = None
    position: LocatedValue | None = None
    date_range: ParsedDateRange | None = None
    summary_parts: list[LocatedValue] = []
    consumed_indices: set[int] = set()

    for index, line in enumerate(group):
        compact_entry = _parse_compact_workplace_line(line)
        if compact_entry is not None:
            employer = compact_entry["employer"]
            position = compact_entry["position"]
            date_range = compact_entry["date_range"]
            inline_summary = compact_entry["summary"]
            if inline_summary is not None:
                summary_parts.append(inline_summary)
            consumed_indices.add(index)
            break

    for index, line in enumerate(group):
        if index in consumed_indices or not line.text:
            continue
        if employer is None:
            employer = _extract_labeled_value(line, WORKPLACE_EMPLOYER_LABELS)
            if employer is not None:
                consumed_indices.add(index)
                continue
        if position is None:
            position = _extract_labeled_value(line, WORKPLACE_POSITION_LABELS)
            if position is not None:
                consumed_indices.add(index)
                continue
        if date_range is None:
            date_value = _extract_labeled_value(line, WORKPLACE_DATE_LABELS)
            if date_value is not None:
                date_range = _build_parsed_date_range(date_value)
                consumed_indices.add(index)
                continue

    for index, line in enumerate(group):
        if index in consumed_indices or not line.text:
            continue
        summary_parts.append(LocatedValue(line.text, line.start_offset, line.end_offset))

    if employer is None and position is None and date_range is None and not summary_parts:
        return None
    if employer is None or position is None:
        return None
    return WorkplaceEntry(
        employer=employer,
        position=position,
        date_range=date_range,
        summary=_combine_located_values(summary_parts),
    )


def _parse_education_group(group: tuple[TextLine, ...]) -> EducationEntry | None:
    """Parse one grouped education block into a structured entry."""
    institution: LocatedValue | None = None
    degree: LocatedValue | None = None
    date_range: ParsedDateRange | None = None
    summary_parts: list[LocatedValue] = []
    consumed_indices: set[int] = set()

    for index, line in enumerate(group):
        compact_entry = _parse_compact_education_line(line)
        if compact_entry is not None:
            institution = compact_entry["institution"]
            degree = compact_entry["degree"]
            date_range = compact_entry["date_range"]
            inline_summary = compact_entry["summary"]
            if inline_summary is not None:
                summary_parts.append(inline_summary)
            consumed_indices.add(index)
            break

    for index, line in enumerate(group):
        if index in consumed_indices or not line.text:
            continue
        if institution is None:
            institution = _extract_labeled_value(line, EDUCATION_INSTITUTION_LABELS)
            if institution is not None:
                consumed_indices.add(index)
                continue
        if degree is None:
            degree = _extract_labeled_value(line, EDUCATION_DEGREE_LABELS)
            if degree is not None:
                consumed_indices.add(index)
                continue
        if date_range is None:
            date_value = _extract_labeled_value(line, EDUCATION_DATE_LABELS)
            if date_value is not None:
                date_range = _build_parsed_date_range(date_value)
                consumed_indices.add(index)
                continue

    for index, line in enumerate(group):
        if index in consumed_indices or not line.text:
            continue
        summary_parts.append(LocatedValue(line.text, line.start_offset, line.end_offset))

    if institution is None and degree is None and date_range is None and not summary_parts:
        return None
    if institution is None or degree is None:
        return None
    return EducationEntry(
        institution=institution,
        degree=degree,
        date_range=date_range,
        summary=_combine_located_values(summary_parts),
    )


def _parse_compact_workplace_line(line: TextLine) -> dict[str, object] | None:
    """Parse one pipe-separated workplace entry line."""
    segments = _split_pipe_segments(line)
    if len(segments) < 3:
        return None
    return _parse_compact_entry_segments(
        segments,
        first_field="employer",
        second_field="position",
    )


def _parse_compact_education_line(line: TextLine) -> dict[str, object] | None:
    """Parse one pipe-separated education entry line."""
    segments = _split_pipe_segments(line)
    if len(segments) < 3:
        return None
    return _parse_compact_entry_segments(
        segments,
        first_field="institution",
        second_field="degree",
    )


def _parse_compact_entry_segments(
    segments: list[LocatedValue],
    *,
    first_field: str,
    second_field: str,
) -> dict[str, object] | None:
    """Parse compact segments with one date part into a structured payload."""
    date_index: int | None = None
    date_range: ParsedDateRange | None = None
    for index, segment in enumerate(segments):
        if not _looks_like_date_fragment(segment.value):
            continue
        parsed = _build_parsed_date_range(segment)
        if parsed is None:
            continue
        date_index = index
        date_range = parsed
        break
    if date_index is None or date_range is None:
        return None

    non_date_segments = [segment for index, segment in enumerate(segments) if index != date_index]
    if len(non_date_segments) < 2:
        return None

    summary = _combine_located_values(non_date_segments[2:]) if len(non_date_segments) > 2 else None
    return {
        first_field: non_date_segments[0],
        second_field: non_date_segments[1],
        "date_range": date_range,
        "summary": summary,
    }


def _split_pipe_segments(line: TextLine) -> list[LocatedValue]:
    """Split one pipe-delimited line into located segments."""
    segments: list[LocatedValue] = []
    for match in re.finditer(r"[^|]+", line.text):
        segment = match.group(0)
        stripped = segment.strip()
        if not stripped:
            continue
        leading_ws = len(segment) - len(segment.lstrip())
        trailing_ws = len(segment) - len(segment.rstrip())
        start_offset = line.start_offset + match.start() + leading_ws
        end_offset = line.start_offset + match.end() - trailing_ws
        segments.append(
            LocatedValue(
                value=stripped,
                start_offset=start_offset,
                end_offset=end_offset,
            )
        )
    return segments


def _extract_labeled_value(line: TextLine, labels: tuple[str, ...]) -> LocatedValue | None:
    """Extract the value part of a labeled `Name: value` style line."""
    for label in labels:
        match = re.match(
            rf"^{re.escape(label)}\s*[:\-–—]\s*(?P<value>.+?)\s*$",
            line.text,
            flags=re.IGNORECASE,
        )
        if match is None:
            continue
        value = match.group("value").strip()
        if not value:
            return None
        return LocatedValue(
            value=value,
            start_offset=line.start_offset + match.start("value"),
            end_offset=line.start_offset + match.end("value"),
        )
    return None


def _combine_located_values(values: list[LocatedValue]) -> LocatedValue | None:
    """Combine multiple located values into one joined span."""
    if not values:
        return None
    combined = " ".join(value.value for value in values if value.value).strip()
    if not combined:
        return None
    return LocatedValue(
        value=combined,
        start_offset=values[0].start_offset,
        end_offset=values[-1].end_offset,
    )


def _build_parsed_date_range(value: LocatedValue) -> ParsedDateRange | None:
    """Build parsed date range metadata from one raw located value."""
    if not value.value.strip():
        return None
    start, end, is_current = normalize_date_range(value.value)
    if (
        start is None
        and end is None
        and not is_current
        and not _looks_like_date_fragment(value.value)
    ):
        return None
    return ParsedDateRange(
        raw=value,
        start=start,
        end=end,
        is_current=is_current,
    )


def normalize_date_range(raw_value: str) -> tuple[str | None, str | None, bool]:
    """Normalize one free-form date or date range into ISO-like string values."""
    cleaned = raw_value.strip()
    if not cleaned:
        return None, None, False
    single_value = normalize_date_token(cleaned)
    if single_value is not None:
        return single_value, None, False

    match = RANGE_SEPARATOR_PATTERN.search(cleaned)
    if match is None:
        return None, None, _is_current_marker(cleaned)

    start_raw = cleaned[: match.start()].strip()
    end_raw = cleaned[match.end() :].strip()
    if not start_raw and not end_raw:
        return None, None, False
    start = normalize_date_token(start_raw)
    end = normalize_date_token(end_raw)
    is_current = _is_current_marker(end_raw)
    if is_current:
        end = None
    return start, end, is_current


def normalize_date_token(raw_value: str) -> str | None:
    """Normalize one free-form date token into `YYYY` or `YYYY-MM`."""
    cleaned = raw_value.strip().lower()
    cleaned = re.sub(r"^(from|с)\s+", "", cleaned)
    cleaned = re.sub(r"\bг\.\b|\bгода\b|\bгод\b|\bг\b", "", cleaned).strip(" .")
    if not cleaned or _is_current_marker(cleaned):
        return None
    if THREE_PART_DATE_PATTERN.fullmatch(cleaned):
        return None
    if re.fullmatch(r"\d{4}", cleaned):
        return cleaned

    numeric_match = MONTH_YEAR_NUMERIC_PATTERN.fullmatch(cleaned)
    if numeric_match is not None:
        first = int(numeric_match.group("first"))
        second = int(numeric_match.group("second"))
        if first >= 1000 and 1 <= second <= 12:
            return f"{first:04d}-{second:02d}"
        if second >= 1000 and 1 <= first <= 12:
            return f"{second:04d}-{first:02d}"
        return None

    month_match = DATE_WITH_MONTH_PATTERN.fullmatch(cleaned)
    if month_match is not None:
        year = month_match.group("year") or month_match.group("year_first")
        month_name = month_match.group("month") or month_match.group("month_first")
        if year is None or month_name is None:
            return None
        month = MONTH_ALIASES.get(month_name.rstrip("."))
        if month is None:
            return None
        return f"{int(year):04d}-{month:02d}"

    return None


def normalize_title_value(raw_value: str) -> str | None:
    """Normalize one workplace title into a profession-agnostic canonical string."""
    normalized = raw_value.strip().lower()
    normalized = re.sub(r"[()]+", " ", normalized)
    normalized = re.sub(r"[.,/]+", " ", normalized)
    normalized = SECTION_HEADER_PATTERN.sub(" ", normalized).strip()
    if not normalized:
        return None
    parts = [TITLE_ABBREVIATIONS.get(part, part) for part in normalized.split()]
    normalized = " ".join(parts).strip()
    return normalized or None


def normalize_skill_value(raw_value: str) -> str | None:
    """Normalize one skill list item while preserving generic professions."""
    normalized = raw_value.strip().lower()
    normalized = normalized.strip(" .,:;")
    normalized = re.sub(r"^[•·\-]+\s*", "", normalized)
    normalized = SECTION_HEADER_PATTERN.sub(" ", normalized).strip()
    if len(normalized) < 2 or normalized.isdigit():
        return None
    for canonical_skill, synonyms in SKILL_SYNONYMS.items():
        if normalized == canonical_skill:
            return canonical_skill
        for synonym in synonyms:
            if normalized == synonym.lower():
                return canonical_skill
    return normalized


def _is_current_marker(raw_value: str) -> bool:
    """Return whether one date token represents an open-ended current period."""
    normalized = raw_value.strip().lower().strip(" .")
    normalized = SECTION_HEADER_PATTERN.sub(" ", normalized)
    return normalized in CURRENT_DATE_MARKERS


def _looks_like_date_fragment(raw_value: str) -> bool:
    """Return whether a raw fragment likely represents a date or date range."""
    cleaned = raw_value.strip().lower()
    cleaned = SECTION_HEADER_PATTERN.sub(" ", cleaned)
    if not cleaned:
        return False
    if _is_current_marker(cleaned):
        return True
    if re.search(r"\b(?:19|20)\d{2}\b", cleaned):
        return True
    if THREE_PART_DATE_PATTERN.fullmatch(cleaned):
        return True
    if MONTH_YEAR_NUMERIC_PATTERN.fullmatch(cleaned):
        return True
    if DATE_WITH_MONTH_PATTERN.fullmatch(cleaned):
        return True
    return any(month in cleaned.split() for month in MONTH_ALIASES)


def _serialize_workplace_entry(entry: WorkplaceEntry) -> dict[str, object]:
    """Serialize one workplace entry to JSON-compatible payload."""
    return {
        "employer": None if entry.employer is None else entry.employer.value,
        "position": None if entry.position is None else _serialize_position(entry.position),
        "date_range": None if entry.date_range is None else _serialize_date_range(entry.date_range),
        "summary": None if entry.summary is None else entry.summary.value,
    }


def _serialize_education_entry(entry: EducationEntry) -> dict[str, object]:
    """Serialize one education entry to JSON-compatible payload."""
    return {
        "institution": None if entry.institution is None else entry.institution.value,
        "degree": None if entry.degree is None else entry.degree.value,
        "date_range": None if entry.date_range is None else _serialize_date_range(entry.date_range),
        "summary": None if entry.summary is None else entry.summary.value,
    }


def _serialize_position(position: LocatedValue) -> dict[str, object]:
    """Serialize one raw position value to raw and normalized forms."""
    return {
        "raw": position.value,
        "normalized": normalize_title_value(position.value),
    }


def _serialize_date_range(date_range: ParsedDateRange) -> dict[str, object]:
    """Serialize one parsed date range to JSON-compatible payload."""
    return {
        "raw": date_range.raw.value,
        "start": date_range.start,
        "end": date_range.end,
        "is_current": date_range.is_current,
    }


def _append_workplace_entry_evidence(
    *,
    text: str,
    evidence: list[dict[str, object]],
    entry: WorkplaceEntry,
    page_spans: tuple[ExtractedTextSpan, ...],
    index: int,
    prefixes: tuple[str, ...],
) -> None:
    """Append evidence links for one workplace entry under all requested prefixes."""
    for prefix in prefixes:
        if entry.employer is not None:
            _append_located_evidence(
                text=text,
                evidence=evidence,
                located=entry.employer,
                field=f"{prefix}.employer",
                page_spans=page_spans,
            )
        if entry.position is not None:
            _append_located_evidence(
                text=text,
                evidence=evidence,
                located=entry.position,
                field=f"{prefix}.position.raw",
                page_spans=page_spans,
            )
        if entry.date_range is not None:
            _append_located_evidence(
                text=text,
                evidence=evidence,
                located=entry.date_range.raw,
                field=f"{prefix}.date_range.raw",
                page_spans=page_spans,
            )
        if entry.summary is not None:
            _append_located_evidence(
                text=text,
                evidence=evidence,
                located=entry.summary,
                field=f"{prefix}.summary",
                page_spans=page_spans,
            )


def _append_education_entry_evidence(
    *,
    text: str,
    evidence: list[dict[str, object]],
    entry: EducationEntry,
    page_spans: tuple[ExtractedTextSpan, ...],
    index: int,
) -> None:
    """Append evidence links for one education entry."""
    if entry.institution is not None:
        _append_located_evidence(
            text=text,
            evidence=evidence,
            located=entry.institution,
            field=f"education.entries[{index}].institution",
            page_spans=page_spans,
        )
    if entry.degree is not None:
        _append_located_evidence(
            text=text,
            evidence=evidence,
            located=entry.degree,
            field=f"education.entries[{index}].degree",
            page_spans=page_spans,
        )
    if entry.date_range is not None:
        _append_located_evidence(
            text=text,
            evidence=evidence,
            located=entry.date_range.raw,
            field=f"education.entries[{index}].date_range.raw",
            page_spans=page_spans,
        )
    if entry.summary is not None:
        _append_located_evidence(
            text=text,
            evidence=evidence,
            located=entry.summary,
            field=f"education.entries[{index}].summary",
            page_spans=page_spans,
        )


def _append_located_evidence(
    *,
    text: str,
    evidence: list[dict[str, object]],
    located: LocatedValue,
    field: str,
    page_spans: tuple[ExtractedTextSpan, ...],
) -> None:
    """Append one evidence record for a located raw value."""
    append_evidence(
        evidence,
        field=field,
        snippet=build_line_snippet(text, located.start_offset, located.end_offset),
        start_offset=located.start_offset,
        end_offset=located.end_offset,
        page=resolve_page_number(
            page_spans,
            start_offset=located.start_offset,
            end_offset=located.end_offset,
        ),
    )


def _extract_skill_items_from_line(line: TextLine) -> list[LocatedValue]:
    """Split one skills line into individual located items."""
    if not line.text:
        return []
    parts: list[LocatedValue] = []
    cursor = 0
    for raw_part in re.split(r"[,;•·]+", line.text):
        stripped = raw_part.strip()
        if stripped:
            start_offset = line.start_offset + line.text.find(stripped, cursor)
            end_offset = start_offset + len(stripped)
            parts.append(
                LocatedValue(
                    value=stripped,
                    start_offset=start_offset,
                    end_offset=end_offset,
                )
            )
            cursor = end_offset - line.start_offset
        else:
            cursor += len(raw_part) + 1
    if parts:
        return parts
    return [LocatedValue(line.text, line.start_offset, line.end_offset)]
