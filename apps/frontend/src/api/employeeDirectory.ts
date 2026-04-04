import type { components } from "./generated/openapi-types";
import { apiRequestBlob } from "./httpClient";
import { buildApiUrl, typedApiClient } from "./typedClient";

export type EmployeeDirectoryListResponse =
  components["schemas"]["EmployeeDirectoryListResponse"];
export type EmployeeDirectoryProfileResponse =
  components["schemas"]["EmployeeDirectoryProfileResponse"];
export type EmployeeProfilePrivacySettingsResponse =
  components["schemas"]["EmployeeProfilePrivacySettingsResponse"];
export type EmployeeProfilePrivacyUpdateRequest =
  components["schemas"]["EmployeeProfilePrivacyUpdateRequest"];
export type EmployeeAvatarUploadResponse =
  components["schemas"]["EmployeeAvatarUploadResponse"];
export type EmployeeAvatarDeleteResponse =
  components["schemas"]["EmployeeAvatarDeleteResponse"];

export type EmployeeDirectoryListQuery = {
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
 * Read employee directory list payload for the authenticated staff actor.
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
 * Read employee directory profile payload by identifier.
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
 * Read privacy settings for the authenticated employee profile.
 */
export function getMyEmployeePrivacySettings(
  accessToken: string,
): Promise<EmployeeProfilePrivacySettingsResponse> {
  return typedApiClient.get<EmployeeProfilePrivacySettingsResponse>(
    "/api/v1/employees/me/privacy",
    undefined,
    withAuth(accessToken),
  );
}

/**
 * Update privacy settings for the authenticated employee profile.
 */
export function updateMyEmployeePrivacySettings(
  accessToken: string,
  payload: EmployeeProfilePrivacyUpdateRequest,
): Promise<EmployeeProfilePrivacySettingsResponse> {
  return typedApiClient.patch<EmployeeProfilePrivacySettingsResponse>(
    "/api/v1/employees/me/privacy",
    payload,
    withAuth(accessToken),
  );
}

/**
 * Upload avatar for the authenticated employee profile.
 */
export function uploadMyEmployeeAvatar(
  accessToken: string,
  file: File,
): Promise<EmployeeAvatarUploadResponse> {
  const formData = new FormData();
  formData.set("file", file, file.name);
  return typedApiClient.postForm<EmployeeAvatarUploadResponse>(
    "/api/v1/employees/me/avatar",
    formData,
    withAuth(accessToken),
  );
}

/**
 * Delete avatar for the authenticated employee profile.
 */
export function deleteMyEmployeeAvatar(
  accessToken: string,
): Promise<EmployeeAvatarDeleteResponse> {
  return typedApiClient.delete<EmployeeAvatarDeleteResponse>(
    "/api/v1/employees/me/avatar",
    withAuth(accessToken),
  );
}

/**
 * Fetch employee avatar as a Blob for rendering in the UI.
 */
export async function fetchEmployeeAvatarBlob(
  accessToken: string,
  employeeId: string,
): Promise<Blob> {
  const url = buildApiUrl(`/api/v1/employees/${employeeId}/avatar`);
  const result = await apiRequestBlob(url, withAuth(accessToken));
  return result.blob;
}
