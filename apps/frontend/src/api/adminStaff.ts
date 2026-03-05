import { typedApiClient } from "./typedClient";
import type { components } from "./generated/openapi-types";

export type StaffRoleClaim = components["schemas"]["AdminCreateStaffRequest"]["role"];
export type AdminStaffListItem = components["schemas"]["AdminStaffListItem"];
export type AdminStaffListResponse = components["schemas"]["AdminStaffListResponse"];
export type AdminStaffUpdateRequest = components["schemas"]["AdminStaffUpdateRequest"];

export type AdminStaffListQuery = {
  limit: number;
  offset: number;
  search?: string;
  role?: StaffRoleClaim;
  is_active?: boolean;
};

export function listAdminStaff(query: AdminStaffListQuery): Promise<AdminStaffListResponse> {
  return typedApiClient.get<AdminStaffListResponse>("/api/v1/admin/staff", query);
}

export function updateAdminStaff(
  staffId: string,
  payload: AdminStaffUpdateRequest,
): Promise<AdminStaffListItem> {
  return typedApiClient.patch<AdminStaffListItem>(`/api/v1/admin/staff/${staffId}`, payload);
}
