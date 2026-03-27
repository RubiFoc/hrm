import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Avatar,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Grid2,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import {
  ApiError,
  getEmployeeAvatarBlob,
  listEmployeeDirectory,
  getMyEmployeeOnboardingPortal,
  uploadMyEmployeeAvatar,
  updateMyEmployeeOnboardingTask,
  type EmployeeDirectoryListResponse,
  type EmployeeOnboardingPortalResponse,
  type EmployeeOnboardingTaskStatus,
} from "../api";
import { readAuthSession } from "../app/auth/session";
import { useSentryRouteTags } from "../app/observability/sentry";
import { PageHero } from "../components/PageHero";

type FeedbackState = {
  type: "success" | "error";
  message: string;
};

type EmployeeDirectoryItem = EmployeeDirectoryListResponse["items"][number];

/**
 * Employee self-service onboarding workspace.
 */
export function EmployeeOnboardingPage() {
  const { t } = useTranslation();
  useSentryRouteTags("/employee");
  const queryClient = useQueryClient();
  const session = readAuthSession();
  const accessToken = session.accessToken;
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const [pendingTaskId, setPendingTaskId] = useState<string | null>(null);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const queryKey = ["employee-onboarding-portal", accessToken];
  const directoryQueryKey = ["employee-directory", accessToken];

  const portalQuery = useQuery({
    queryKey,
    queryFn: () => getMyEmployeeOnboardingPortal(accessToken!),
    enabled: Boolean(accessToken),
    retry: false,
  });
  const directoryQuery = useQuery({
    queryKey: directoryQueryKey,
    queryFn: () => listEmployeeDirectory(accessToken!, { limit: 20, offset: 0 }),
    enabled: Boolean(accessToken),
    retry: false,
  });

  const updateTaskMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: string; status: EmployeeOnboardingTaskStatus }) =>
      updateMyEmployeeOnboardingTask(accessToken!, taskId, { status }),
    onMutate: ({ taskId }) => {
      setFeedback(null);
      setPendingTaskId(taskId);
    },
    onSuccess: (updatedTask) => {
      setFeedback({ type: "success", message: t("employeePortal.updateSuccess") });
      queryClient.setQueryData<EmployeeOnboardingPortalResponse | undefined>(queryKey, (current) =>
        current
          ? {
              ...current,
              tasks: current.tasks.map((task) =>
                task.task_id === updatedTask.task_id ? updatedTask : task,
              ),
            }
          : current,
      );
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveEmployeePortalError(error, t) });
    },
    onSettled: () => {
      setPendingTaskId(null);
    },
  });
  const updateAvatarMutation = useMutation({
    mutationFn: (file: File) => uploadMyEmployeeAvatar(accessToken!, file),
    onMutate: () => {
      setFeedback(null);
      setAvatarUploading(true);
    },
    onSuccess: () => {
      setFeedback({ type: "success", message: t("employeePortal.directory.avatarUpdated") });
      void queryClient.invalidateQueries({ queryKey: directoryQueryKey });
      void queryClient.invalidateQueries({ queryKey });
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveEmployeePortalError(error, t) });
    },
    onSettled: () => {
      setAvatarUploading(false);
    },
  });

  if (!accessToken) {
    return (
      <Stack spacing={2}>
        <PageHero
          title={t("employeeWorkspace")}
          description={t("employeePortal.subtitle")}
          imageSrc="/images/candidate-portal.jpg"
          imageAlt={t("employeeWorkspace")}
        />
        <Alert severity="warning">{t("employeePortal.authRequired")}</Alert>
      </Stack>
    );
  }

  if (portalQuery.isLoading) {
    return (
      <Stack spacing={2} alignItems="center" sx={{ py: 6 }}>
        <CircularProgress size={28} />
        <Typography variant="body2">{t("employeePortal.loading")}</Typography>
      </Stack>
    );
  }

  if (portalQuery.isError) {
    return (
      <Stack spacing={2}>
        <PageHero
          title={t("employeeWorkspace")}
          description={t("employeePortal.subtitle")}
          imageSrc="/images/candidate-portal.jpg"
          imageAlt={t("employeeWorkspace")}
        />
        <Alert severity="error">{resolveEmployeePortalError(portalQuery.error, t)}</Alert>
      </Stack>
    );
  }

  const portal = portalQuery.data;
  if (!portal) {
    return null;
  }
  const noValue = t("employeePortal.noValue");
  const directoryItems = Array.isArray(directoryQuery.data?.items)
    ? directoryQuery.data.items
    : [];
  const hasDirectoryItems = directoryItems.length > 0;

  return (
    <Stack spacing={3}>
      <PageHero
        title={t("employeePortal.title")}
        description={t("employeePortal.subtitle")}
        imageSrc="/images/candidate-portal.jpg"
        imageAlt={t("employeePortal.title")}
      />

      {feedback ? <Alert severity={feedback.type}>{feedback.message}</Alert> : null}

      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Stack spacing={1}>
            <Typography variant="h5">
              {portal.first_name} {portal.last_name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {portal.email}
            </Typography>
          </Stack>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1} flexWrap="wrap">
            <Chip
              label={t("employeePortal.summary.onboardingStatus", {
                value: portal.onboarding_status
                  ? t(`employeePortal.status.${portal.onboarding_status}`)
                  : noValue,
              })}
              color="primary"
              variant="outlined"
            />
            <Chip
              label={t("employeePortal.summary.currentTitle", {
                value: portal.current_title || noValue,
              })}
              variant="outlined"
            />
            <Chip
              label={t("employeePortal.summary.location", {
                value: portal.location || noValue,
              })}
              variant="outlined"
            />
            <Chip
              label={t("employeePortal.summary.startDate", {
                value: formatDateValue(portal.start_date, noValue),
              })}
              variant="outlined"
            />
          </Stack>
          {portal.offer_terms_summary ? (
            <>
              <Divider />
              <Typography variant="body2">{portal.offer_terms_summary}</Typography>
            </>
          ) : null}
        </Stack>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Typography variant="h6">{t("employeePortal.directory.title")}</Typography>
          {directoryQuery.isLoading ? (
            <Stack direction="row" spacing={1} alignItems="center">
              <CircularProgress size={20} />
              <Typography variant="body2">{t("employeePortal.directory.loading")}</Typography>
            </Stack>
          ) : null}
          {directoryQuery.isError ? (
            <Alert severity="error">{resolveEmployeePortalError(directoryQuery.error, t)}</Alert>
          ) : null}
          {directoryQuery.data && directoryItems.length === 0 ? (
            <Alert severity="info">{t("employeePortal.directory.empty")}</Alert>
          ) : null}
          {directoryQuery.data && hasDirectoryItems ? (
            <Grid2 container spacing={2}>
              {directoryItems.map((item) => {
                const isSelf = item.employee_id === portal.employee_id;
                return (
                  <Grid2 key={item.employee_id} size={{ xs: 12, md: 6 }}>
                    <Paper variant="outlined" sx={{ p: 2, height: "100%" }}>
                      <Stack spacing={1.5} sx={{ height: "100%" }}>
                        <Stack direction="row" spacing={1.5} alignItems="center">
                          <DirectoryAvatar
                            accessToken={accessToken}
                            profile={item}
                          />
                          <Stack spacing={0.25}>
                            <Typography variant="subtitle1">{item.full_name}</Typography>
                            <Typography variant="body2" color="text.secondary">
                              {item.position_title || t("employeePortal.noValue")}
                            </Typography>
                          </Stack>
                        </Stack>
                        <Typography variant="body2" color="text.secondary">
                          {item.email}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {item.phone || t("employeePortal.noValue")}
                        </Typography>
                        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                          <Chip
                            size="small"
                            variant="outlined"
                            label={t("employeePortal.directory.department", {
                              value: item.department || t("employeePortal.noValue"),
                            })}
                          />
                          <Chip
                            size="small"
                            variant="outlined"
                            label={t("employeePortal.directory.location", {
                              value: item.location || t("employeePortal.noValue"),
                            })}
                          />
                          <Chip
                            size="small"
                            variant="outlined"
                            label={t("employeePortal.directory.tenureMonths", {
                              value:
                                item.tenure_in_company_months != null
                                  ? String(item.tenure_in_company_months)
                                  : t("employeePortal.noValue"),
                            })}
                          />
                        </Stack>
                        {isSelf ? (
                          <Button
                            component="label"
                            variant="outlined"
                            size="small"
                            disabled={avatarUploading}
                            sx={{ mt: "auto", alignSelf: "flex-start" }}
                          >
                            {avatarUploading
                              ? t("employeePortal.directory.uploadingAvatar")
                              : t("employeePortal.directory.updateAvatar")}
                            <input
                              hidden
                              type="file"
                              accept="image/png,image/jpeg,image/webp"
                              onChange={(event) => {
                                const file = event.currentTarget.files?.[0];
                                event.currentTarget.value = "";
                                if (!file) {
                                  return;
                                }
                                updateAvatarMutation.mutate(file);
                              }}
                            />
                          </Button>
                        ) : null}
                      </Stack>
                    </Paper>
                  </Grid2>
                );
              })}
            </Grid2>
          ) : null}
        </Stack>
      </Paper>

      {portal.tasks.length === 0 ? (
        <Alert severity="info">{t("employeePortal.empty")}</Alert>
      ) : (
        <Grid2 container spacing={2}>
          {portal.tasks.map((task) => {
            const nextStatus = resolveNextTaskStatus(task.status);
            const isPending = pendingTaskId === task.task_id;
            return (
              <Grid2 key={task.task_id} size={{ xs: 12, md: 6 }}>
                <Paper sx={{ p: 3, height: "100%" }}>
                  <Stack spacing={2} sx={{ height: "100%" }}>
                    <Stack
                      direction={{ xs: "column", sm: "row" }}
                      spacing={1}
                      justifyContent="space-between"
                    >
                      <Stack spacing={0.5}>
                        <Typography variant="h6">{task.title}</Typography>
                        <Typography variant="body2" color="text.secondary">
                          {task.description || t("employeePortal.noDescription")}
                        </Typography>
                      </Stack>
                      <Chip
                        label={t(`employeePortal.taskStatus.${task.status}`)}
                        color={resolveTaskChipColor(task.status)}
                      />
                    </Stack>

                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                      <Chip
                        size="small"
                        label={
                          task.is_required
                            ? t("employeePortal.required")
                            : t("employeePortal.optional")
                        }
                        variant="outlined"
                      />
                      <Chip
                        size="small"
                        label={t("employeePortal.summary.assignment", {
                          value: task.assigned_role
                            ? t(`adminStaff.roles.${task.assigned_role}`)
                            : t("employeePortal.notAssigned"),
                        })}
                        variant="outlined"
                      />
                      <Chip
                        size="small"
                        label={t("employeePortal.summary.dueAt", {
                          value: formatDateTimeValue(task.due_at, noValue),
                        })}
                        variant="outlined"
                      />
                    </Stack>

                    <Typography variant="body2" color="text.secondary">
                      {t("employeePortal.summary.lastUpdated", {
                        value: formatDateTimeValue(task.updated_at, noValue),
                      })}
                    </Typography>

                    <Stack direction="row" spacing={1} sx={{ mt: "auto" }}>
                      {task.can_update ? (
                        <Button
                          variant="contained"
                          disabled={isPending}
                          onClick={() => {
                            updateTaskMutation.mutate({
                              taskId: task.task_id,
                              status: nextStatus,
                            });
                          }}
                        >
                          {isPending
                            ? t("employeePortal.actions.saving")
                            : t(`employeePortal.actions.${nextStatus}`)}
                        </Button>
                      ) : (
                        <Chip label={t("employeePortal.staffManaged")} color="default" />
                      )}
                    </Stack>
                  </Stack>
                </Paper>
              </Grid2>
            );
          })}
        </Grid2>
      )}
    </Stack>
  );
}

