import type { components, paths } from "./generated/openapi-types";
import { downloadFile } from "./httpClient";
import { buildApiUrl, typedApiClient } from "./typedClient";

export type AuditEventListResponse = components["schemas"]["AuditEventListResponse"];
export type AuditEventExportFormat =
  paths["/api/v1/audit/events/export"]["get"]["parameters"]["query"]["format"];
export type AuditEventListQuery = {
  limit?: number;
  offset?: number;
  action?: string;
  result?: "allowed" | "denied" | "success" | "failure";
  source?: "api" | "job";
  resourceType?: string;
  correlationId?: string;
  occurredFrom?: string;
  occurredTo?: string;
};

/**
 * Load audit events for admin query and export workflows.
 *
 * Inputs:
 * - `query`: optional filter and pagination state from the audit console.
 *
 * Outputs:
 * - resolved audit event list response.
 */
export function listAuditEvents(query: AuditEventListQuery = {}): Promise<AuditEventListResponse> {
  return typedApiClient.get<AuditEventListResponse>(
    "/api/v1/audit/events",
    {
      limit: query.limit,
      offset: query.offset,
      action: query.action,
      result: query.result,
      source: query.source,
      resource_type: query.resourceType,
      correlation_id: query.correlationId,
      occurred_from: query.occurredFrom,
      occurred_to: query.occurredTo,
    },
  );
}

/**
 * Download filtered audit events as CSV, JSONL, or XLSX.
 *
 * Inputs:
 * - `format`: export format selected in the audit console.
 * - `query`: optional filter state reused from the audit list.
 *
 * Outputs:
 * - resolves after the browser download flow is triggered.
 */
export function downloadAuditEventsExport(
  format: AuditEventExportFormat,
  query: AuditEventListQuery = {},
): Promise<void> {
  return downloadFile(
    buildApiUrl("/api/v1/audit/events/export", {
      format,
      limit: query.limit,
      offset: query.offset,
      action: query.action,
      result: query.result,
      source: query.source,
      resource_type: query.resourceType,
      correlation_id: query.correlationId,
      occurred_from: query.occurredFrom,
      occurred_to: query.occurredTo,
    }),
    { method: "GET" },
  ).then(() => undefined);
}
