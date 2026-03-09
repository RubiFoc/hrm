import type { components } from "./generated/openapi-types";
import { typedApiClient } from "./typedClient";

export type MatchScoreCreateRequest = components["schemas"]["MatchScoreCreateRequest"];
export type MatchScoreEvidenceResponse =
  components["schemas"]["MatchScoreEvidenceResponse"];
export type MatchScoreResponse = components["schemas"]["MatchScoreResponse"];
export type MatchScoreListResponse = components["schemas"]["MatchScoreListResponse"];

function withAuth(accessToken: string): RequestInit {
  return {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  };
}

/**
 * Enqueue scoring or return the latest active score job for one vacancy-candidate pair.
 */
export function createMatchScore(
  accessToken: string,
  vacancyId: string,
  payload: MatchScoreCreateRequest,
): Promise<MatchScoreResponse> {
  return typedApiClient.post<MatchScoreResponse>(
    `/api/v1/vacancies/${vacancyId}/match-scores`,
    payload,
    withAuth(accessToken),
  );
}

/**
 * Load latest score/status entries for one vacancy, optionally narrowed to one candidate.
 */
export function listMatchScores(
  accessToken: string,
  vacancyId: string,
  candidateId?: string,
): Promise<MatchScoreListResponse> {
  return typedApiClient.get<MatchScoreListResponse>(
    `/api/v1/vacancies/${vacancyId}/match-scores`,
    { candidate_id: candidateId },
    withAuth(accessToken),
  );
}

/**
 * Load latest score/status payload for one vacancy-candidate pair.
 */
export function getMatchScore(
  accessToken: string,
  vacancyId: string,
  candidateId: string,
): Promise<MatchScoreResponse> {
  return typedApiClient.get<MatchScoreResponse>(
    `/api/v1/vacancies/${vacancyId}/match-scores/${candidateId}`,
    undefined,
    withAuth(accessToken),
  );
}
