/**
 * Lightweight typed HTTP wrapper for API calls.
 *
 * Generated OpenAPI types are created via `npm run api:types:generate`
 * into `src/api/generated/openapi-types.ts` and can be referenced in
 * higher-level API modules.
 */
export async function apiRequest<TResponse>(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<TResponse> {
  const response = await fetch(input, init);
  if (!response.ok) {
    throw new Error(`API request failed with status ${response.status}`);
  }
  return (await response.json()) as TResponse;
}
