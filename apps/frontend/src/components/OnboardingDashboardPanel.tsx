import { useDeferredValue, useEffect, useState } from "react";
import {
  Alert,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  FormControlLabel,
  Grid2,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import {
  ApiError,
  getOnboardingDashboardRun,
  listOnboardingDashboardRuns,
  type OnboardingDashboardDetailResponse,
  type OnboardingDashboardListResponse,
  type OnboardingDashboardTaskStatus,
} from "../api";
import { readAuthSession } from "../app/auth/session";

type OnboardingDashboardMode = "embedded" | "standalone";

type OnboardingDashboardPanelProps = {
  mode?: OnboardingDashboardMode;
};

const EMPTY_SUMMARY = {
  run_count: 0,
  total_tasks: 0,
  pending_tasks: 0,
  in_progress_tasks: 0,
  completed_tasks: 0,
  overdue_tasks: 0,
} satisfies OnboardingDashboardListResponse["summary"];
const EMPTY_ITEMS: OnboardingDashboardListResponse["items"] = [];

/**
 * Staff-facing onboarding progress dashboard used by HR and manager workspaces.
 */
export function OnboardingDashboardPanel({
  mode = "embedded",
}: OnboardingDashboardPanelProps) {
  const { t } = useTranslation();
  const session = readAuthSession();
  const accessToken = session.accessToken;
  const role = session.role;
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search);
  const [taskStatus, setTaskStatus] = useState<OnboardingDashboardTaskStatus | "all">("all");
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [selectedOnboardingId, setSelectedOnboardingId] = useState<string | null>(null);

  const dashboardQuery = useQuery({
    queryKey: ["onboarding-dashboard", accessToken, deferredSearch, taskStatus, overdueOnly],
    queryFn: () =>
      listOnboardingDashboardRuns(accessToken!, {
        search: deferredSearch || undefined,
        taskStatus: taskStatus === "all" ? undefined : taskStatus,
        overdueOnly,
        limit: 20,
        offset: 0,
      }),
    enabled: Boolean(accessToken),
    retry: false,
  });

  const items = dashboardQuery.data?.items ?? EMPTY_ITEMS;
  const summary = dashboardQuery.data?.summary ?? EMPTY_SUMMARY;

  useEffect(() => {
    if (items.length === 0) {
      if (selectedOnboardingId !== null) {
        setSelectedOnboardingId(null);
      }
      return;
    }
    if (!selectedOnboardingId || !items.some((item) => item.onboarding_id === selectedOnboardingId)) {
      setSelectedOnboardingId(items[0].onboarding_id);
    }
  }, [items, selectedOnboardingId]);

  const detailQuery = useQuery({
    queryKey: ["onboarding-dashboard-detail", accessToken, selectedOnboardingId],
    queryFn: () => getOnboardingDashboardRun(accessToken!, selectedOnboardingId!),
    enabled: Boolean(accessToken && selectedOnboardingId),
    retry: false,
  });

  if (!accessToken) {
    return (
      <Alert severity="warning">{t("onboardingDashboard.authRequired")}</Alert>
    );
  }

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant={mode === "standalone" ? "h4" : "h5"}>
          {t("onboardingDashboard.title")}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {role === "manager"
            ? t("onboardingDashboard.managerSubtitle")
            : t("onboardingDashboard.subtitle")}
        </Typography>
      </Stack>

      <Stack direction={{ xs: "column", md: "row" }} spacing={1} flexWrap="wrap" useFlexGap>
        <Chip
          label={t("onboardingDashboard.summary.runs", { value: summary.run_count })}
          color="primary"
          variant="outlined"
        />
        <Chip
          label={t("onboardingDashboard.summary.pendingTasks", { value: summary.pending_tasks })}
          variant="outlined"
        />
        <Chip
          label={t("onboardingDashboard.summary.inProgressTasks", {
            value: summary.in_progress_tasks,
          })}
          variant="outlined"
        />
        <Chip
          label={t("onboardingDashboard.summary.completedTasks", {
            value: summary.completed_tasks,
          })}
          variant="outlined"
        />
        <Chip
          label={t("onboardingDashboard.summary.overdueTasks", { value: summary.overdue_tasks })}
          color={summary.overdue_tasks > 0 ? "warning" : "default"}
          variant="outlined"
        />
      </Stack>

      <Paper sx={{ p: 3 }}>
        <Grid2 container spacing={2}>
          <Grid2 size={{ xs: 12, md: 6 }}>
            <TextField
              fullWidth
              label={t("onboardingDashboard.filters.search")}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </Grid2>
          <Grid2 size={{ xs: 12, md: 3 }}>
            <TextField
              fullWidth
              select
              label={t("onboardingDashboard.filters.taskStatus")}
              value={taskStatus}
              onChange={(event) =>
                setTaskStatus(event.target.value as OnboardingDashboardTaskStatus | "all")
              }
            >
              <MenuItem value="all">{t("onboardingDashboard.filters.allStatuses")}</MenuItem>
              <MenuItem value="pending">{t("onboardingDashboard.taskStatus.pending")}</MenuItem>
              <MenuItem value="in_progress">
                {t("onboardingDashboard.taskStatus.in_progress")}
              </MenuItem>
              <MenuItem value="completed">{t("onboardingDashboard.taskStatus.completed")}</MenuItem>
            </TextField>
          </Grid2>
          <Grid2 size={{ xs: 12, md: 3 }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={overdueOnly}
                  onChange={(event) => setOverdueOnly(event.target.checked)}
                />
              }
              label={t("onboardingDashboard.filters.overdueOnly")}
            />
          </Grid2>
        </Grid2>
      </Paper>

      {dashboardQuery.isLoading ? (
        <Stack spacing={2} alignItems="center" sx={{ py: 4 }}>
          <CircularProgress size={28} />
          <Typography variant="body2">{t("onboardingDashboard.loading")}</Typography>
        </Stack>
      ) : null}

      {dashboardQuery.isError ? (
        <Alert severity="error">{resolveOnboardingDashboardError(dashboardQuery.error, t)}</Alert>
      ) : null}

      {dashboardQuery.isLoading || dashboardQuery.isError ? null : (
        <Grid2 container spacing={2}>
          <Grid2 size={{ xs: 12, lg: 7 }}>
            <Paper sx={{ overflowX: "auto" }}>
              {items.length === 0 ? (
                <Alert severity="info" sx={{ borderRadius: 0 }}>
                  {t("onboardingDashboard.empty")}
                </Alert>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>{t("onboardingDashboard.table.employee")}</TableCell>
                      <TableCell>{t("onboardingDashboard.table.title")}</TableCell>
                      <TableCell>{t("onboardingDashboard.table.progress")}</TableCell>
                      <TableCell>{t("onboardingDashboard.table.tasks")}</TableCell>
                      <TableCell>{t("onboardingDashboard.table.overdue")}</TableCell>
                      <TableCell align="right">{t("onboardingDashboard.table.action")}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {items.map((item) => (
                      <TableRow
                        key={item.onboarding_id}
                        selected={item.onboarding_id === selectedOnboardingId}
                        hover
                      >
                        <TableCell>
                          <Stack spacing={0.5}>
                            <Typography variant="body2" fontWeight={600}>
                              {item.first_name} {item.last_name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {item.email}
                            </Typography>
                          </Stack>
                        </TableCell>
                        <TableCell>{item.current_title || t("onboardingDashboard.noValue")}</TableCell>
                        <TableCell>{t("onboardingDashboard.progressValue", {
                          value: item.progress_percent,
                        })}</TableCell>
                        <TableCell>{t("onboardingDashboard.taskBreakdown", {
                          completed: item.completed_tasks,
                          total: item.total_tasks,
                        })}</TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={String(item.overdue_tasks)}
                            color={item.overdue_tasks > 0 ? "warning" : "default"}
                          />
                        </TableCell>
                        <TableCell align="right">
                          <Button
                            size="small"
                            onClick={() => setSelectedOnboardingId(item.onboarding_id)}
                          >
                            {t("onboardingDashboard.actions.view")}
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </Paper>
          </Grid2>

          <Grid2 size={{ xs: 12, lg: 5 }}>
            <Paper sx={{ p: 3, minHeight: 320 }}>
              {selectedOnboardingId === null ? (
                <Alert severity="info">{t("onboardingDashboard.selectRun")}</Alert>
              ) : detailQuery.isLoading ? (
                <Stack spacing={2} alignItems="center" sx={{ py: 4 }}>
                  <CircularProgress size={24} />
                  <Typography variant="body2">{t("onboardingDashboard.detailLoading")}</Typography>
                </Stack>
              ) : detailQuery.isError ? (
                <Alert severity="error">{resolveOnboardingDashboardError(detailQuery.error, t)}</Alert>
              ) : detailQuery.data ? (
                <DashboardDetail detail={detailQuery.data} />
              ) : null}
            </Paper>
          </Grid2>
        </Grid2>
      )}
    </Stack>
  );
}

type DashboardDetailProps = {
  detail: OnboardingDashboardDetailResponse;
};

function DashboardDetail({ detail }: DashboardDetailProps) {
  const { t } = useTranslation();

  return (
    <Stack spacing={2}>
      <Stack spacing={0.5}>
        <Typography variant="h6">
          {detail.first_name} {detail.last_name}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {detail.email}
        </Typography>
      </Stack>

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip
          label={t("onboardingDashboard.summary.currentTitle", {
            value: detail.current_title || t("onboardingDashboard.noValue"),
          })}
          variant="outlined"
        />
        <Chip
          label={t("onboardingDashboard.summary.location", {
            value: detail.location || t("onboardingDashboard.noValue"),
          })}
          variant="outlined"
        />
        <Chip
          label={t("onboardingDashboard.summary.startDate", {
            value: formatDateValue(detail.start_date),
          })}
          variant="outlined"
        />
        <Chip
          label={t("onboardingDashboard.summary.runStatus", {
            value: t(`onboardingDashboard.runStatus.${detail.onboarding_status}`),
          })}
          color="primary"
          variant="outlined"
        />
      </Stack>

      {detail.offer_terms_summary ? (
        <Typography variant="body2">{detail.offer_terms_summary}</Typography>
      ) : null}

      <Stack spacing={1}>
        <Typography variant="subtitle1">{t("onboardingDashboard.detailTasks")}</Typography>
        {detail.tasks.length === 0 ? (
          <Alert severity="info">{t("onboardingDashboard.noTasks")}</Alert>
        ) : (
          <Stack spacing={1.5}>
            {detail.tasks.map((task) => (
              <Paper key={task.task_id} variant="outlined" sx={{ p: 2 }}>
                <Stack spacing={1}>
                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    spacing={1}
                    justifyContent="space-between"
                  >
                    <Typography variant="body1" fontWeight={600}>
                      {task.title}
                    </Typography>
                    <Chip
                      size="small"
                      label={t(`onboardingDashboard.taskStatus.${task.status}`)}
                      color={resolveTaskChipColor(task.status)}
                    />
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    {task.description || t("onboardingDashboard.noDescription")}
                  </Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    <Chip
                      size="small"
                      label={
                        task.is_required
                          ? t("onboardingDashboard.required")
                          : t("onboardingDashboard.optional")
                      }
                      variant="outlined"
                    />
                    <Chip
                      size="small"
                      label={t("onboardingDashboard.summary.assignment", {
                        value: task.assigned_role
                          ? t(`adminStaff.roles.${task.assigned_role}`)
                          : t("onboardingDashboard.unassigned"),
                      })}
                      variant="outlined"
                    />
                    <Chip
                      size="small"
                      label={t("onboardingDashboard.summary.dueAt", {
                        value: formatDateTimeValue(task.due_at),
                      })}
                      color={isOverdueTask(task) ? "warning" : "default"}
                      variant="outlined"
                    />
                  </Stack>
                </Stack>
              </Paper>
            ))}
          </Stack>
        )}
      </Stack>
    </Stack>
  );
}

function resolveOnboardingDashboardError(
  error: unknown,
  t: ReturnType<typeof useTranslation>["t"],
) {
  if (error instanceof ApiError) {
    const detail = error.detail;
    if (detail === "onboarding_run_not_found") {
      return t("onboardingDashboard.errors.onboardingRunNotFound");
    }
    return t(`onboardingDashboard.errors.${detail}`, {
      defaultValue: t(`onboardingDashboard.errors.http_${error.status}`, {
        defaultValue: t("onboardingDashboard.errors.generic"),
      }),
    });
  }
  return t("onboardingDashboard.errors.generic");
}

function resolveTaskChipColor(status: OnboardingDashboardTaskStatus) {
  if (status === "completed") {
    return "success" as const;
  }
  if (status === "in_progress") {
    return "warning" as const;
  }
  return "default" as const;
}

function isOverdueTask(task: OnboardingDashboardDetailResponse["tasks"][number]) {
  if (!task.due_at || task.status === "completed") {
    return false;
  }
  return new Date(task.due_at).getTime() < Date.now();
}

function formatDateValue(value: string | null) {
  if (!value) {
    return "n/a";
  }
  return new Date(value).toLocaleDateString();
}

function formatDateTimeValue(value: string | null) {
  if (!value) {
    return "n/a";
  }
  return new Date(value).toLocaleString();
}
