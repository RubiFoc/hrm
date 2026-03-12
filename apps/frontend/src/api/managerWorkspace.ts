import type { components } from "./generated/openapi-types";
import { typedApiClient } from "./typedClient";

export type ManagerWorkspaceOverviewResponse =
  components["schemas"]["ManagerWorkspaceOverviewResponse"];
export type ManagerWorkspaceVacancyListItemResponse =
  components["schemas"]["ManagerWorkspaceVacancyListItemResponse"];
export type ManagerWorkspaceCandidateSnapshotResponse =
  components["schemas"]["ManagerWorkspaceCandidateSnapshotResponse"];
export type ManagerWorkspaceCandidateSnapshotItemResponse =
  components["schemas"]["ManagerWorkspaceCandidateSnapshotItemResponse"];
export type ManagerWorkspaceCandidateSnapshotSummaryResponse =
  components["schemas"]["ManagerWorkspaceCandidateSnapshotSummaryResponse"];
export type ManagerWorkspaceStageSummaryResponse =
  components["schemas"]["ManagerWorkspaceStageSummaryResponse"];

function withAuth(accessToken: string): RequestInit {
  return {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  };
}

/**
 * Load manager-scoped hiring summary plus visible vacancies.
 */
export function getManagerWorkspaceOverview(
  accessToken: string,
): Promise<ManagerWorkspaceOverviewResponse> {
  return typedApiClient.get<ManagerWorkspaceOverviewResponse>(
    "/api/v1/vacancies/manager-workspace",
    undefined,
    withAuth(accessToken),
  );
}

/**
 * Load the read-only candidate snapshot for one manager-visible vacancy.
 */
export function getManagerWorkspaceCandidateSnapshot(
  accessToken: string,
  vacancyId: string,
): Promise<ManagerWorkspaceCandidateSnapshotResponse> {
  return typedApiClient.get<ManagerWorkspaceCandidateSnapshotResponse>(
    `/api/v1/vacancies/${vacancyId}/manager-workspace/candidates`,
    undefined,
    withAuth(accessToken),
  );
}
