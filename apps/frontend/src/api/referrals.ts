import type { components } from "./generated/openapi-types";
import { typedApiClient } from "./typedClient";

export type ReferralSubmitResponse = components["schemas"]["ReferralSubmitResponse"];
export type ReferralListResponse = components["schemas"]["ReferralListResponse"];
export type ReferralListItemResponse = components["schemas"]["ReferralListItemResponse"];
export type ReferralReviewRequest = components["schemas"]["ReferralReviewRequest"];
export type ReferralReviewResponse = components["schemas"]["ReferralReviewResponse"];

export type ReferralSubmitRequest = {
  vacancy_id: string;
  full_name: string;
  phone: string;
  email: string;
  checksum_sha256: string;
  file: File;
};

function withAuth(accessToken: string): RequestInit {
  return {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  };
}

/**
 * Submit an employee referral for a vacancy.
 */
export function submitReferral(
  accessToken: string,
  payload: ReferralSubmitRequest,
): Promise<ReferralSubmitResponse> {
  const formData = new FormData();
  formData.set("vacancy_id", payload.vacancy_id);
  formData.set("full_name", payload.full_name);
  formData.set("phone", payload.phone);
  formData.set("email", payload.email);
  formData.set("checksum_sha256", payload.checksum_sha256);
  formData.set("file", payload.file, payload.file.name);

  return typedApiClient.postForm<ReferralSubmitResponse>(
    "/api/v1/referrals",
    formData,
    withAuth(accessToken),
  );
}

/**
 * Read referral submissions visible to the current staff role.
 */
export function listReferrals(
  accessToken: string,
  query?: { vacancy_id?: string; limit?: number; offset?: number },
): Promise<ReferralListResponse> {
  return typedApiClient.get<ReferralListResponse>(
    "/api/v1/referrals",
    query,
    withAuth(accessToken),
  );
}

/**
 * Append a review transition to the referral candidate pipeline.
 */
export function reviewReferral(
  accessToken: string,
  referralId: string,
  payload: ReferralReviewRequest,
): Promise<ReferralReviewResponse> {
  return typedApiClient.post<ReferralReviewResponse>(
    `/api/v1/referrals/${referralId}/review`,
    payload,
    withAuth(accessToken),
  );
}
