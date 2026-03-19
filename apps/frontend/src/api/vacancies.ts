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

/**
 * Load vacancies for authenticated staff users.
 */
export function listVacancies(): Promise<VacancyListResponse> {
  return typedApiClient.get<VacancyListResponse>("/api/v1/vacancies");
}

/**
 * Read one vacancy through the staff API.
 */
export function getVacancy(vacancyId: string): Promise<VacancyResponse> {
  return typedApiClient.get<VacancyResponse>(`/api/v1/vacancies/${vacancyId}`);
}

/**
 * Create one vacancy through the staff API.
 */
export function createVacancy(
  payload: VacancyCreateRequest,
): Promise<VacancyResponse> {
  return typedApiClient.post<VacancyResponse>("/api/v1/vacancies", payload);
}

/**
 * Patch one vacancy through the staff API.
 */
export function updateVacancy(
  vacancyId: string,
  payload: VacancyUpdateRequest,
): Promise<VacancyResponse> {
  return typedApiClient.patch<VacancyResponse>(`/api/v1/vacancies/${vacancyId}`, payload);
}

/**
 * Load ordered pipeline transition history for one vacancy+candidate pair.
 */
export function listPipelineTransitions(
  vacancyId: string,
  candidateId: string,
): Promise<PipelineTransitionListResponse> {
  return typedApiClient.get<PipelineTransitionListResponse>(
    "/api/v1/pipeline/transitions",
    {
      vacancy_id: vacancyId,
      candidate_id: candidateId,
    },
  );
}

/**
 * Append one pipeline transition for one vacancy+candidate pair.
 */
export function createPipelineTransition(
  payload: PipelineTransitionCreateRequest,
): Promise<PipelineTransitionResponse> {
  return typedApiClient.post<PipelineTransitionResponse>("/api/v1/pipeline/transitions", payload);
}
