/**
 * Lightweight typed HTTP wrapper for API calls.
 *
 * Generated OpenAPI types are created via `npm run api:types:generate`
 * into `src/api/generated/openapi-types.ts` and can be referenced in
 * higher-level API modules.
 */
export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`API request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export async function apiRequest<TResponse>(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<TResponse> {
  const response = await fetch(input, init);
  const rawBody = await response.text();
  const payload = parseJsonBody(rawBody);

  if (!response.ok) {
    const detail = resolveErrorDetail(payload, response.status);
    throw new ApiError(response.status, detail);
  }

  if (!rawBody.trim()) {
    return undefined as TResponse;
  }

  if (payload !== undefined) {
    return payload as TResponse;
  }
  return rawBody as TResponse;
}

function parseJsonBody(rawBody: string): unknown | undefined {
  if (!rawBody.trim()) {
    return undefined;
  }
  try {
    return JSON.parse(rawBody) as unknown;
  } catch {
    return undefined;
  }
}

function resolveErrorDetail(payload: unknown, status: number): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail.trim();
    }
  }
  return `http_${status}`;
}
