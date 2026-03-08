import type { components } from "./generated/openapi-types";
import { typedApiClient } from "./typedClient";

export type VacancyCreateRequest = components["schemas"]["VacancyCreateRequest"];
export type VacancyUpdateRequest = components["schemas"]["VacancyUpdateRequest"];
export type VacancyResponse = components["schemas"]["VacancyResponse"];
export type VacancyListResponse = components["schemas"]["VacancyListResponse"];
export type PipelineTransitionCreateRequest =
  components["schemas"]["PipelineTransitionCreateRequest"];
export type PipelineTransitionResponse =
  components["schemas"]["PipelineTransitionResponse"];
export type PipelineTransitionListResponse =
  components["schemas"]["PipelineTransitionListResponse"];

function withAuth(accessToken: string): RequestInit {
  return {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  };
}

/**
 * Load vacancies for authenticated staff users.
 */
export function listVacancies(accessToken: string): Promise<VacancyListResponse> {
  return typedApiClient.get<VacancyListResponse>("/api/v1/vacancies", undefined, withAuth(accessToken));
}

/**
 * Create one vacancy through the staff API.
 */
export function createVacancy(
  accessToken: string,
  payload: VacancyCreateRequest,
): Promise<VacancyResponse> {
  return typedApiClient.post<VacancyResponse>("/api/v1/vacancies", payload, withAuth(accessToken));
}

/**
 * Patch one vacancy through the staff API.
 */
export function updateVacancy(
  accessToken: string,
  vacancyId: string,
  payload: VacancyUpdateRequest,
): Promise<VacancyResponse> {
  return typedApiClient.patch<VacancyResponse>(
    `/api/v1/vacancies/${vacancyId}`,
    payload,
    withAuth(accessToken),
  );
}

/**
 * Load ordered pipeline transition history for one vacancy+candidate pair.
 */
export function listPipelineTransitions(
  accessToken: string,
  vacancyId: string,
  candidateId: string,
): Promise<PipelineTransitionListResponse> {
  return typedApiClient.get<PipelineTransitionListResponse>(
    "/api/v1/pipeline/transitions",
    {
      vacancy_id: vacancyId,
      candidate_id: candidateId,
    },
    withAuth(accessToken),
  );
}

/**
 * Append one pipeline transition for one vacancy+candidate pair.
 */
export function createPipelineTransition(
  accessToken: string,
  payload: PipelineTransitionCreateRequest,
): Promise<PipelineTransitionResponse> {
  return typedApiClient.post<PipelineTransitionResponse>(
    "/api/v1/pipeline/transitions",
    payload,
    withAuth(accessToken),
  );
}
