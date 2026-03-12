"""Dataset models and loaders for the scoring quality harness.

The quality harness intentionally operates on scoring-domain inputs after CV parsing instead of
replaying public upload or API flows. Dataset cases therefore store vacancy snapshots plus parsed
candidate document payloads that can be reconstructed into the existing scoring models in memory.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from hrm_backend.candidates.models.document import CandidateDocument
from hrm_backend.scoring.utils.result import MatchScoreResult
from hrm_backend.vacancies.models.vacancy import Vacancy

EvaluationMode = Literal["fixture", "ollama"]


def _normalize_requirement_label(value: str) -> str:
    """Normalize one requirement label for deterministic comparisons."""

    return " ".join(value.strip().casefold().split())


def _normalize_unique_string_list(value: object) -> list[str]:
    """Normalize list-like inputs into unique non-empty strings.

    Args:
        value: Raw value received from dataset JSON.

    Returns:
        list[str]: Ordered unique string values.

    Raises:
        ValueError: If the input is not a list.
    """

    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("must be a list")

    normalized_items: list[str] = []
    seen: set[str] = set()
    for raw_item in value:
        item = str(raw_item).strip()
        if not item:
            continue
        normalized_key = _normalize_requirement_label(item)
        if normalized_key in seen:
            continue
        normalized_items.append(item)
        seen.add(normalized_key)
    return normalized_items


class EvaluationVacancySnapshot(BaseModel):
    """Vacancy snapshot used as one scoring target during evaluation.

    Attributes:
        title: Recruiter-facing vacancy title.
        description: Vacancy description fed into the scoring prompt.
        department: Owning department label.
        status: Current vacancy lifecycle state.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=256)
    description: str = Field(min_length=1)
    department: str = Field(min_length=1, max_length=128)
    status: str = Field(default="open", min_length=1, max_length=32)

    @field_validator("title", "description", "department", "status")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        """Strip text fields and reject empty strings."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("must be non-empty")
        return normalized

    def to_vacancy_model(self, *, scenario_id: str) -> Vacancy:
        """Build an in-memory vacancy entity for the existing scoring adapter.

        Args:
            scenario_id: Dataset scenario identifier used for deterministic synthetic ids.

        Returns:
            Vacancy: SQLAlchemy vacancy model instantiated in memory only.
        """

        return Vacancy(
            vacancy_id=str(uuid5(NAMESPACE_URL, f"scoring-quality-vacancy:{scenario_id}")),
            title=self.title,
            description=self.description,
            department=self.department,
            status=self.status,
        )


class EvaluationDocumentSnapshot(BaseModel):
    """Parsed candidate document snapshot used by the quality harness.

    Attributes:
        filename: Display filename for the synthetic document.
        mime_type: Parsed document MIME type.
        detected_language: Stored parser language marker.
        parsed_at: Timestamp when parsing completed successfully.
        parsed_profile_json: Canonical parsed profile consumed by the scoring prompt.
        evidence_json: Evidence payload linked to parsed profile fields.
    """

    model_config = ConfigDict(extra="forbid")

    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=128)
    detected_language: str = Field(min_length=1, max_length=16)
    parsed_at: datetime
    parsed_profile_json: dict[str, object]
    evidence_json: list[dict[str, object]] = Field(default_factory=list)

    @field_validator("filename", "mime_type", "detected_language")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        """Strip text fields and reject empty strings."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("must be non-empty")
        return normalized

    @field_validator("parsed_at")
    @classmethod
    def _require_timezone(cls, value: datetime) -> datetime:
        """Reject naive timestamps so dataset snapshots stay unambiguous."""

        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("must include timezone information")
        return value

    def to_candidate_document_model(
        self,
        *,
        scenario_id: str,
        candidate_id: str,
    ) -> CandidateDocument:
        """Build an in-memory parsed candidate document for the scoring adapter.

        Args:
            scenario_id: Scenario identifier used to derive deterministic synthetic ids.
            candidate_id: Dataset candidate identifier used to derive synthetic ids.

        Returns:
            CandidateDocument: SQLAlchemy document model instantiated in memory only.
        """

        serialized_payload = json.dumps(
            {
                "candidate_id": candidate_id,
                "detected_language": self.detected_language,
                "evidence_json": self.evidence_json,
                "filename": self.filename,
                "mime_type": self.mime_type,
                "parsed_at": self.parsed_at.isoformat(),
                "parsed_profile_json": self.parsed_profile_json,
                "scenario_id": scenario_id,
            },
            ensure_ascii=True,
            sort_keys=True,
        ).encode("utf-8")
        checksum_sha256 = hashlib.sha256(serialized_payload).hexdigest()

        return CandidateDocument(
            document_id=str(
                uuid5(
                    NAMESPACE_URL,
                    f"scoring-quality-document:{scenario_id}:{candidate_id}",
                )
            ),
            candidate_id=str(uuid5(NAMESPACE_URL, f"scoring-quality-candidate:{candidate_id}")),
            object_key=f"scoring-quality/{scenario_id}/{candidate_id}/{self.filename}",
            filename=self.filename,
            mime_type=self.mime_type,
            size_bytes=len(serialized_payload),
            checksum_sha256=checksum_sha256,
            is_active=True,
            parsed_profile_json=self.parsed_profile_json,
            evidence_json=self.evidence_json,
            detected_language=self.detected_language,
            parsed_at=self.parsed_at,
            created_at=self.parsed_at,
        )


