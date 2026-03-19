import type { paths } from "./generated/openapi-types";
import { typedApiClient } from "./typedClient";

export type BackendHealthResponse = paths["/health"]["get"]["responses"][200]["content"]["application/json"];

/**
 * Read the backend health payload from the shared monitoring endpoint.
 *
 * Outputs:
 * - the current `/health` response body, which is a compact status map.
 *
 * Side effects:
 * - performs one read-only HTTP request against the backend health endpoint.
 */
export function getBackendHealth(): Promise<BackendHealthResponse> {
  return typedApiClient.get<BackendHealthResponse>("/health");
}
