import { typedApiClient } from "./typedClient";
import type { components } from "./generated/openapi-types";

export type LoginRequest = components["schemas"]["LoginRequest"];
export type TokenResponse = components["schemas"]["TokenResponse"];
export type MeResponse = components["schemas"]["MeResponse"];

/**
 * Authenticate staff user and receive token pair.
 */
export function login(payload: LoginRequest): Promise<TokenResponse> {
  return typedApiClient.post<TokenResponse>("/api/v1/auth/login", payload);
}

/**
 * Read authenticated identity payload for current access token.
 */
export function getMe(accessToken: string): Promise<MeResponse> {
  return typedApiClient.get<MeResponse>("/api/v1/auth/me", undefined, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

/**
 * Invalidate current access token/session on backend side.
 */
export function logout(accessToken: string): Promise<void> {
  return typedApiClient.post<void>("/api/v1/auth/logout", undefined, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}