function resolveEmployeePortalError(
  error: unknown,
  t: (key: string) => string,
): string {
  if (error instanceof ApiError) {
    if (
      error.detail === "employee_profile_not_found"
      || error.detail === "employee_profile_identity_conflict"
      || error.detail === "employee_onboarding_not_found"
      || error.detail === "onboarding_task_not_found"
      || error.detail === "onboarding_task_not_actionable_by_employee"
      || error.detail === "employee_avatar_not_found"
      || error.detail === "employee_avatar_empty"
      || error.detail === "employee_avatar_invalid_mime_type"
      || error.detail === "employee_avatar_too_large"
    ) {
      return t(`employeePortal.errors.${error.detail}`);
    }
    if (error.status === 403) {
      return t("employeePortal.errors.http_403");
    }
    if (error.status === 404) {
      return t("employeePortal.errors.http_404");
    }
    if (error.status === 409) {
      return t("employeePortal.errors.http_409");
    }
    if (error.status === 422) {
      return t("employeePortal.errors.http_422");
    }
  }
  return t("employeePortal.errors.generic");
}

type DirectoryAvatarProps = {
  accessToken: string;
  profile: EmployeeDirectoryItem;
};

function DirectoryAvatar({ accessToken, profile }: DirectoryAvatarProps) {
  const avatarQuery = useQuery({
    queryKey: [
      "employee-directory-avatar",
      accessToken,
      profile.employee_id,
      profile.avatar_updated_at,
    ],
    queryFn: () => getEmployeeAvatarBlob(accessToken, profile.employee_id),
    enabled: Boolean(profile.avatar_url),
    retry: false,
  });

  const objectUrl = useMemo(
    () => (avatarQuery.data ? URL.createObjectURL(avatarQuery.data) : null),
    [avatarQuery.data],
  );

  useEffect(
    () => () => {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    },
    [objectUrl],
  );

  return (
    <Avatar src={objectUrl || undefined} alt={profile.full_name} sx={{ width: 40, height: 40 }}>
      {buildInitials(profile.full_name)}
    </Avatar>
  );
}

function resolveNextTaskStatus(status: EmployeeOnboardingTaskStatus): EmployeeOnboardingTaskStatus {
  if (status === "pending") {
    return "in_progress";
  }
  if (status === "in_progress") {
    return "completed";
  }
  return "pending";
}

function resolveTaskChipColor(
  status: EmployeeOnboardingTaskStatus,
): "default" | "warning" | "success" {
  if (status === "completed") {
    return "success";
  }
  if (status === "in_progress") {
    return "warning";
  }
  return "default";
}

function formatDateValue(value: string | null, fallback: string): string {
  if (!value) {
    return fallback;
  }
  return new Date(`${value}T00:00:00Z`).toLocaleDateString();
}

function formatDateTimeValue(value: string | null, fallback: string): string {
  if (!value) {
    return fallback;
  }
  return new Date(value).toLocaleString();
}

function buildInitials(value: string): string {
  const parts = value
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (parts.length === 0) {
    return "?";
  }
  return parts
    .slice(0, 2)
    .map((item) => item[0]?.toUpperCase() ?? "")
    .join("");
}
