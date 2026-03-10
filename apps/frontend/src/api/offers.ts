import type { components } from "./generated/openapi-types";
import { typedApiClient } from "./typedClient";

export type OfferStatus = components["schemas"]["OfferResponse"]["status"];
export type OfferResponse = components["schemas"]["OfferResponse"];
export type OfferUpsertRequest = components["schemas"]["OfferUpsertRequest"];
export type OfferDecisionRequest = components["schemas"]["OfferDecisionRequest"];

function withAuth(accessToken: string): RequestInit {
  return {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  };
}

/**
 * Read current offer lifecycle state for one vacancy and candidate.
 */
export function getOffer(
  accessToken: string,
  vacancyId: string,
  candidateId: string,
): Promise<OfferResponse> {
  return typedApiClient.get<OfferResponse>(
    `/api/v1/vacancies/${vacancyId}/offers/${candidateId}`,
    undefined,
    withAuth(accessToken),
  );
}

/**
 * Create or update draft offer fields.
 */
export function upsertOffer(
  accessToken: string,
  vacancyId: string,
  candidateId: string,
  payload: OfferUpsertRequest,
): Promise<OfferResponse> {
  return typedApiClient.put<OfferResponse>(
    `/api/v1/vacancies/${vacancyId}/offers/${candidateId}`,
    payload,
    withAuth(accessToken),
  );
}

/**
 * Mark one draft offer as sent.
 */
export function sendOffer(
  accessToken: string,
  vacancyId: string,
  candidateId: string,
): Promise<OfferResponse> {
  return typedApiClient.post<OfferResponse>(
    `/api/v1/vacancies/${vacancyId}/offers/${candidateId}/send`,
    undefined,
    withAuth(accessToken),
  );
}

/**
 * Record accepted status for one sent offer.
 */
export function acceptOffer(
  accessToken: string,
  vacancyId: string,
  candidateId: string,
  payload?: OfferDecisionRequest,
): Promise<OfferResponse> {
  return typedApiClient.post<OfferResponse>(
    `/api/v1/vacancies/${vacancyId}/offers/${candidateId}/accept`,
    payload,
    withAuth(accessToken),
  );
}

/**
 * Record declined status for one sent offer.
 */
export function declineOffer(
  accessToken: string,
  vacancyId: string,
  candidateId: string,
  payload?: OfferDecisionRequest,
): Promise<OfferResponse> {
  return typedApiClient.post<OfferResponse>(
    `/api/v1/vacancies/${vacancyId}/offers/${candidateId}/decline`,
    payload,
    withAuth(accessToken),
  );
}
