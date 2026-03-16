import type { components } from "./generated/openapi-types";
import { downloadFile } from "./httpClient";
import { buildApiUrl, typedApiClient } from "./typedClient";

export type KpiSnapshotMetric = components["schemas"]["KpiSnapshotMetric"];
export type KpiSnapshotReadResponse = components["schemas"]["KpiSnapshotReadResponse"];
export type KpiSnapshotExportFormat = "csv" | "xlsx";

function withAuth(accessToken: string): RequestInit {
  return {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  };
}

/**
 * Read stored KPI snapshot metrics for one calendar month.
 */
export function readKpiSnapshot(
  accessToken: string,
  periodMonth: string,
): Promise<KpiSnapshotReadResponse> {
  return typedApiClient.get<KpiSnapshotReadResponse>(
    "/api/v1/reporting/kpi-snapshots",
    {
      period_month: periodMonth,
    },
    withAuth(accessToken),
  );
}

/**
 * Download KPI snapshot attachment for one calendar month.
 */
export function downloadKpiSnapshotExport(
  accessToken: string,
  format: KpiSnapshotExportFormat,
  periodMonth: string,
): Promise<void> {
  return downloadFile(
    buildApiUrl("/api/v1/reporting/kpi-snapshots/export", {
      format,
      period_month: periodMonth,
    }),
    {
      ...withAuth(accessToken),
      method: "GET",
    },
  ).then(() => undefined);
}