class EvaluationCandidateCase(BaseModel):
    """One candidate case inside one quality-harness scenario.

    Attributes:
        candidate_id: Stable dataset-level identifier used for ranking and paraphrase comparisons.
        document: Parsed document snapshot used for scoring.
        expected_relevance: Expected relevance grade in the `0..3` range for ranking metrics.
        expected_matched_requirements: Requirement labels expected to be satisfied.
        expected_missing_requirements: Requirement labels expected to be missing.
        fixture_prediction: Deterministic synthetic score payload used by fixture mode.
    """

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1, max_length=128)
    document: EvaluationDocumentSnapshot
    expected_relevance: int = Field(ge=0, le=3)
    expected_matched_requirements: list[str] = Field(default_factory=list)
    expected_missing_requirements: list[str] = Field(default_factory=list)
    fixture_prediction: MatchScoreResult | None = None

    @field_validator("candidate_id")
    @classmethod
    def _strip_candidate_id(cls, value: str) -> str:
        """Normalize candidate identifiers."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("must be non-empty")
        return normalized

    @field_validator(
        "expected_matched_requirements",
        "expected_missing_requirements",
        mode="before",
    )
    @classmethod
    def _normalize_requirement_lists(cls, value: object) -> list[str]:
        """Normalize requirement lists into deterministic unique strings."""

        return _normalize_unique_string_list(value)

    @model_validator(mode="after")
    def _validate_expected_sets(self) -> EvaluationCandidateCase:
        """Reject overlapping matched and missing expectations after normalization."""

        matched = {
            _normalize_requirement_label(item)
            for item in self.expected_matched_requirements
        }
        missing = {
            _normalize_requirement_label(item)
            for item in self.expected_missing_requirements
        }
        overlap = matched & missing
        if overlap:
            raise ValueError(
                "expected_matched_requirements and expected_missing_requirements must be disjoint"
            )
        return self


class EvaluationScenario(BaseModel):
    """One vacancy-scoring scenario evaluated by the quality harness.

    Attributes:
        scenario_id: Stable scenario identifier used in reports and paraphrase references.
        paraphrase_of: Optional base scenario id when this case is a paraphrase variant.
        vacancy: Vacancy snapshot scored against the candidate set.
        candidates: Candidate cases compared and ranked for this scenario.
    """

    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(min_length=1, max_length=128)
    paraphrase_of: str | None = Field(default=None, min_length=1, max_length=128)
    vacancy: EvaluationVacancySnapshot
    candidates: list[EvaluationCandidateCase] = Field(min_length=1)

    @field_validator("scenario_id", "paraphrase_of")
    @classmethod
    def _strip_ids(cls, value: str | None) -> str | None:
        """Normalize scenario identifiers while preserving null."""

        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("must be non-empty")
        return normalized

    @model_validator(mode="after")
    def _validate_candidate_ids(self) -> EvaluationScenario:
        """Ensure each scenario contains a unique candidate id set."""

        candidate_ids = [candidate.candidate_id for candidate in self.candidates]
        duplicates = sorted(
            {
                candidate_id
                for candidate_id in candidate_ids
                if candidate_ids.count(candidate_id) > 1
            }
        )
        if duplicates:
            raise ValueError(f"duplicate candidate ids: {', '.join(duplicates)}")
        return self


class ScoringQualityDataset(BaseModel):
    """Root dataset container for the scoring quality harness.

    Attributes:
        dataset_id: Stable dataset identifier shown in reports.
        scenarios: Ordered scenario collection validated as one consistent dataset.
    """

    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(min_length=1, max_length=128)
    scenarios: list[EvaluationScenario] = Field(min_length=1)

    @field_validator("dataset_id")
    @classmethod
    def _strip_dataset_id(cls, value: str) -> str:
        """Normalize dataset identifiers."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("must be non-empty")
        return normalized

    @model_validator(mode="after")
    def _validate_scenarios(self) -> ScoringQualityDataset:
        """Validate scenario-level uniqueness and paraphrase invariants."""

        scenario_map: dict[str, EvaluationScenario] = {}
        duplicates: list[str] = []
        for scenario in self.scenarios:
            if scenario.scenario_id in scenario_map:
                duplicates.append(scenario.scenario_id)
            scenario_map[scenario.scenario_id] = scenario
        if duplicates:
            unique_duplicates = ", ".join(sorted(set(duplicates)))
            raise ValueError(f"duplicate scenario ids: {unique_duplicates}")

        for scenario in self.scenarios:
            if scenario.paraphrase_of is None:
                continue
            if scenario.paraphrase_of == scenario.scenario_id:
                raise ValueError("paraphrase_of must reference a different scenario")
            base_scenario = scenario_map.get(scenario.paraphrase_of)
            if base_scenario is None:
                raise ValueError(
                    f"paraphrase_of must reference an existing scenario: {scenario.paraphrase_of}"
                )

            base_candidate_ids = {
                candidate.candidate_id for candidate in base_scenario.candidates
            }
            paraphrase_candidate_ids = {candidate.candidate_id for candidate in scenario.candidates}
            if base_candidate_ids != paraphrase_candidate_ids:
                raise ValueError(
                    "paraphrase scenario candidate ids must match the referenced base scenario"
                )
        return self

    def validate_for_mode(self, *, mode: EvaluationMode) -> ScoringQualityDataset:
        """Apply mode-specific validation that cannot be expressed in the static schema.

        Args:
            mode: Harness execution mode.

        Returns:
            ScoringQualityDataset: The same dataset after additional validation.

        Raises:
            ValueError: If the dataset is incompatible with the selected mode.
        """

        if mode == "fixture":
            for scenario in self.scenarios:
                for candidate in scenario.candidates:
                    if candidate.fixture_prediction is None:
                        raise ValueError(
                            "fixture mode requires fixture_prediction for "
                            f"{scenario.scenario_id}/{candidate.candidate_id}"
                        )
        return self


def load_scoring_quality_dataset(
    path: str | Path,
    *,
    mode: EvaluationMode,
) -> ScoringQualityDataset:
    """Load and validate one scoring quality dataset from disk.

    Args:
        path: Filesystem path to a JSON dataset file.
        mode: Harness mode used for mode-specific validation.

    Returns:
        ScoringQualityDataset: Validated dataset object.

    Raises:
        ValueError: If the file cannot be parsed or validated.
    """

    dataset_path = Path(path)
    try:
        raw_payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"dataset file not found: {dataset_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"dataset file is not valid JSON: {dataset_path}") from exc

    try:
        dataset = ScoringQualityDataset.model_validate(raw_payload)
    except ValidationError as exc:
        raise ValueError(f"dataset validation failed for {dataset_path}: {exc}") from exc

    return dataset.validate_for_mode(mode=mode)


__all__ = [
    "EvaluationCandidateCase",
    "EvaluationDocumentSnapshot",
    "EvaluationMode",
    "EvaluationScenario",
    "EvaluationVacancySnapshot",
    "ScoringQualityDataset",
    "load_scoring_quality_dataset",
]
