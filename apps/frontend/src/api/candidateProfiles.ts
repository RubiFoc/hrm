import type { components } from "./generated/openapi-types";
import { typedApiClient } from "./typedClient";

export type CandidateListResponse = components["schemas"]["CandidateListResponse"];
export type CandidateListItemResponse = components["schemas"]["CandidateListItemResponse"];
export type CandidateResponse = components["schemas"]["CandidateResponse"];
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

function withAuth(accessToken: string): RequestInit {
  return {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  };
}

/**
 * Load candidate profiles for authenticated HR/admin actors.
 */
export function listCandidateProfiles(
  accessToken: string,
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
    withAuth(accessToken),
  );
}
