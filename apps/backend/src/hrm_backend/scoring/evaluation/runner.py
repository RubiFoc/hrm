"""Scenario execution and aggregation logic for the scoring quality harness."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Protocol

from hrm_backend.scoring.evaluation.dataset import EvaluationMode, ScoringQualityDataset
from hrm_backend.scoring.evaluation.metrics import (
    jaccard_similarity,
    match_precision,
    match_recall,
    mrr,
    ndcg,
    sort_scored_candidate_ids,
)
from hrm_backend.scoring.utils.result import MatchScoreResult


class MatchScoringPredictor(Protocol):
    """Protocol implemented by adapters used for `ollama`-mode evaluation."""

    def score_candidate(self, *, vacancy, document) -> MatchScoreResult:
        """Return one structured scoring prediction for the given vacancy and document."""


@dataclass(frozen=True, slots=True)
class CandidateEvaluationResult:
    """Evaluation result for one candidate inside one scenario.

    Attributes:
        candidate_id: Stable dataset candidate identifier.
        expected_relevance: Expected relevance grade used by ranking metrics.
        predicted_score: Predicted score returned by the selected evaluation mode.
        predicted_confidence: Predicted confidence returned by the selected evaluation mode.
        summary: Predicted recruiter-facing summary.
        match_precision: Precision over predicted vs expected matched requirements.
        match_recall: Recall over predicted vs expected matched requirements.
        predicted_matched_requirements: Predicted matched requirement labels.
        expected_matched_requirements: Expected matched requirement labels.
        predicted_missing_requirements: Predicted missing requirement labels.
        expected_missing_requirements: Expected missing requirement labels.
        model_name: Model name reported by the scoring payload.
        model_version: Model version reported by the scoring payload.
    """

    candidate_id: str
    expected_relevance: int
    predicted_score: float
    predicted_confidence: float
    summary: str
    match_precision: float
    match_recall: float
    predicted_matched_requirements: tuple[str, ...]
    expected_matched_requirements: tuple[str, ...]
    predicted_missing_requirements: tuple[str, ...]
    expected_missing_requirements: tuple[str, ...]
    model_name: str
    model_version: str


@dataclass(frozen=True, slots=True)
class ScenarioEvaluationResult:
    """Aggregated result for one scored scenario.

    Attributes:
        scenario_id: Scenario identifier from the dataset.
        paraphrase_of: Optional base scenario id when this result belongs to a paraphrase case.
        ranking_ndcg: NDCG score for the predicted ranking.
        ranking_mrr: MRR score for the predicted ranking.
        match_precision: Mean candidate-level requirement precision.
        match_recall: Mean candidate-level requirement recall.
        ranked_candidate_ids: Deterministic ranking emitted by the harness.
        candidates: Candidate-level evaluation details sorted by candidate id.
    """

    scenario_id: str
    paraphrase_of: str | None
    ranking_ndcg: float
    ranking_mrr: float
    match_precision: float
    match_recall: float
    ranked_candidate_ids: tuple[str, ...]
    candidates: tuple[CandidateEvaluationResult, ...]


@dataclass(frozen=True, slots=True)
class ParaphraseRobustnessPairResult:
    """Paraphrase robustness comparison between one base and one variant scenario.

    Attributes:
        base_scenario_id: Referenced base scenario identifier.
        paraphrase_scenario_id: Variant scenario identifier.
        base_top_candidate_id: Top-ranked candidate in the base scenario.
        paraphrase_top_candidate_id: Top-ranked candidate in the paraphrase scenario.
        top_1_stable: Whether both scenarios share the same top-ranked candidate.
        full_ranking_stable: Whether both scenarios share the exact full ranking.
        mean_matched_requirement_jaccard:
            Mean candidate-level Jaccard similarity for matched labels.
        mean_missing_requirement_jaccard:
            Mean candidate-level Jaccard similarity for missing labels.
        mean_absolute_score_delta: Mean absolute candidate-level score delta.
    """

    base_scenario_id: str
    paraphrase_scenario_id: str
    base_top_candidate_id: str | None
    paraphrase_top_candidate_id: str | None
    top_1_stable: bool
    full_ranking_stable: bool
    mean_matched_requirement_jaccard: float
    mean_missing_requirement_jaccard: float
    mean_absolute_score_delta: float


@dataclass(frozen=True, slots=True)
class QualityHarnessReport:
    """Complete quality-harness output consumed by deterministic reporting.

    Attributes:
        dataset_id: Dataset identifier from the input file.
        mode: Harness mode used for execution.
        ranking_ndcg: Mean scenario-level NDCG.
        ranking_mrr: Mean scenario-level MRR.
        match_precision: Mean candidate-level requirement precision.
        match_recall: Mean candidate-level requirement recall.
        scenarios: Per-scenario evaluation results sorted by scenario id.
        paraphrase_pairs: Paraphrase robustness comparisons sorted by paraphrase scenario id.
    """

    dataset_id: str
    mode: EvaluationMode
    ranking_ndcg: float
    ranking_mrr: float
    match_precision: float
    match_recall: float
    scenarios: tuple[ScenarioEvaluationResult, ...]
    paraphrase_pairs: tuple[ParaphraseRobustnessPairResult, ...]


def run_quality_harness(
    *,
    dataset: ScoringQualityDataset,
    mode: EvaluationMode,
    adapter: MatchScoringPredictor | None = None,
) -> QualityHarnessReport:
    """Run the scoring quality harness against a validated dataset.

    Args:
        dataset: Validated scoring quality dataset.
        mode: Selected harness mode.
        adapter: Optional scoring adapter required for `ollama` mode.

    Returns:
        QualityHarnessReport: Aggregated harness output.

    Raises:
        ValueError: If `ollama` mode is requested without an adapter.
    """

    if mode == "ollama" and adapter is None:
        raise ValueError("ollama mode requires a scoring adapter")

    scenario_results: list[ScenarioEvaluationResult] = []
    all_candidate_results: list[CandidateEvaluationResult] = []
    for scenario in sorted(dataset.scenarios, key=lambda item: item.scenario_id):
        vacancy = scenario.vacancy.to_vacancy_model(scenario_id=scenario.scenario_id)
        candidate_results: list[CandidateEvaluationResult] = []
        scores_by_candidate: dict[str, float] = {}

        for candidate_case in sorted(scenario.candidates, key=lambda item: item.candidate_id):
            document = candidate_case.document.to_candidate_document_model(
                scenario_id=scenario.scenario_id,
                candidate_id=candidate_case.candidate_id,
            )
            if mode == "fixture":
                assert candidate_case.fixture_prediction is not None
                prediction = candidate_case.fixture_prediction
            else:
                assert adapter is not None
                prediction = adapter.score_candidate(vacancy=vacancy, document=document)

            candidate_result = CandidateEvaluationResult(
                candidate_id=candidate_case.candidate_id,
                expected_relevance=candidate_case.expected_relevance,
                predicted_score=float(prediction.score),
                predicted_confidence=float(prediction.confidence),
                summary=prediction.summary,
                match_precision=match_precision(
                    prediction.matched_requirements,
                    candidate_case.expected_matched_requirements,
                ),
                match_recall=match_recall(
                    prediction.matched_requirements,
                    candidate_case.expected_matched_requirements,
                ),
                predicted_matched_requirements=tuple(prediction.matched_requirements),
                expected_matched_requirements=tuple(candidate_case.expected_matched_requirements),
                predicted_missing_requirements=tuple(prediction.missing_requirements),
                expected_missing_requirements=tuple(candidate_case.expected_missing_requirements),
                model_name=prediction.model_name,
                model_version=prediction.model_version,
            )
            candidate_results.append(candidate_result)
            all_candidate_results.append(candidate_result)
            scores_by_candidate[candidate_case.candidate_id] = float(prediction.score)

        ranked_candidate_ids = tuple(sort_scored_candidate_ids(scores_by_candidate))
        relevance_by_candidate = {
            candidate_case.candidate_id: candidate_case.expected_relevance
            for candidate_case in scenario.candidates
        }
        scenario_results.append(
            ScenarioEvaluationResult(
                scenario_id=scenario.scenario_id,
                paraphrase_of=scenario.paraphrase_of,
                ranking_ndcg=ndcg(relevance_by_candidate, ranked_candidate_ids),
                ranking_mrr=mrr(relevance_by_candidate, ranked_candidate_ids),
                match_precision=mean(
                    candidate_result.match_precision for candidate_result in candidate_results
                ),
                match_recall=mean(
                    candidate_result.match_recall for candidate_result in candidate_results
                ),
                ranked_candidate_ids=ranked_candidate_ids,
                candidates=tuple(candidate_results),
            )
        )

    paraphrase_pairs = tuple(_build_paraphrase_pair_results(scenario_results))
    return QualityHarnessReport(
        dataset_id=dataset.dataset_id,
        mode=mode,
        ranking_ndcg=mean(result.ranking_ndcg for result in scenario_results),
        ranking_mrr=mean(result.ranking_mrr for result in scenario_results),
        match_precision=mean(result.match_precision for result in all_candidate_results),
        match_recall=mean(result.match_recall for result in all_candidate_results),
        scenarios=tuple(scenario_results),
        paraphrase_pairs=paraphrase_pairs,
    )


def _build_paraphrase_pair_results(
    scenario_results: list[ScenarioEvaluationResult],
) -> list[ParaphraseRobustnessPairResult]:
    """Build paraphrase robustness comparisons from completed scenario results."""

    scenario_by_id = {scenario.scenario_id: scenario for scenario in scenario_results}
    paraphrase_results: list[ParaphraseRobustnessPairResult] = []

    for scenario in sorted(scenario_results, key=lambda item: item.scenario_id):
        if scenario.paraphrase_of is None:
            continue
        base_scenario = scenario_by_id[scenario.paraphrase_of]
        base_candidates = {
            candidate.candidate_id: candidate for candidate in base_scenario.candidates
        }
        paraphrase_candidates = {
            candidate.candidate_id: candidate for candidate in scenario.candidates
        }
        candidate_ids = sorted(base_candidates)
        top_1_stable = base_scenario.ranked_candidate_ids[:1] == scenario.ranked_candidate_ids[:1]
        full_ranking_stable = (
            base_scenario.ranked_candidate_ids == scenario.ranked_candidate_ids
        )

        paraphrase_results.append(
            ParaphraseRobustnessPairResult(
                base_scenario_id=base_scenario.scenario_id,
                paraphrase_scenario_id=scenario.scenario_id,
                base_top_candidate_id=(
                    base_scenario.ranked_candidate_ids[0]
                    if base_scenario.ranked_candidate_ids
                    else None
                ),
                paraphrase_top_candidate_id=(
                    scenario.ranked_candidate_ids[0] if scenario.ranked_candidate_ids else None
                ),
                top_1_stable=top_1_stable,
                full_ranking_stable=full_ranking_stable,
                mean_matched_requirement_jaccard=mean(
                    jaccard_similarity(
                        base_candidates[candidate_id].predicted_matched_requirements,
                        paraphrase_candidates[candidate_id].predicted_matched_requirements,
                    )
                    for candidate_id in candidate_ids
                ),
                mean_missing_requirement_jaccard=mean(
                    jaccard_similarity(
                        base_candidates[candidate_id].predicted_missing_requirements,
                        paraphrase_candidates[candidate_id].predicted_missing_requirements,
                    )
                    for candidate_id in candidate_ids
                ),
                mean_absolute_score_delta=mean(
                    abs(
                        base_candidates[candidate_id].predicted_score
                        - paraphrase_candidates[candidate_id].predicted_score
                    )
                    for candidate_id in candidate_ids
                ),
            )
        )
    return paraphrase_results


__all__ = [
    "CandidateEvaluationResult",
    "MatchScoringPredictor",
    "ParaphraseRobustnessPairResult",
    "QualityHarnessReport",
    "ScenarioEvaluationResult",
    "run_quality_harness",
]
