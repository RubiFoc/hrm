import type { components } from "./generated/openapi-types";
import { typedApiClient } from "./typedClient";

export type PublicVacancyListItemResponse = components["schemas"]["PublicVacancyListItemResponse"];
export type PublicVacancyListResponse = components["schemas"]["PublicVacancyListResponse"];

/**
 * Load the public open-role board for the careers page.
 */
export function listPublicVacancies(): Promise<PublicVacancyListResponse> {
  return typedApiClient.get<PublicVacancyListResponse>("/api/v1/public/vacancies");
}
