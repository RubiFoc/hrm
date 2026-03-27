import { useState } from "react";
import {
  Alert,
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
import { Link as RouterLink, useInRouterContext } from "react-router-dom";

import {
  ApiError,
  getMyEmployeeOnboardingPortal,
  updateMyEmployeeOnboardingTask,
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

/**
 * Employee self-service onboarding workspace.
 */
export function EmployeeOnboardingPage() {
  const { t } = useTranslation();
  useSentryRouteTags("/employee");
  const queryClient = useQueryClient();
  const session = readAuthSession();
  const accessToken = session.accessToken;
  const inRouter = useInRouterContext();
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const [pendingTaskId, setPendingTaskId] = useState<string | null>(null);
  const queryKey = ["employee-onboarding-portal", accessToken];

  const portalQuery = useQuery({
    queryKey,
    queryFn: () => getMyEmployeeOnboardingPortal(accessToken!),
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

  return (
    <Stack spacing={3}>
      <PageHero
        title={t("employeePortal.title")}
        description={t("employeePortal.subtitle")}
        imageSrc="/images/candidate-portal.jpg"
        imageAlt={t("employeePortal.title")}
      />

      <Paper sx={{ p: 2 }}>
        <Stack spacing={1.5} direction={{ xs: "column", md: "row" }} alignItems="flex-start">
          <Stack spacing={0.5}>
            <Typography variant="h6">{t("referrals.employeeCalloutTitle")}</Typography>
            <Typography variant="body2" color="text.secondary">
              {t("referrals.employeeCalloutSubtitle")}
            </Typography>
          </Stack>
          <Button
            component={inRouter ? RouterLink : "button"}
            to={inRouter ? "/employee/referrals" : undefined}
            variant="contained"
            sx={{ ml: { md: "auto" } }}
          >
            {t("referrals.employeeCalloutCta")}
          </Button>
        </Stack>
      </Paper>

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
  }
  return t("employeePortal.errors.generic");
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
