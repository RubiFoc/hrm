/**
 * Shared helpers for the split HR workspace routes.
 *
 * The legacy monolith still exists for regression coverage and the full workbench,
 * while these helpers keep the focused subpages consistent without duplicating
 * validation, formatting, and localized API error handling.
 */

import { ApiError, type CandidateListItemResponse, type HRInterviewResponse, type InterviewFeedbackItemResponse, type InterviewFeedbackPanelSummaryResponse, type InterviewFeedbackRecommendation, type InterviewFeedbackUpsertRequest, type InterviewStatus, type MatchScoreResponse, type MeResponse, type OfferResponse, type OfferStatus, type OfferUpsertRequest, type PipelineTransitionCreateRequest, type VacancyCreateRequest, type VacancyResponse, type VacancyUpdateRequest } from "../../api";

export const PIPELINE_STAGE_OPTIONS: PipelineTransitionCreateRequest["to_stage"][] = [
  "applied",
  "screening",
  "shortlist",
  "interview",
  "offer",
  "hired",
  "rejected",
];
export const MATCH_SCORE_POLL_INTERVAL_MS = 1000;
export const DEFAULT_CANDIDATE_LIMIT = 20;
export const INTERVIEW_POLL_INTERVAL_MS = 1000;
export const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
export const FEEDBACK_SCORE_OPTIONS = [1, 2, 3, 4, 5] as const;
export const FEEDBACK_RECOMMENDATION_OPTIONS: InterviewFeedbackRecommendation[] = [
  "strong_yes",
  "yes",
  "mixed",
  "no",
];
export const OFFER_MUTABLE_STATUS: OfferStatus = "draft";

export type FeedbackState = {
  type: "success" | "error";
  message: string;
};
export type VacancyDraft = VacancyCreateRequest;
export type CandidateStageFilterValue = PipelineTransitionCreateRequest["to_stage"] | "all";
export type MatchScoreStatus = MatchScoreResponse["status"];
export type InterviewDraft = {
  scheduledStartLocal: string;
  scheduledEndLocal: string;
  timezone: string;
  locationKind: "google_meet" | "onsite" | "phone";
  locationDetails: string;
  interviewerStaffIdsInput: string;
  cancelReasonCode: string;
};
export type InterviewerFeedbackDraft = {
  requirementsMatchScore: number;
  communicationScore: number;
  problemSolvingScore: number;
  collaborationScore: number;
  recommendation: InterviewFeedbackRecommendation;
  strengthsNote: string;
  concernsNote: string;
  evidenceNote: string;
};
export type OfferDraft = {
  termsSummary: string;
  proposedStartDate: string;
  expiresAt: string;
  note: string;
  decisionNote: string;
};

export const DEFAULT_VACANCY_DRAFT: VacancyDraft = {
  title: "",
  description: "",
  department: "",
  status: "open",
};

export function normalizeInput(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}

export function normalizeCandidateFilterValue(value: string): string | undefined {
  const normalized = value.trim();
  return normalized ? normalized : undefined;
}

export function toVacancyDraft(vacancy: VacancyResponse): VacancyDraft {
  return {
    title: vacancy.title,
    description: vacancy.description,
    department: vacancy.department,
    status: vacancy.status,
  };
}

export function buildVacancyPatchPayload(
  current: VacancyResponse,
  draft: VacancyDraft,
): VacancyUpdateRequest {
  const payload: VacancyUpdateRequest = {};
  if (draft.title !== current.title) {
    payload.title = draft.title;
  }
  if (draft.description !== current.description) {
    payload.description = draft.description;
  }
  if (draft.department !== current.department) {
    payload.department = draft.department;
  }
  if (draft.status !== current.status) {
    payload.status = draft.status;
  }
  return payload;
}

export function mergeCandidateSelectItems(
  items: CandidateListItemResponse[],
  selectedCandidate: CandidateListItemResponse | null,
): CandidateListItemResponse[] {
  if (!selectedCandidate) {
    return items;
  }
  if (items.some((item) => item.candidate_id === selectedCandidate.candidate_id)) {
    return items;
  }
  return [selectedCandidate, ...items];
}

