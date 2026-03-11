import type { components } from "./generated/openapi-types";
import { typedApiClient } from "./typedClient";

export type EmployeeOnboardingPortalResponse =
  components["schemas"]["EmployeeOnboardingPortalResponse"];
export type EmployeeOnboardingTaskResponse =
  components["schemas"]["EmployeeOnboardingTaskResponse"];
export type EmployeeOnboardingTaskUpdateRequest =
  components["schemas"]["EmployeeOnboardingTaskUpdateRequest"];
export type EmployeeOnboardingTaskStatus =
  components["schemas"]["EmployeeOnboardingTaskResponse"]["status"];

function withAuth(accessToken: string): RequestInit {
  return {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  };
}

/**
 * Read self-service onboarding portal payload for the authenticated employee.
 */
export function getMyEmployeeOnboardingPortal(
  accessToken: string,
): Promise<EmployeeOnboardingPortalResponse> {
  return typedApiClient.get<EmployeeOnboardingPortalResponse>(
    "/api/v1/employees/me/onboarding",
    undefined,
    withAuth(accessToken),
  );
}

/**
 * Update one employee-actionable onboarding task for the authenticated employee.
 */
export function updateMyEmployeeOnboardingTask(
  accessToken: string,
  taskId: string,
  payload: EmployeeOnboardingTaskUpdateRequest,
): Promise<EmployeeOnboardingTaskResponse> {
  return typedApiClient.patch<EmployeeOnboardingTaskResponse>(
    `/api/v1/employees/me/onboarding/tasks/${taskId}`,
    payload,
    withAuth(accessToken),
  );
}
