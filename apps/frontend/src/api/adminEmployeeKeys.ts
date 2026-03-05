import { typedApiClient } from "./typedClient";
import type { components } from "./generated/openapi-types";
import type { StaffRoleClaim } from "./adminStaff";

export type EmployeeKeyStatus = components["schemas"]["AdminEmployeeKeyListItem"]["status"];
export type AdminEmployeeKeyListItem = components["schemas"]["AdminEmployeeKeyListItem"];
export type AdminEmployeeKeyListResponse = components["schemas"]["AdminEmployeeKeyListResponse"];
export type AdminCreateEmployeeKeyRequest = components["schemas"]["AdminCreateEmployeeKeyRequest"];
export type EmployeeRegistrationKeyResponse = components["schemas"]["EmployeeRegistrationKeyResponse"];

export type AdminEmployeeKeyListQuery = {
  limit: number;
  offset: number;
  target_role?: StaffRoleClaim;
  status?: EmployeeKeyStatus;
  created_by_staff_id?: string;
  search?: string;
};

export function listAdminEmployeeKeys(
  query: AdminEmployeeKeyListQuery,
): Promise<AdminEmployeeKeyListResponse> {
  return typedApiClient.get<AdminEmployeeKeyListResponse>("/api/v1/admin/employee-keys", query);
}

export function createAdminEmployeeKey(
  payload: AdminCreateEmployeeKeyRequest,
): Promise<EmployeeRegistrationKeyResponse> {
  return typedApiClient.post<EmployeeRegistrationKeyResponse>("/api/v1/admin/employee-keys", payload);
}

export function revokeAdminEmployeeKey(keyId: string): Promise<AdminEmployeeKeyListItem> {
  return typedApiClient.post<AdminEmployeeKeyListItem>(`/api/v1/admin/employee-keys/${keyId}/revoke`, {});
}