export function formatCandidateLabel(candidate: CandidateListItemResponse): string {
  return `${candidate.first_name} ${candidate.last_name} (${candidate.email})`;
}

export function formatDateTime(value: string): string {
  return new Date(value).toLocaleString();
}

export function formatScore(
  value: number | null | undefined,
  t: (key: string) => string,
): string {
  if (value === null || value === undefined) {
    return t("hrDashboard.shortlist.notAvailable");
  }
  return value.toFixed(0);
}

export function formatConfidence(
  value: number | null | undefined,
  t: (key: string) => string,
): string {
  if (value === null || value === undefined) {
    return t("hrDashboard.shortlist.notAvailable");
  }
  return `${Math.round(value * 100)}%`;
}

export function formatAverageScore(
  value: number | null | undefined,
  t: (key: string) => string,
): string {
  if (value === null || value === undefined) {
    return t("hrDashboard.shortlist.notAvailable");
  }
  return value.toFixed(2);
}

export function buildMatchScoreManualReviewMessage(
  matchScore: MatchScoreResponse,
  t: (key: string, options?: Record<string, unknown>) => string,
): string {
  if (matchScore.manual_review_reason === "low_confidence") {
    if (
      matchScore.confidence_threshold !== null
      && matchScore.confidence_threshold !== undefined
    ) {
      return t("hrDashboard.shortlist.manualReview.lowConfidenceWithThreshold", {
        confidence: formatConfidence(matchScore.confidence, t),
        threshold: formatConfidence(matchScore.confidence_threshold, t),
      });
    }
    return t("hrDashboard.shortlist.manualReview.lowConfidence", {
      confidence: formatConfidence(matchScore.confidence, t),
    });
  }

  return t("hrDashboard.shortlist.manualReview.generic");
}

export function resolveMatchScoreChipColor(
  status: MatchScoreStatus,
): "default" | "error" | "info" | "success" | "warning" {
  switch (status) {
    case "queued":
      return "info";
    case "running":
      return "warning";
    case "succeeded":
      return "success";
    case "failed":
      return "error";
    default:
      return "default";
  }
}

export function renderStringList(items: string[], emptyState: string) {
  if (items.length === 0) {
    return emptyState;
  }

  return items.join(", ");
}

export function createEmptyInterviewDraft(): InterviewDraft {
  return {
    scheduledStartLocal: "",
    scheduledEndLocal: "",
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
    locationKind: "google_meet",
    locationDetails: "",
    interviewerStaffIdsInput: "",
    cancelReasonCode: "cancelled_by_staff",
  };
}

export function createEmptyOfferDraft(): OfferDraft {
  return {
    termsSummary: "",
    proposedStartDate: "",
    expiresAt: "",
    note: "",
    decisionNote: "",
  };
}

export function createEmptyInterviewerFeedbackDraft(): InterviewerFeedbackDraft {
  return {
    requirementsMatchScore: 3,
    communicationScore: 3,
    problemSolvingScore: 3,
    collaborationScore: 3,
    recommendation: "mixed",
    strengthsNote: "",
    concernsNote: "",
    evidenceNote: "",
  };
}

export function buildInterviewDraftFromResponse(interview: HRInterviewResponse): InterviewDraft {
  return {
    scheduledStartLocal: toDateTimeLocalValue(interview.scheduled_start_at),
    scheduledEndLocal: toDateTimeLocalValue(interview.scheduled_end_at),
    timezone: interview.timezone,
    locationKind: interview.location_kind,
    locationDetails: interview.location_details ?? "",
    interviewerStaffIdsInput: interview.interviewer_staff_ids.join(", "),
    cancelReasonCode: interview.cancel_reason_code ?? "cancelled_by_staff",
  };
}

