import { apiRequest } from "./httpClient";
import type { paths } from "./generated/openapi-types";

export type ApiPath = keyof paths & string;
type QueryValue = string | number | boolean | null | undefined;
type QueryParams = Record<string, QueryValue>;

export function createTypedApiClient(baseUrl = "") {
  return {
    get<TResponse>(path: string, query?: QueryParams, init?: RequestInit) {
      return apiRequest<TResponse>(`${baseUrl}${appendQuery(path, query)}`, {
        ...init,
        method: "GET",
      });
    },
    post<TResponse>(path: string, body: unknown, init?: RequestInit) {
      return apiRequest<TResponse>(`${baseUrl}${path}`, {
        ...init,
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(init?.headers ?? {}),
        },
        body: JSON.stringify(body),
      });
    },
    patch<TResponse>(path: string, body: unknown, init?: RequestInit) {
      return apiRequest<TResponse>(`${baseUrl}${path}`, {
        ...init,
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(init?.headers ?? {}),
        },
        body: JSON.stringify(body),
      });
    },
  };
}

export const typedApiClient = createTypedApiClient();

function appendQuery(path: string, query?: QueryParams): string {
  if (!query) {
    return path;
  }

  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") {
      continue;
    }
    search.set(key, String(value));
  }

  const encoded = search.toString();
  if (!encoded) {
    return path;
  }
  return `${path}?${encoded}`;
}
