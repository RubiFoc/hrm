import type { components } from "./generated/openapi-types";
import { typedApiClient } from "./typedClient";

export type CompensationTableListResponse =
  components["schemas"]["CompensationTableListResponse"];
export type CompensationTableRowResponse =
  components["schemas"]["CompensationTableRowResponse"];
export type CompensationRaiseCreateRequest =
  components["schemas"]["CompensationRaiseCreateRequest"];
export type CompensationRaiseDecisionRequest =
  components["schemas"]["CompensationRaiseDecisionRequest"];
export type CompensationRaiseResponse =
  components["schemas"]["CompensationRaiseResponse"];
export type CompensationRaiseListResponse =
  components["schemas"]["CompensationRaiseListResponse"];
export type CompensationRaiseStatus =
  components["schemas"]["CompensationRaiseStatus"];
export type SalaryBandCreateRequest =
  components["schemas"]["SalaryBandCreateRequest"];
export type SalaryBandListResponse =
  components["schemas"]["SalaryBandListResponse"];
export type SalaryBandResponse =
  components["schemas"]["SalaryBandResponse"];
export type BonusUpsertRequest = components["schemas"]["BonusUpsertRequest"];
export type BonusEntryResponse = components["schemas"]["BonusEntryResponse"];

export type CompensationTableListQuery = {
  limit?: number;
  offset?: number;
};

export type RaiseListQuery = {
  status?: CompensationRaiseStatus;
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
 * Load compensation table rows visible to the current actor.
 */
export function listCompensationTable(
  accessToken: string,
  query: CompensationTableListQuery,
): Promise<CompensationTableListResponse> {
  return typedApiClient.get<CompensationTableListResponse>(
    "/api/v1/compensation/table",
    query,
    withAuth(accessToken),
  );
}

/**
 * List raise requests visible to manager or leader workflows.
 */
export function listRaiseRequests(
  accessToken: string,
  query: RaiseListQuery,
): Promise<CompensationRaiseListResponse> {
  return typedApiClient.get<CompensationRaiseListResponse>(
    "/api/v1/compensation/raises",
    {
      status: query.status,
      limit: query.limit,
      offset: query.offset,
    },
    withAuth(accessToken),
  );
}

/**
 * Create a manager-initiated raise request.
 */
export function createRaiseRequest(
  accessToken: string,
  payload: CompensationRaiseCreateRequest,
): Promise<CompensationRaiseResponse> {
  return typedApiClient.post<CompensationRaiseResponse>(
    "/api/v1/compensation/raises",
    payload,
    withAuth(accessToken),
  );
}

/**
 * Confirm a raise request as manager.
 */
export function confirmRaiseRequest(
  accessToken: string,
  raiseRequestId: string,
): Promise<CompensationRaiseResponse> {
  return typedApiClient.post<CompensationRaiseResponse>(
    `/api/v1/compensation/raises/${raiseRequestId}/confirm`,
    undefined,
    withAuth(accessToken),
  );
}

/**
 * Approve a raise request as leader.
 */
export function approveRaiseRequest(
  accessToken: string,
  raiseRequestId: string,
  payload: CompensationRaiseDecisionRequest,
): Promise<CompensationRaiseResponse> {
  return typedApiClient.post<CompensationRaiseResponse>(
    `/api/v1/compensation/raises/${raiseRequestId}/approve`,
    payload,
    withAuth(accessToken),
  );
}

/**
 * Reject a raise request as leader.
 */
export function rejectRaiseRequest(
  accessToken: string,
  raiseRequestId: string,
  payload: CompensationRaiseDecisionRequest,
): Promise<CompensationRaiseResponse> {
  return typedApiClient.post<CompensationRaiseResponse>(
    `/api/v1/compensation/raises/${raiseRequestId}/reject`,
    payload,
    withAuth(accessToken),
  );
}

/**
 * List salary band history for a vacancy.
 */
export function listSalaryBands(
  accessToken: string,
  vacancyId: string,
): Promise<SalaryBandListResponse> {
  return typedApiClient.get<SalaryBandListResponse>(
    "/api/v1/compensation/salary-bands",
    { vacancy_id: vacancyId },
    withAuth(accessToken),
  );
}

/**
 * Create a salary band entry for a vacancy.
 */
export function createSalaryBand(
  accessToken: string,
  payload: SalaryBandCreateRequest,
): Promise<SalaryBandResponse> {
  return typedApiClient.post<SalaryBandResponse>(
    "/api/v1/compensation/salary-bands",
    payload,
    withAuth(accessToken),
  );
}

/**
 * Create or update a manual bonus entry.
 */
export function upsertBonusEntry(
  accessToken: string,
  payload: BonusUpsertRequest,
): Promise<BonusEntryResponse> {
  return typedApiClient.post<BonusEntryResponse>(
    "/api/v1/compensation/bonuses",
    payload,
    withAuth(accessToken),
  );
}