export function buildFeedbackDraftFromItem(
  item: InterviewFeedbackItemResponse | null,
): InterviewerFeedbackDraft {
  if (!item) {
    return createEmptyInterviewerFeedbackDraft();
  }
  return {
    requirementsMatchScore: item.requirements_match_score,
    communicationScore: item.communication_score,
    problemSolvingScore: item.problem_solving_score,
    collaborationScore: item.collaboration_score,
    recommendation: item.recommendation,
    strengthsNote: item.strengths_note,
    concernsNote: item.concerns_note,
    evidenceNote: item.evidence_note,
  };
}

export function buildOfferDraftFromResponse(item: OfferResponse | null): OfferDraft {
  if (!item) {
    return createEmptyOfferDraft();
  }
  return {
    termsSummary: item.terms_summary ?? "",
    proposedStartDate: item.proposed_start_date ?? "",
    expiresAt: item.expires_at ?? "",
    note: item.note ?? "",
    decisionNote: item.decision_note ?? "",
  };
}

export function buildInterviewFeedbackPayload(
  draft: InterviewerFeedbackDraft,
  t: (key: string) => string,
): InterviewFeedbackUpsertRequest {
  const strengthsNote = draft.strengthsNote.trim();
  const concernsNote = draft.concernsNote.trim();
  const evidenceNote = draft.evidenceNote.trim();
  if (!strengthsNote || !concernsNote || !evidenceNote) {
    throw new Error(t("hrDashboard.interviews.feedback.errors.notesRequired"));
  }
  return {
    requirements_match_score: draft.requirementsMatchScore,
    communication_score: draft.communicationScore,
    problem_solving_score: draft.problemSolvingScore,
    collaboration_score: draft.collaborationScore,
    recommendation: draft.recommendation,
    strengths_note: strengthsNote,
    concerns_note: concernsNote,
    evidence_note: evidenceNote,
  };
}

export function buildOfferUpsertPayload(
  draft: OfferDraft,
  t: (key: string) => string,
): OfferUpsertRequest {
  const termsSummary = normalizeInput(draft.termsSummary);
  if (!termsSummary) {
    throw new Error(t("hrDashboard.offers.errors.termsRequired"));
  }
  return {
    terms_summary: termsSummary,
    proposed_start_date: normalizeInput(draft.proposedStartDate),
    expires_at: normalizeInput(draft.expiresAt),
    note: normalizeInput(draft.note),
  };
}

export function buildInterviewCreatePayload(
  draft: InterviewDraft,
  candidateId: string,
  t: (key: string) => string,
) {
  const basePayload = buildInterviewSchedulePayload(draft, t);
  return {
    ...basePayload,
    candidate_id: candidateId,
  };
}

export function buildInterviewReschedulePayload(
  draft: InterviewDraft,
  t: (key: string) => string,
) {
  return buildInterviewSchedulePayload(draft, t);
}

export function buildInterviewSchedulePayload(
  draft: InterviewDraft,
  t: (key: string) => string,
) {
  const interviewerStaffIds = parseInterviewerStaffIds(draft.interviewerStaffIdsInput);
  if (!draft.scheduledStartLocal || !draft.scheduledEndLocal) {
    throw new Error(t("hrDashboard.interviews.errors.missingScheduleWindow"));
  }
  if (interviewerStaffIds.length === 0) {
    throw new Error(t("hrDashboard.interviews.errors.invalidInterviewerIds"));
  }
  return {
    scheduled_start_local: draft.scheduledStartLocal,
    scheduled_end_local: draft.scheduledEndLocal,
    timezone: draft.timezone.trim(),
    location_kind: draft.locationKind,
    location_details: normalizeInput(draft.locationDetails),
    interviewer_staff_ids: interviewerStaffIds,
  };
}

export function parseInterviewerStaffIds(value: string): string[] {
  const items = value
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
  if (items.some((item) => !UUID_PATTERN.test(item))) {
    return [];
  }
  return Array.from(new Set(items));
}

