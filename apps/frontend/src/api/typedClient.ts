import { apiRequest } from "./httpClient";
import type { paths } from "./generated/openapi-types";

export type ApiPath = keyof paths & string;
type QueryValue = string | number | boolean | null | undefined;
type QueryParams = Record<string, QueryValue>;

export function createTypedApiClient(baseUrl = "") {
  return {
    request<TResponse>(path: string, init: RequestInit) {
      return apiRequest<TResponse>(`${baseUrl}${path}`, init);
    },
    get<TResponse>(path: string, query?: QueryParams, init?: RequestInit) {
      return apiRequest<TResponse>(`${baseUrl}${appendQuery(path, query)}`, {
        ...init,
        method: "GET",
      });
    },
    post<TResponse>(path: string, body: unknown, init?: RequestInit) {
      return apiRequest<TResponse>(
        `${baseUrl}${path}`,
        withJsonRequestInit("POST", body, init),
      );
    },
    patch<TResponse>(path: string, body: unknown, init?: RequestInit) {
      return apiRequest<TResponse>(
        `${baseUrl}${path}`,
        withJsonRequestInit("PATCH", body, init),
      );
    },
    postForm<TResponse>(path: string, body: FormData, init?: RequestInit) {
      return apiRequest<TResponse>(`${baseUrl}${path}`, {
        ...init,
        method: "POST",
        body,
      });
    },
  };
}

function resolveApiBaseUrl(): string {
  const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL;
  if (typeof configuredBaseUrl !== "string") {
    return "";
  }
  const normalized = configuredBaseUrl.trim();
  if (!normalized) {
    return "";
  }
  return normalized.replace(/\/+$/, "");
}

export const typedApiClient = createTypedApiClient(resolveApiBaseUrl());

function withJsonRequestInit(
  method: "POST" | "PATCH",
  body: unknown,
  init?: RequestInit,
): RequestInit {
  if (body === undefined) {
    return {
      ...init,
      method,
    };
  }

  return {
    ...init,
    method,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    body: JSON.stringify(body),
  };
}

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
