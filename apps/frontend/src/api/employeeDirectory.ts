import type { components } from "./generated/openapi-types";
import { ApiError } from "./httpClient";
import { buildApiUrl, typedApiClient } from "./typedClient";

export type EmployeeDirectoryListResponse =
  components["schemas"]["EmployeeDirectoryListResponse"];
export type EmployeeDirectoryProfileResponse =
  components["schemas"]["EmployeeDirectoryProfileResponse"];
export type EmployeeAvatarUploadResponse =
  components["schemas"]["EmployeeAvatarUploadResponse"];

export type EmployeeDirectoryListQuery = {
  search?: string;
  limit?: number;
  offset?: number;
};

function withAuth(accessToken: string): RequestInit {
  return {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  };
}

/**
 * List employee directory cards visible to authenticated employee actors.
 */
export function listEmployeeDirectory(
  accessToken: string,
  query?: EmployeeDirectoryListQuery,
): Promise<EmployeeDirectoryListResponse> {
  return typedApiClient.get<EmployeeDirectoryListResponse>(
    "/api/v1/employees/directory",
    query,
    withAuth(accessToken),
  );
}

/**
 * Read one detailed employee profile from employee-directory scope.
 */
export function getEmployeeDirectoryProfile(
  accessToken: string,
  employeeId: string,
): Promise<EmployeeDirectoryProfileResponse> {
  return typedApiClient.get<EmployeeDirectoryProfileResponse>(
    `/api/v1/employees/directory/${employeeId}`,
    undefined,
    withAuth(accessToken),
  );
}

/**
 * Upload or replace avatar binary for the authenticated employee profile.
 */
export function uploadMyEmployeeAvatar(
  accessToken: string,
  file: File,
): Promise<EmployeeAvatarUploadResponse> {
  const body = new FormData();
  body.append("file", file);
  return typedApiClient.postForm<EmployeeAvatarUploadResponse>(
    "/api/v1/employees/me/avatar",
    body,
    withAuth(accessToken),
  );
}

/**
 * Download employee avatar bytes as Blob for authenticated UI rendering.
 */
export async function getEmployeeAvatarBlob(
  accessToken: string,
  employeeId: string,
): Promise<Blob> {
  const response = await fetch(
    buildApiUrl(`/api/v1/employees/${employeeId}/avatar`),
    withAuth(accessToken),
  );
  if (!response.ok) {
    const detail = await resolveErrorDetail(response);
    throw new ApiError(response.status, detail);
  }
  return response.blob();
}

async function resolveErrorDetail(response: Response): Promise<string> {
  const body = await response.text();
  if (!body.trim()) {
    return `http_${response.status}`;
  }
  try {
    const payload = JSON.parse(body) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.trim()) {
      return payload.detail.trim();
    }
  } catch {
    // Ignore parse failures and keep fallback.
  }
  return `http_${response.status}`;
}
