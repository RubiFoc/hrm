import type { components } from "./generated/openapi-types";
import { typedApiClient } from "./typedClient";

export type PublicVacancyApplicationResponse =
  components["schemas"]["PublicVacancyApplicationResponse"];

export type PublicVacancyApplicationRequest = {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  consent_confirmed: boolean;
  checksum_sha256: string;
  file: File;
  location?: string | null;
  current_title?: string | null;
  extra_data?: Record<string, unknown> | null;
  website?: string | null;
};

/**
 * Submit one anonymous candidate application to a target vacancy.
 */
export function applyToVacancyPublic(
  vacancyId: string,
  payload: PublicVacancyApplicationRequest,
): Promise<PublicVacancyApplicationResponse> {
  const formData = new FormData();
  formData.set("first_name", payload.first_name);
  formData.set("last_name", payload.last_name);
  formData.set("email", payload.email);
  formData.set("phone", payload.phone);
  formData.set("consent_confirmed", String(payload.consent_confirmed));
  formData.set("checksum_sha256", payload.checksum_sha256);
  formData.set("file", payload.file, payload.file.name);

  if (payload.location?.trim()) {
    formData.set("location", payload.location.trim());
  }
  if (payload.current_title?.trim()) {
    formData.set("current_title", payload.current_title.trim());
  }
  if (payload.extra_data && Object.keys(payload.extra_data).length > 0) {
    formData.set("extra_data", JSON.stringify(payload.extra_data));
  }
  if (payload.website !== undefined) {
    formData.set("website", payload.website ?? "");
  }

  return typedApiClient.postForm<PublicVacancyApplicationResponse>(
    `/api/v1/vacancies/${vacancyId}/applications`,
    formData,
  );
}
