import type { components } from "./generated/openapi-types";
import { typedApiClient } from "./typedClient";

export type NotificationListStatus = "unread" | "all";
export type NotificationPayloadResponse = components["schemas"]["NotificationPayload"];
export type NotificationResponse = components["schemas"]["NotificationResponse"];
export type NotificationListResponse = components["schemas"]["NotificationListResponse"];
export type NotificationDigestSummaryResponse =
  components["schemas"]["NotificationDigestSummaryResponse"];
export type NotificationDigestResponse = components["schemas"]["NotificationDigestResponse"];

export type NotificationListQuery = {
  status?: NotificationListStatus;
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
 * Load recipient-scoped notifications for the current authenticated staff subject.
 */
export function listNotifications(
  accessToken: string,
  query: NotificationListQuery,
): Promise<NotificationListResponse> {
  return typedApiClient.get<NotificationListResponse>(
    "/api/v1/notifications",
    query,
    withAuth(accessToken),
  );
}

/**
 * Load the on-demand digest for the current authenticated recipient.
 */
export function getNotificationDigest(accessToken: string): Promise<NotificationDigestResponse> {
  return typedApiClient.get<NotificationDigestResponse>(
    "/api/v1/notifications/digest",
    undefined,
    withAuth(accessToken),
  );
}

/**
 * Mark one recipient-owned notification as read.
 */
export function markNotificationRead(
  accessToken: string,
  notificationId: string,
): Promise<NotificationResponse> {
  return typedApiClient.post<NotificationResponse>(
    `/api/v1/notifications/${notificationId}/read`,
    undefined,
    withAuth(accessToken),
  );
}
