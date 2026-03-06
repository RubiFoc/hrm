import { typedApiClient } from "./typedClient";
import type { components } from "./generated/openapi-types";

export type CandidateCvParsingStatusResponse = components["schemas"]["CVParsingStatusResponse"];
export type CandidateCvAnalysisResponse = components["schemas"]["CVAnalysisResponse"];

export function getCandidateCvParsingStatus(
  candidateId: string,
): Promise<CandidateCvParsingStatusResponse> {
  return typedApiClient.get<CandidateCvParsingStatusResponse>(
    `/api/v1/candidates/${candidateId}/cv/parsing-status`,
  );
}

export function getCandidateCvAnalysis(candidateId: string): Promise<CandidateCvAnalysisResponse> {
  return typedApiClient.get<CandidateCvAnalysisResponse>(`/api/v1/candidates/${candidateId}/cv/analysis`);
}
