import type { components } from "./generated/openapi-types";
import { downloadFile } from "./httpClient";
import { buildApiUrl, typedApiClient } from "./typedClient";

export type AccountingWorkspaceListResponse =
  components["schemas"]["AccountingWorkspaceListResponse"];
export type AccountingWorkspaceRowResponse =
  components["schemas"]["AccountingWorkspaceRowResponse"];
export type AccountingWorkspaceExportFormat = "csv" | "xlsx";

export type AccountingWorkspaceListQuery = {
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
 * Load accountant-visible onboarding rows for the current actor.
 */
export function listAccountingWorkspace(
  accessToken: string,
  query: AccountingWorkspaceListQuery,
): Promise<AccountingWorkspaceListResponse> {
  return typedApiClient.get<AccountingWorkspaceListResponse>(
    "/api/v1/accounting/workspace",
    query,
    withAuth(accessToken),
  );
}

/**
 * Download the full filtered accountant workspace scope as CSV or XLSX.
 */
export function downloadAccountingWorkspaceExport(
  accessToken: string,
  format: AccountingWorkspaceExportFormat,
  search?: string,
): Promise<void> {
  return downloadFile(
    buildApiUrl("/api/v1/accounting/workspace/export", {
      format,
      search,
    }),
    {
      ...withAuth(accessToken),
      method: "GET",
    },
  ).then(() => undefined);
}