export function toDateTimeLocalValue(value: string): string {
  const item = new Date(value);
  if (Number.isNaN(item.getTime())) {
    return "";
  }
  const year = item.getFullYear();
  const month = String(item.getMonth() + 1).padStart(2, "0");
  const day = String(item.getDate()).padStart(2, "0");
  const hours = String(item.getHours()).padStart(2, "0");
  const minutes = String(item.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

export function formatInterviewDateTime(value: string, timezone: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: timezone,
    }).format(new Date(value));
  } catch {
    return new Date(value).toLocaleString();
  }
}

export function selectInterviewState(items: HRInterviewResponse[]): {
  active: HRInterviewResponse | null;
  latest: HRInterviewResponse | null;
} {
  const active = items.find((item) => item.status !== "cancelled") ?? null;
  return {
    active,
    latest: active ?? items[0] ?? null,
  };
}

export function findFeedbackItemForInterviewer(
  summary: InterviewFeedbackPanelSummaryResponse | null,
  interviewerId: string | null,
): InterviewFeedbackItemResponse | null {
  if (!summary || !interviewerId) {
    return null;
  }
  return summary.items.find((item) => item.interviewer_staff_id === interviewerId) ?? null;
}

export function isCurrentUserAssignedInterviewer(
  interview: HRInterviewResponse | null,
  currentUser: MeResponse | null,
): boolean {
  if (!interview || !currentUser) {
    return false;
  }
  return interview.interviewer_staff_ids.includes(currentUser.subject_id);
}

export function hasInterviewFeedbackWindowOpened(interview: HRInterviewResponse | null): boolean {
  if (!interview) {
    return false;
  }
  return new Date(interview.scheduled_end_at).getTime() <= Date.now();
}

export function resolveFeedbackEditorBlockedReason({
  latestInterview,
  currentPipelineStage,
  currentUserCanWriteFeedback,
  feedbackWindowOpen,
  t,
}: {
  latestInterview: HRInterviewResponse | null;
  currentPipelineStage: PipelineTransitionCreateRequest["to_stage"] | null;
  currentUserCanWriteFeedback: boolean;
  feedbackWindowOpen: boolean;
  t: (key: string) => string;
}): string | null {
  if (!latestInterview || !currentUserCanWriteFeedback) {
    return null;
  }
  if (latestInterview.status === "cancelled") {
    return t("hrDashboard.interviews.feedback.locked");
  }
  if (!feedbackWindowOpen) {
    return t("hrDashboard.interviews.feedback.windowNotOpen");
  }
  if (currentPipelineStage && currentPipelineStage !== "interview") {
    return t("hrDashboard.interviews.feedback.locked");
  }
  return null;
}

export function buildOfferGateAlertMessage(
  summary: InterviewFeedbackPanelSummaryResponse,
  t: (key: string, options?: Record<string, unknown>) => string,
): string {
  if (summary.gate_status === "passed") {
    return t("hrDashboard.interviews.feedback.offerReady");
  }
  return t("hrDashboard.interviews.feedback.offerBlocked", {
    reasons: resolveFeedbackGateReasonLabels(summary.gate_reason_codes, t).join(", "),
  });
}

export function buildFeedbackGateMessage(
  summary: InterviewFeedbackPanelSummaryResponse,
  t: (key: string, options?: Record<string, unknown>) => string,
): string {
  if (summary.gate_status === "passed") {
    return t("hrDashboard.interviews.feedback.gatePassed");
  }
  return t("hrDashboard.interviews.feedback.gateBlocked", {
    reasons: resolveFeedbackGateReasonLabels(summary.gate_reason_codes, t).join(", "),
  });
}

export function resolveFeedbackGateReasonLabels(
  reasonCodes: string[],
  t: (key: string) => string,
): string[] {
  return reasonCodes.map((reasonCode) => {
    const translated = t(`hrDashboard.interviews.feedback.gateReasons.${reasonCode}`);
    if (translated !== `hrDashboard.interviews.feedback.gateReasons.${reasonCode}`) {
      return translated;
    }
    return reasonCode;
  });
}

