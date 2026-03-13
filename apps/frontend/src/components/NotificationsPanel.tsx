import {
  Alert,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import {
  ApiError,
  getNotificationDigest,
  listNotifications,
  markNotificationRead,
  type NotificationDigestResponse,
  type NotificationResponse,
} from "../api";

const MAX_UNREAD_ITEMS = 5;
const EMPTY_DIGEST: NotificationDigestResponse = {
  generated_at: "",
  summary: {
    unread_notification_count: 0,
    active_task_count: 0,
    overdue_task_count: 0,
    owned_open_vacancy_count: 0,
  },
  latest_unread_items: [],
};

type NotificationsPanelProps = {
  accessToken: string;
  workspace: "manager" | "accountant";
};

/**
 * Shared in-app notifications panel for manager and accountant workspaces.
 */
export function NotificationsPanel({ accessToken, workspace }: NotificationsPanelProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const digestQuery = useQuery({
    queryKey: ["notifications-digest", accessToken],
    queryFn: () => getNotificationDigest(accessToken),
    enabled: Boolean(accessToken),
    retry: false,
  });
  const listQuery = useQuery({
    queryKey: ["notifications-list", accessToken],
    queryFn: () =>
      listNotifications(accessToken, {
        status: "unread",
        limit: MAX_UNREAD_ITEMS,
        offset: 0,
      }),
    enabled: Boolean(accessToken),
    retry: false,
  });
  const markReadMutation = useMutation({
    mutationFn: (notificationId: string) => markNotificationRead(accessToken, notificationId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["notifications-digest", accessToken],
        }),
        queryClient.invalidateQueries({
          queryKey: ["notifications-list", accessToken],
        }),
      ]);
    },
  });

  const summary = digestQuery.data?.summary ?? EMPTY_DIGEST.summary;
  const unreadItems = Array.isArray(listQuery.data?.items)
    ? listQuery.data.items
    : Array.isArray(digestQuery.data?.latest_unread_items)
      ? digestQuery.data.latest_unread_items
      : [];
  const hasLoadedPayload = digestQuery.isSuccess || listQuery.isSuccess;
  const error = digestQuery.error ?? listQuery.error;

  return (
    <Paper sx={{ p: 3 }}>
      <Stack spacing={2.5}>
        <Stack spacing={0.5}>
          <Typography variant="h6">{t("notificationsPanel.title")}</Typography>
          <Typography variant="body2" color="text.secondary">
            {t(`notificationsPanel.subtitle.${workspace}`)}
          </Typography>
        </Stack>

        <Stack direction={{ xs: "column", md: "row" }} spacing={1} flexWrap="wrap" useFlexGap>
          <Chip
            label={t("notificationsPanel.summary.unread", {
              value: summary.unread_notification_count,
            })}
            color="primary"
            variant="outlined"
          />
          <Chip
            label={t("notificationsPanel.summary.activeTasks", {
              value: summary.active_task_count,
            })}
            variant="outlined"
          />
          <Chip
            label={t("notificationsPanel.summary.overdueTasks", {
              value: summary.overdue_task_count,
            })}
            color={summary.overdue_task_count > 0 ? "warning" : "default"}
            variant="outlined"
          />
          {workspace === "manager" ? (
            <Chip
              label={t("notificationsPanel.summary.openVacancies", {
                value: summary.owned_open_vacancy_count,
              })}
              variant="outlined"
            />
          ) : null}
        </Stack>

        {!hasLoadedPayload && (digestQuery.isLoading || listQuery.isLoading) ? (
          <Stack spacing={2} alignItems="center" sx={{ py: 2 }}>
            <CircularProgress size={24} />
            <Typography variant="body2">{t("notificationsPanel.loading")}</Typography>
          </Stack>
        ) : null}

        {error ? (
          <Alert severity="error">{resolveNotificationsError(error, t)}</Alert>
        ) : null}

        {error || (!hasLoadedPayload && (digestQuery.isLoading || listQuery.isLoading)) ? null : unreadItems.length === 0 ? (
          <Alert severity="info">{t("notificationsPanel.empty")}</Alert>
        ) : (
          <Stack divider={<Divider flexItem />}>
            {unreadItems.map((notification) => (
              <NotificationRow
                key={notification.notification_id}
                notification={notification}
                isPending={markReadMutation.isPending && markReadMutation.variables === notification.notification_id}
                onMarkRead={() => markReadMutation.mutate(notification.notification_id)}
              />
            ))}
          </Stack>
        )}
      </Stack>
    </Paper>
  );
}

type NotificationRowProps = {
  notification: NotificationResponse;
  isPending: boolean;
  onMarkRead: () => void;
};

function NotificationRow({ notification, isPending, onMarkRead }: NotificationRowProps) {
  const { t } = useTranslation();

  return (
    <Stack
      direction={{ xs: "column", md: "row" }}
      spacing={2}
      justifyContent="space-between"
      sx={{ py: 1.5 }}
    >
      <Stack spacing={0.75}>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
          <Typography variant="subtitle2">{notification.title}</Typography>
          <Chip
            label={t("notificationsPanel.unread")}
            size="small"
            color="primary"
            variant="outlined"
          />
        </Stack>
        <Typography variant="body2">{notification.body}</Typography>
        <Typography variant="caption" color="text.secondary">
          {t("notificationsPanel.receivedAt", {
            value: formatDateTimeValue(notification.created_at),
          })}
        </Typography>
      </Stack>

      <Stack direction="row" justifyContent={{ xs: "flex-start", md: "flex-end" }}>
        <Button size="small" variant="outlined" disabled={isPending} onClick={onMarkRead}>
          {isPending
            ? t("notificationsPanel.markReadPending")
            : t("notificationsPanel.markRead")}
        </Button>
      </Stack>
    </Stack>
  );
}

function resolveNotificationsError(
  error: unknown,
  t: (key: string, options?: Record<string, unknown>) => string,
): string {
  if (error instanceof ApiError) {
    return t(`notificationsPanel.errors.${error.detail}`, {
      defaultValue: t(`notificationsPanel.errors.http_${error.status}`, {
        defaultValue: t("notificationsPanel.errors.generic"),
      }),
    });
  }
  return t("notificationsPanel.errors.generic");
}

function formatDateTimeValue(value: string): string {
  if (!value) {
    return "";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}
