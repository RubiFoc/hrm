import type { components } from "./generated/openapi-types";
import { typedApiClient } from "./typedClient";

export type DepartmentListResponse = components["schemas"]["DepartmentListResponse"];
export type DepartmentResponse = components["schemas"]["DepartmentResponse"];
export type DepartmentCreateRequest = components["schemas"]["DepartmentCreateRequest"];
export type DepartmentUpdateRequest = components["schemas"]["DepartmentUpdateRequest"];

export type DepartmentListQuery = {
  limit?: number;
  offset?: number;
  search?: string;
};

function withAuth(accessToken: string): RequestInit {
  return {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  };
}

/**
 * List departments with pagination and optional search.
 */
export function listDepartments(
  accessToken: string,
  query?: DepartmentListQuery,
): Promise<DepartmentListResponse> {
  return typedApiClient.get<DepartmentListResponse>(
    "/api/v1/departments",
    query,
    withAuth(accessToken),
  );
}

/**
 * Fetch a single department by identifier.
 */
export function getDepartment(
  accessToken: string,
  departmentId: string,
): Promise<DepartmentResponse> {
  return typedApiClient.get<DepartmentResponse>(
    `/api/v1/departments/${departmentId}`,
    undefined,
    withAuth(accessToken),
  );
}

/**
 * Create a new department.
 */
export function createDepartment(
  accessToken: string,
  payload: DepartmentCreateRequest,
): Promise<DepartmentResponse> {
  return typedApiClient.post<DepartmentResponse>(
    "/api/v1/departments",
    payload,
    withAuth(accessToken),
  );
}

/**
 * Update an existing department.
 */
export function updateDepartment(
  accessToken: string,
  departmentId: string,
  payload: DepartmentUpdateRequest,
): Promise<DepartmentResponse> {
  return typedApiClient.patch<DepartmentResponse>(
    `/api/v1/departments/${departmentId}`,
    payload,
    withAuth(accessToken),
  );
}