export function buildOfferPrerequisiteMessage({
  currentPipelineStage,
  feedbackSummary,
  offerQueryError,
  t,
}: {
  currentPipelineStage: PipelineTransitionCreateRequest["to_stage"] | null;
  feedbackSummary: InterviewFeedbackPanelSummaryResponse | null;
  offerQueryError: unknown;
  t: (key: string, options?: Record<string, unknown>) => string;
}): string | null {
  if (currentPipelineStage === "interview" && feedbackSummary) {
    if (feedbackSummary.gate_status === "passed") {
      return t("hrDashboard.offers.waitingForTransition");
    }
    return t("hrDashboard.offers.blockedByFairnessGate", {
      reasons: resolveFeedbackGateReasonLabels(feedbackSummary.gate_reason_codes, t).join(", "),
    });
  }
  if (
    currentPipelineStage !== "offer"
    && currentPipelineStage !== "hired"
    && currentPipelineStage !== "rejected"
  ) {
    return t("hrDashboard.offers.inactive");
  }
  if (isOfferStageNotActiveError(offerQueryError)) {
    return t("hrDashboard.offers.stageNotReady");
  }
  return null;
}

export function buildOfferStatusHint(
  status: OfferStatus,
  t: (key: string) => string,
): string {
  switch (status) {
    case "draft":
      return t("hrDashboard.offers.hints.draft");
    case "sent":
      return t("hrDashboard.offers.hints.sent");
    case "accepted":
      return t("hrDashboard.offers.hints.accepted");
    case "declined":
      return t("hrDashboard.offers.hints.declined");
    default:
      return t("hrDashboard.offers.hints.draft");
  }
}

export function isOfferStageNotActiveError(error: unknown): boolean {
  return error instanceof ApiError && error.detail.toLowerCase().includes("offer_stage_not_active");
}

export function resolveRecruitmentApiError(
  error: unknown,
  t: (key: string) => string,
): string {
  if (error instanceof Error && !(error instanceof ApiError)) {
    return error.message;
  }
  if (error instanceof ApiError) {
    const detail = error.detail.toLowerCase();
    if (detail.includes("vacancy not found")) {
      return t("hrDashboard.errors.vacancyNotFound");
    }
    if (detail.includes("candidate not found")) {
      return t("hrDashboard.errors.candidateNotFound");
    }
    if (detail.includes("cv analysis is not ready")) {
      return t("hrDashboard.errors.cvAnalysisNotReady");
    }
    if (detail.includes("stage_requires_vacancy_id")) {
      return t("hrDashboard.errors.stageRequiresVacancy");
    }
    if (detail.includes("in_pipeline_only_requires_vacancy_id")) {
      return t("hrDashboard.errors.inPipelineOnlyRequiresVacancy");
    }
    if (detail.includes("match score not found")) {
      return t("hrDashboard.errors.matchScoreNotFound");
    }
    if (detail.includes("interview_feedback_window_not_open")) {
      return t("hrDashboard.errors.interviewFeedbackWindowNotOpen");
    }
    if (detail.includes("interview_feedback_missing")) {
      return t("hrDashboard.errors.interviewFeedbackMissing");
    }
    if (detail.includes("interview_feedback_incomplete")) {
      return t("hrDashboard.errors.interviewFeedbackIncomplete");
    }
    if (detail.includes("interview_feedback_stale")) {
      return t("hrDashboard.errors.interviewFeedbackStale");
    }
    if (detail.includes("offer_stage_not_active")) {
      return t("hrDashboard.errors.offerStageNotActive");
    }
    if (detail.includes("offer_not_found")) {
      return t("hrDashboard.errors.offerNotFound");
    }
    if (detail.includes("offer_not_editable")) {
      return t("hrDashboard.errors.offerNotEditable");
    }
    if (detail.includes("offer_already_sent")) {
      return t("hrDashboard.errors.offerAlreadySent");
    }
    if (detail.includes("offer_already_accepted")) {
      return t("hrDashboard.errors.offerAlreadyAccepted");
    }
    if (detail.includes("offer_already_declined")) {
      return t("hrDashboard.errors.offerAlreadyDeclined");
    }
    if (detail.includes("offer_not_sent")) {
      return t("hrDashboard.errors.offerNotSent");
    }
    if (detail.includes("offer_terms_missing")) {
      return t("hrDashboard.errors.offerTermsMissing");
    }
    if (detail.includes("offer_not_accepted")) {
      return t("hrDashboard.errors.offerNotAccepted");
    }
    if (detail.includes("offer_not_declined")) {
      return t("hrDashboard.errors.offerNotDeclined");
    }
    if (detail.includes("transition from")) {
      return t("hrDashboard.errors.invalidTransition");
    }
    const statusMessage = t(`hrDashboard.errors.http_${error.status}`);
    if (statusMessage !== `hrDashboard.errors.http_${error.status}`) {
      return statusMessage;
    }
  }
  return t("hrDashboard.errors.generic");
}

