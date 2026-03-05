import { apiRequest } from "./httpClient";
import type { paths } from "./generated/openapi-types";

export type ApiPath = keyof paths & string;

export function createTypedApiClient(baseUrl = "") {
  return {
    get<TResponse>(path: ApiPath, init?: RequestInit) {
      return apiRequest<TResponse>(`${baseUrl}${path}`, {
        ...init,
        method: "GET",
      });
    },
    post<TResponse>(path: ApiPath, body: unknown, init?: RequestInit) {
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
  };
}

export const typedApiClient = createTypedApiClient();
