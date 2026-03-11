import type { components } from "./generated/openapi-types";
import { typedApiClient } from "./typedClient";

export type OnboardingDashboardListResponse =
  components["schemas"]["OnboardingDashboardListResponse"];
export type OnboardingDashboardDetailResponse =
  components["schemas"]["OnboardingDashboardDetailResponse"];
export type OnboardingDashboardTaskStatus =
  components["schemas"]["OnboardingDashboardTaskResponse"]["status"];

export type OnboardingDashboardListQuery = {
  search?: string;
  taskStatus?: OnboardingDashboardTaskStatus;
  assignedRole?: string;
  assignedStaffId?: string;
  overdueOnly?: boolean;
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
 * List onboarding progress rows visible to the current staff actor.
 */
export function listOnboardingDashboardRuns(
  accessToken: string,
  query: OnboardingDashboardListQuery = {},
): Promise<OnboardingDashboardListResponse> {
  return typedApiClient.get<OnboardingDashboardListResponse>(
    "/api/v1/onboarding/runs",
    {
      search: query.search,
      task_status: query.taskStatus,
      assigned_role: query.assignedRole,
      assigned_staff_id: query.assignedStaffId,
      overdue_only: query.overdueOnly,
      limit: query.limit,
      offset: query.offset,
    },
    withAuth(accessToken),
  );
}

/**
 * Read onboarding dashboard detail for one onboarding run.
 */
export function getOnboardingDashboardRun(
  accessToken: string,
  onboardingId: string,
): Promise<OnboardingDashboardDetailResponse> {
  return typedApiClient.get<OnboardingDashboardDetailResponse>(
    `/api/v1/onboarding/runs/${onboardingId}`,
    undefined,
    withAuth(accessToken),
  );
}
