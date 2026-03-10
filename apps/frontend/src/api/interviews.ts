import type { components } from "./generated/openapi-types";
import { typedApiClient } from "./typedClient";

export type InterviewCreateRequest = components["schemas"]["InterviewCreateRequest"];
export type InterviewRescheduleRequest =
  components["schemas"]["InterviewRescheduleRequest"];
export type InterviewCancelRequest = components["schemas"]["InterviewCancelRequest"];
export type PublicInterviewActionRequest =
  components["schemas"]["PublicInterviewActionRequest"];
export type HRInterviewResponse = components["schemas"]["HRInterviewResponse"];
export type HRInterviewListResponse = components["schemas"]["HRInterviewListResponse"];
export type InterviewStatus = components["schemas"]["HRInterviewResponse"]["status"];
export type CalendarSyncStatus =
  components["schemas"]["HRInterviewResponse"]["calendar_sync_status"];
export type PublicInterviewRegistrationResponse =
  components["schemas"]["PublicInterviewRegistrationResponse"];
export type InterviewFeedbackRecommendation =
  components["schemas"]["InterviewFeedbackItemResponse"]["recommendation"];
export type InterviewFeedbackGateStatus =
  components["schemas"]["InterviewFeedbackPanelSummaryResponse"]["gate_status"];
export type InterviewFeedbackUpsertRequest =
  components["schemas"]["InterviewFeedbackUpsertRequest"];
export type InterviewFeedbackItemResponse =
  components["schemas"]["InterviewFeedbackItemResponse"];
export type InterviewFeedbackRecommendationDistributionResponse =
  components["schemas"]["InterviewFeedbackRecommendationDistributionResponse"];
export type InterviewFeedbackAverageScoresResponse =
  components["schemas"]["InterviewFeedbackAverageScoresResponse"];
export type InterviewFeedbackPanelSummaryResponse =
  components["schemas"]["InterviewFeedbackPanelSummaryResponse"];

function withAuth(accessToken: string): RequestInit {
  return {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  };
}

/**
 * Create one interview proposal for the selected vacancy and candidate.
 */
export function createInterview(
  accessToken: string,
  vacancyId: string,
  payload: InterviewCreateRequest,
): Promise<HRInterviewResponse> {
  return typedApiClient.post<HRInterviewResponse>(
    `/api/v1/vacancies/${vacancyId}/interviews`,
    payload,
    withAuth(accessToken),
  );
}

/**
 * List interview rows for one vacancy with optional filters.
 */
export function listInterviews(
  accessToken: string,
  vacancyId: string,
  params?: {
    candidateId?: string;
    status?: InterviewStatus;
  },
): Promise<HRInterviewListResponse> {
  return typedApiClient.get<HRInterviewListResponse>(
    `/api/v1/vacancies/${vacancyId}/interviews`,
    {
      candidate_id: params?.candidateId,
      status: params?.status,
    },
    withAuth(accessToken),
  );
}

/**
 * Read one interview row for the selected vacancy.
 */
export function getInterview(
  accessToken: string,
  vacancyId: string,
  interviewId: string,
): Promise<HRInterviewResponse> {
  return typedApiClient.get<HRInterviewResponse>(
    `/api/v1/vacancies/${vacancyId}/interviews/${interviewId}`,
    undefined,
    withAuth(accessToken),
  );
}

/**
 * Read current-version feedback summary for one interview.
 */
export function getInterviewFeedbackSummary(
  accessToken: string,
  vacancyId: string,
  interviewId: string,
): Promise<InterviewFeedbackPanelSummaryResponse> {
  return typedApiClient.get<InterviewFeedbackPanelSummaryResponse>(
    `/api/v1/vacancies/${vacancyId}/interviews/${interviewId}/feedback`,
    undefined,
    withAuth(accessToken),
  );
}

/**
 * Create or replace the current interviewer's feedback for one interview.
 */
export function putMyInterviewFeedback(
  accessToken: string,
  vacancyId: string,
  interviewId: string,
  payload: InterviewFeedbackUpsertRequest,
): Promise<InterviewFeedbackItemResponse> {
  return typedApiClient.put<InterviewFeedbackItemResponse>(
    `/api/v1/vacancies/${vacancyId}/interviews/${interviewId}/feedback/me`,
    payload,
    withAuth(accessToken),
  );
}

/**
 * Replace the current schedule window and re-enqueue sync.
 */
export function rescheduleInterview(
  accessToken: string,
  vacancyId: string,
  interviewId: string,
  payload: InterviewRescheduleRequest,
): Promise<HRInterviewResponse> {
  return typedApiClient.post<HRInterviewResponse>(
    `/api/v1/vacancies/${vacancyId}/interviews/${interviewId}/reschedule`,
    payload,
    withAuth(accessToken),
  );
}

/**
 * Cancel one interview from HR workspace.
 */
export function cancelInterview(
  accessToken: string,
  vacancyId: string,
  interviewId: string,
  payload: InterviewCancelRequest,
): Promise<HRInterviewResponse> {
  return typedApiClient.post<HRInterviewResponse>(
    `/api/v1/vacancies/${vacancyId}/interviews/${interviewId}/cancel`,
    payload,
    withAuth(accessToken),
  );
}

/**
 * Reissue a fresh candidate invite token for the current schedule version.
 */
export function resendInterviewInvite(
  accessToken: string,
  vacancyId: string,
  interviewId: string,
): Promise<HRInterviewResponse> {
  return typedApiClient.post<HRInterviewResponse>(
    `/api/v1/vacancies/${vacancyId}/interviews/${interviewId}/resend-invite`,
    undefined,
    withAuth(accessToken),
  );
}

/**
 * Read public interview registration payload by opaque token.
 */
export function getPublicInterviewRegistration(
  token: string,
): Promise<PublicInterviewRegistrationResponse> {
  return typedApiClient.get<PublicInterviewRegistrationResponse>(
    `/api/v1/public/interview-registrations/${encodeURIComponent(token)}`,
  );
}

/**
 * Confirm attendance for the current interview token.
 */
export function confirmPublicInterviewRegistration(
  token: string,
): Promise<PublicInterviewRegistrationResponse> {
  return typedApiClient.post<PublicInterviewRegistrationResponse>(
    `/api/v1/public/interview-registrations/${encodeURIComponent(token)}/confirm`,
    undefined,
  );
}

/**
 * Request a new slot for the current interview token.
 */
export function requestPublicInterviewReschedule(
  token: string,
  payload: PublicInterviewActionRequest,
): Promise<PublicInterviewRegistrationResponse> {
  return typedApiClient.post<PublicInterviewRegistrationResponse>(
    `/api/v1/public/interview-registrations/${encodeURIComponent(token)}/request-reschedule`,
    payload,
  );
}

/**
 * Decline the current interview token.
 */
export function cancelPublicInterviewRegistration(
  token: string,
  payload: PublicInterviewActionRequest,
): Promise<PublicInterviewRegistrationResponse> {
  return typedApiClient.post<PublicInterviewRegistrationResponse>(
    `/api/v1/public/interview-registrations/${encodeURIComponent(token)}/cancel`,
    payload,
  );
}