export function resolveInterviewApiError(
  error: unknown,
  t: (key: string) => string,
): string {
  if (error instanceof Error && !(error instanceof ApiError)) {
    return error.message;
  }
  if (error instanceof ApiError) {
    const detail = error.detail.toLowerCase();
    if (detail.includes("calendar_not_configured")) {
      return t("hrDashboard.interviews.errors.calendarNotConfigured");
    }
    if (detail.includes("interviewer_calendar_not_configured")) {
      return t("hrDashboard.interviews.errors.interviewerCalendarNotConfigured");
    }
    if (detail.includes("active_interview_already_exists")) {
      return t("hrDashboard.interviews.errors.activeInterviewAlreadyExists");
    }
    if (detail.includes("invalid_pipeline_stage")) {
      return t("hrDashboard.interviews.errors.invalidPipelineStage");
    }
    if (detail.includes("duplicate_interviewer_list")) {
      return t("hrDashboard.interviews.errors.duplicateInterviewers");
    }
    if (detail.includes("interview_terminal")) {
      return t("hrDashboard.interviews.errors.interviewTerminal");
    }
    if (detail.includes("invite_not_available")) {
      return t("hrDashboard.interviews.errors.inviteNotAvailable");
    }
    if (detail.includes("interview_feedback_forbidden")) {
      return t("hrDashboard.interviews.feedback.notAssigned");
    }
    if (detail.includes("interview_feedback_locked")) {
      return t("hrDashboard.interviews.feedback.locked");
    }
    if (detail.includes("interview_feedback_window_not_open")) {
      return t("hrDashboard.interviews.feedback.windowNotOpen");
    }
    const statusMessage = t(`hrDashboard.interviews.errors.http_${error.status}`);
    if (statusMessage !== `hrDashboard.interviews.errors.http_${error.status}`) {
      return statusMessage;
    }
  }
  return t("hrDashboard.interviews.errors.generic");
}

export function resolveInterviewStatusChipColor(
  status: InterviewStatus,
): "default" | "error" | "info" | "success" | "warning" {
  switch (status) {
    case "pending_sync":
      return "info";
    case "awaiting_candidate_confirmation":
      return "warning";
    case "confirmed":
      return "success";
    case "reschedule_requested":
      return "warning";
    case "cancelled":
      return "error";
    default:
      return "default";
  }
}

export function resolveInterviewSyncChipColor(
  status: HRInterviewResponse["calendar_sync_status"],
): "default" | "error" | "info" | "success" | "warning" {
  switch (status) {
    case "queued":
      return "info";
    case "running":
      return "warning";
    case "synced":
      return "success";
    case "conflict":
      return "warning";
    case "failed":
      return "error";
    default:
      return "default";
  }
}

export function resolveOfferStatusChipColor(
  status: OfferStatus,
): "default" | "error" | "info" | "success" | "warning" {
  switch (status) {
    case "draft":
      return "info";
    case "sent":
      return "warning";
    case "accepted":
      return "success";
    case "declined":
      return "error";
    default:
      return "default";
  }
}

export function resolveOfferHintSeverity(
  status: OfferStatus,
): "error" | "info" | "success" | "warning" {
  switch (status) {
    case "accepted":
      return "success";
    case "declined":
      return "warning";
    case "sent":
      return "info";
    default:
      return "info";
  }
}
