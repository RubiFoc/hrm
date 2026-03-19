import type { components } from "./generated/openapi-types";
import { typedApiClient } from "./typedClient";

export type CandidateListResponse = components["schemas"]["CandidateListResponse"];
export type CandidateListItemResponse = components["schemas"]["CandidateListItemResponse"];
export type CandidateResponse = components["schemas"]["CandidateResponse"];
export type CandidateCreateRequest = components["schemas"]["CandidateCreateRequest"];
export type CandidateUpdateRequest = components["schemas"]["CandidateUpdateRequest"];
export type CandidateListQuery = {
  limit?: number;
  offset?: number;
  search?: string;
  location?: string;
  currentTitle?: string;
  skill?: string;
  analysisReady?: boolean;
  minYearsExperience?: number;
  vacancyId?: string;
  inPipelineOnly?: boolean;
  stage?: CandidateListItemResponse["vacancy_stage"];
};

/**
 * Load candidate profiles for authenticated HR/admin actors.
 */
export function listCandidateProfiles(
  query: CandidateListQuery = {},
): Promise<CandidateListResponse> {
  return typedApiClient.get<CandidateListResponse>(
    "/api/v1/candidates",
    {
      limit: query.limit,
      offset: query.offset,
      search: query.search,
      location: query.location,
      current_title: query.currentTitle,
      skill: query.skill,
      analysis_ready: query.analysisReady,
      min_years_experience: query.minYearsExperience,
      vacancy_id: query.vacancyId,
      in_pipeline_only: query.inPipelineOnly,
      stage: query.stage,
    },
  );
}

/**
 * Read one candidate profile for admin or recruiter workflows.
 */
export function getCandidateProfile(
  candidateId: string,
): Promise<CandidateResponse> {
  return typedApiClient.get<CandidateResponse>(
    `/api/v1/candidates/${candidateId}`,
    undefined,
  );
}

/**
 * Create one candidate profile for admin management workflows.
 */
export function createCandidateProfile(
  payload: CandidateCreateRequest,
): Promise<CandidateResponse> {
  return typedApiClient.post<CandidateResponse>("/api/v1/candidates", payload);
}

/**
 * Patch one candidate profile for admin management workflows.
 */
export function updateCandidateProfile(
  candidateId: string,
  payload: CandidateUpdateRequest,
): Promise<CandidateResponse> {
  return typedApiClient.patch<CandidateResponse>(
    `/api/v1/candidates/${candidateId}`,
    payload,
  );
}
