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

/**
 * Read public parsing status for one anonymous application tracking job.
 */
export function getPublicCandidateCvParsingStatus(
  jobId: string,
): Promise<CandidateCvParsingStatusResponse> {
  return typedApiClient.get<CandidateCvParsingStatusResponse>(`/api/v1/public/cv-parsing-jobs/${jobId}`);
}

/**
 * Read public CV analysis for one anonymous application tracking job.
 */
export function getPublicCandidateCvAnalysis(
  jobId: string,
): Promise<CandidateCvAnalysisResponse> {
  return typedApiClient.get<CandidateCvAnalysisResponse>(`/api/v1/public/cv-parsing-jobs/${jobId}/analysis`);
}
