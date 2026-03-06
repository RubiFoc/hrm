"""Validation and parsing helpers for candidate CV processing."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException, status


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

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:\+?\d[\d\-\s\(\)]{7,}\d)")
EXPERIENCE_PATTERN = re.compile(r"(?P<years>\d{1,2})\+?\s*(?:years?|лет|года|год)\b", re.IGNORECASE)


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
    if content.startswith(b"FAIL_PARSE"):
        raise ValueError("CV parsing failed by deterministic test marker")

    text = content.decode("utf-8", errors="ignore")
    normalized_text = text.replace("\x00", " ").strip()
    if not normalized_text:
        raise ValueError("CV parsing failed: empty textual payload")

    detected_language = detect_cv_language(normalized_text)
    evidence: list[dict[str, object]] = []

    full_name = extract_full_name(normalized_text, evidence)
    emails = extract_emails(normalized_text, evidence)
    phones = extract_phones(normalized_text, evidence)
    years_total = extract_years_of_experience(normalized_text, evidence)
    skills = extract_skills(normalized_text, evidence)

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
        },
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
            )
    return CVParseResult(
        parsed_profile=parsed_profile,
        evidence=evidence,
        detected_language=detected_language,
    )


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


def extract_full_name(text: str, evidence: list[dict[str, object]]) -> str | None:
    """Extract likely full name from CV header lines.

    Args:
        text: Decoded CV text.
        evidence: Mutable evidence accumulator.

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
        )
        return line
    return None


def extract_emails(text: str, evidence: list[dict[str, object]]) -> list[str]:
    """Extract and normalize e-mail addresses from CV text.

    Args:
        text: Decoded CV text.
        evidence: Mutable evidence accumulator.

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
        )
    return unique


def extract_phones(text: str, evidence: list[dict[str, object]]) -> list[str]:
    """Extract and normalize phone numbers from CV text.

    Args:
        text: Decoded CV text.
        evidence: Mutable evidence accumulator.

    Returns:
        list[str]: Distinct normalized phone values.
    """
    unique: list[str] = []
    seen: set[str] = set()
    for match in PHONE_PATTERN.finditer(text):
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
        )
    return unique


def extract_years_of_experience(text: str, evidence: list[dict[str, object]]) -> int | None:
    """Extract total experience years from CV text.

    Args:
        text: Decoded CV text.
        evidence: Mutable evidence accumulator.

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
    )
    return years


def extract_skills(text: str, evidence: list[dict[str, object]]) -> list[str]:
    """Extract canonical skills using bilingual synonym matching.

    Args:
        text: Decoded CV text.
        evidence: Mutable evidence accumulator.

    Returns:
        list[str]: Sorted canonical skill identifiers.
    """
    normalized_text = text.lower()
    extracted: set[str] = set()
    for canonical_skill, synonyms in SKILL_SYNONYMS.items():
        for synonym in synonyms:
            pattern = build_skill_pattern(synonym)
            match = re.search(pattern, normalized_text, flags=re.IGNORECASE)
            if match is None:
                continue
            extracted.add(canonical_skill)
            append_evidence(
                evidence,
                field=f"skills.{canonical_skill}",
                snippet=build_line_snippet(text, match.start(), match.end()),
                start_offset=match.start(),
                end_offset=match.end(),
            )
            break
    return sorted(extracted)


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
) -> None:
    """Append one evidence record to mutable accumulator.

    Args:
        evidence: Mutable evidence list.
        field: Canonical field path in parsed profile.
        snippet: Source snippet proving extracted field value.
        start_offset: Source start offset.
        end_offset: Source end offset.
    """
    evidence.append(
        {
            "field": field,
            "snippet": snippet,
            "start_offset": start_offset,
            "end_offset": end_offset,
            "page": None,
        }
    )
