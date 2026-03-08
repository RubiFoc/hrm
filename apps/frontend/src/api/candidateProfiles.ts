import type { components } from "./generated/openapi-types";
import { typedApiClient } from "./typedClient";

export type CandidateListResponse = components["schemas"]["CandidateListResponse"];
export type CandidateResponse = components["schemas"]["CandidateResponse"];

/**
 * Load candidate profiles for authenticated HR/admin actors.
 */
export function listCandidateProfiles(accessToken: string): Promise<CandidateListResponse> {
  return typedApiClient.get<CandidateListResponse>("/api/v1/candidates", undefined, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}
