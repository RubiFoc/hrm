import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Chip,
  CircularProgress,
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
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import {
  ApiError,
  confirmRaiseRequest,
  createRaiseRequest,
  getManagerWorkspaceCandidateSnapshot,
  getManagerWorkspaceOverview,
  listRaiseRequests,
  type CompensationTableRowResponse,
  type ManagerWorkspaceCandidateSnapshotResponse,
  type ManagerWorkspaceOverviewResponse,
} from "../api";
import { readAuthSession } from "../app/auth/session";
import { useSentryRouteTags } from "../app/observability/sentry";
import { CompensationTablePanel } from "../components/CompensationTablePanel";
import { NotificationsPanel } from "../components/NotificationsPanel";
import { OnboardingDashboardPanel } from "../components/OnboardingDashboardPanel";
import { PageHero } from "../components/PageHero";
import { resolveCompensationApiError } from "../pages/compensation/compensationErrors";

const EMPTY_OVERVIEW: ManagerWorkspaceOverviewResponse = {
  summary: {
    vacancy_count: 0,
    open_vacancy_count: 0,
    candidate_count: 0,
    active_interview_count: 0,
    upcoming_interview_count: 0,
  },
  items: [],
};

type FeedbackState = {
  type: "success" | "error";
  message: string;
};

/**
 * Manager-facing workspace that combines hiring visibility with embedded onboarding progress.
 */
export function ManagerWorkspacePage() {
  const { t } = useTranslation();
  useSentryRouteTags("/manager");
  const queryClient = useQueryClient();
  const session = readAuthSession();
  const accessToken = session.accessToken;
  const [selectedVacancyId, setSelectedVacancyId] = useState<string | null>(null);
  const [compensationRows, setCompensationRows] = useState<CompensationTableRowResponse[]>([]);
  const [raiseEmployeeId, setRaiseEmployeeId] = useState("");
  const [raiseSalary, setRaiseSalary] = useState("");
  const [raiseEffectiveDate, setRaiseEffectiveDate] = useState("");
  const [raiseFeedback, setRaiseFeedback] = useState<FeedbackState | null>(null);

  const employeeOptions = useMemo(
    () =>
      compensationRows.map((row) => ({
        id: row.employee_id,
        label: `${row.full_name} (${formatShortUuid(row.employee_id)})`,
      })),
    [compensationRows],
  );

  const overviewQuery = useQuery({
    queryKey: ["manager-workspace-overview", accessToken],
    queryFn: () => getManagerWorkspaceOverview(accessToken!),
    enabled: Boolean(accessToken),
    retry: false,
  });

  const overview = overviewQuery.data ?? EMPTY_OVERVIEW;
  const vacancyItems = overview.items;

  useEffect(() => {
    if (vacancyItems.length === 0) {
      if (selectedVacancyId !== null) {
        setSelectedVacancyId(null);
      }
      return;
    }
    if (!selectedVacancyId || !vacancyItems.some((item) => item.vacancy_id === selectedVacancyId)) {
      setSelectedVacancyId(vacancyItems[0].vacancy_id);
    }
  }, [selectedVacancyId, vacancyItems]);

  const snapshotQuery = useQuery({
    queryKey: ["manager-workspace-snapshot", accessToken, selectedVacancyId],
    queryFn: () => getManagerWorkspaceCandidateSnapshot(accessToken!, selectedVacancyId!),
    enabled: Boolean(accessToken && selectedVacancyId),
    retry: false,
  });

  const raiseQuery = useQuery({
    queryKey: ["compensation-raises", accessToken],
    queryFn: () =>
      listRaiseRequests(accessToken!, {
        limit: 50,
        offset: 0,
      }),
    enabled: Boolean(accessToken),
    retry: false,
  });

  const createRaiseMutation = useMutation({
    mutationFn: ({
      employeeId,
      proposedBaseSalary,
      effectiveDate,
    }: {
      employeeId: string;
      proposedBaseSalary: number;
      effectiveDate: string;
    }) =>
      createRaiseRequest(accessToken!, {
        employee_id: employeeId,
        proposed_base_salary: proposedBaseSalary,
        effective_date: effectiveDate,
      }),
    onSuccess: () => {
      setRaiseFeedback({ type: "success", message: t("compensationRaise.manager.createSuccess") });
      setRaiseSalary("");
      setRaiseEffectiveDate("");
      void queryClient.invalidateQueries({ queryKey: ["compensation-raises", accessToken] });
      void queryClient.invalidateQueries({ queryKey: ["compensation-table", accessToken] });
    },
    onError: (error: unknown) => {
      setRaiseFeedback({ type: "error", message: resolveCompensationApiError(error, t) });
    },
  });

  const confirmRaiseMutation = useMutation({
    mutationFn: (requestId: string) => confirmRaiseRequest(accessToken!, requestId),
    onSuccess: () => {
      setRaiseFeedback({ type: "success", message: t("compensationRaise.manager.confirmSuccess") });
      void queryClient.invalidateQueries({ queryKey: ["compensation-raises", accessToken] });
      void queryClient.invalidateQueries({ queryKey: ["compensation-table", accessToken] });
    },
    onError: (error: unknown) => {
      setRaiseFeedback({ type: "error", message: resolveCompensationApiError(error, t) });
    },
  });

  const raiseItems = raiseQuery.data?.items ?? [];
  const employeeLookup = useMemo(
    () =>
      new Map(
        compensationRows.map((row) => [
          row.employee_id,
          row.full_name,
        ]),
      ),
    [compensationRows],
  );

  const handleCreateRaise = () => {
    setRaiseFeedback(null);
    if (!raiseEmployeeId) {
      setRaiseFeedback({ type: "error", message: t("compensationRaise.manager.errors.employeeRequired") });
      return;
    }
    if (!raiseEffectiveDate) {
      setRaiseFeedback({ type: "error", message: t("compensationRaise.manager.errors.effectiveDateRequired") });
      return;
    }
    const proposedSalary = Number.parseFloat(raiseSalary);
    if (!Number.isFinite(proposedSalary) || proposedSalary <= 0) {
      setRaiseFeedback({ type: "error", message: t("compensationRaise.manager.errors.salaryRequired") });
      return;
    }
    createRaiseMutation.mutate({
      employeeId: raiseEmployeeId,
      proposedBaseSalary: proposedSalary,
      effectiveDate: raiseEffectiveDate,
    });
  };

  if (!accessToken) {
    return <Alert severity="warning">{t("managerDashboard.authRequired")}</Alert>;
  }

  return (
    <Stack spacing={3}>
      <PageHero
        title={t("managerWorkspace")}
        description={t("managerDashboard.subtitle")}
        imageSrc="/images/company-hero.jpg"
        imageAlt={t("managerWorkspace")}
      />

      <NotificationsPanel accessToken={accessToken} workspace="manager" />

      <Stack direction={{ xs: "column", md: "row" }} spacing={1} flexWrap="wrap" useFlexGap>
        <Chip
          label={t("managerDashboard.summary.vacancies", {
            value: overview.summary.vacancy_count,
          })}
          color="primary"
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.summary.openVacancies", {
            value: overview.summary.open_vacancy_count,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.summary.candidates", {
            value: overview.summary.candidate_count,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.summary.activeInterviews", {
            value: overview.summary.active_interview_count,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.summary.upcomingInterviews", {
            value: overview.summary.upcoming_interview_count,
          })}
          variant="outlined"
        />
      </Stack>

      {overviewQuery.isLoading ? (
        <Stack spacing={2} alignItems="center" sx={{ py: 4 }}>
          <CircularProgress size={28} />
          <Typography variant="body2">{t("managerDashboard.loading")}</Typography>
        </Stack>
      ) : null}

      {overviewQuery.isError ? (
        <Alert severity="error">{resolveManagerWorkspaceError(overviewQuery.error, t)}</Alert>
      ) : null}

      {overviewQuery.isLoading || overviewQuery.isError ? null : (
        <Grid2 container spacing={2}>
          <Grid2 size={{ xs: 12, lg: 5 }}>
            <Paper sx={{ overflowX: "auto" }}>
              <Stack spacing={1} sx={{ p: 3, pb: vacancyItems.length === 0 ? 3 : 1 }}>
                <Typography variant="h6">{t("managerDashboard.vacancies.title")}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {t("managerDashboard.vacancies.subtitle")}
                </Typography>
              </Stack>
              {vacancyItems.length === 0 ? (
                <Alert severity="info" sx={{ borderRadius: 0 }}>
                  {t("managerDashboard.empty")}
                </Alert>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>{t("managerDashboard.vacancies.table.title")}</TableCell>
                      <TableCell>{t("managerDashboard.vacancies.table.counts")}</TableCell>
                      <TableCell>{t("managerDashboard.vacancies.table.activity")}</TableCell>
                      <TableCell align="right">
                        {t("managerDashboard.vacancies.table.actions")}
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {vacancyItems.map((vacancy) => (
                      <TableRow
                        key={vacancy.vacancy_id}
                        hover
                        selected={vacancy.vacancy_id === selectedVacancyId}
                      >
                        <TableCell>
                          <Stack spacing={0.5}>
                            <Typography variant="body2" fontWeight={600}>
                              {vacancy.title}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {t("managerDashboard.vacancies.meta", {
                                department: vacancy.department,
                                status: vacancy.status,
                              })}
                            </Typography>
                          </Stack>
                        </TableCell>
                        <TableCell>
                          <Stack spacing={0.5}>
                            <Typography variant="body2">
                              {t("managerDashboard.vacancies.counts.candidates", {
                                value: vacancy.candidate_count,
                              })}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {t("managerDashboard.vacancies.counts.interviews", {
                                value: vacancy.active_interview_count,
                              })}
                            </Typography>
                          </Stack>
                        </TableCell>
                        <TableCell>{formatDateTimeValue(vacancy.latest_activity_at)}</TableCell>
                        <TableCell align="right">
                          <Button size="small" onClick={() => setSelectedVacancyId(vacancy.vacancy_id)}>
                            {t("managerDashboard.vacancies.actions.view")}
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </Paper>
          </Grid2>

          <Grid2 size={{ xs: 12, lg: 7 }}>
            <Paper sx={{ p: 3, minHeight: 320 }}>
              {selectedVacancyId === null ? (
                <Alert severity="info">{t("managerDashboard.snapshot.selectVacancy")}</Alert>
              ) : snapshotQuery.isLoading ? (
                <Stack spacing={2} alignItems="center" sx={{ py: 4 }}>
                  <CircularProgress size={24} />
                  <Typography variant="body2">{t("managerDashboard.snapshot.loading")}</Typography>
                </Stack>
              ) : snapshotQuery.isError ? (
                <Alert severity="error">{resolveManagerWorkspaceError(snapshotQuery.error, t)}</Alert>
              ) : snapshotQuery.data ? (
                <CandidateSnapshot snapshot={snapshotQuery.data} />
              ) : null}
            </Paper>
          </Grid2>
        </Grid2>
      )}

      <Grid2 container spacing={2}>
        <Grid2 size={{ xs: 12, lg: 5 }}>
          <Paper sx={{ p: 2 }}>
            <Stack spacing={2}>
              <Stack spacing={0.5}>
                <Typography variant="h6">{t("compensationRaise.manager.title")}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {t("compensationRaise.manager.subtitle")}
                </Typography>
              </Stack>

              {raiseFeedback ? <Alert severity={raiseFeedback.type}>{raiseFeedback.message}</Alert> : null}

              {employeeOptions.length === 0 ? (
                <Alert severity="info">{t("compensationRaise.manager.emptyEmployees")}</Alert>
              ) : (
                <>
                  <TextField
                    select
                    label={t("compensationRaise.fields.employee")}
                    value={raiseEmployeeId}
                    onChange={(event) => setRaiseEmployeeId(event.target.value)}
                    fullWidth
                  >
                    {employeeOptions.map((option) => (
                      <MenuItem key={option.id} value={option.id}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </TextField>
                  <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
                    <TextField
                      label={t("compensationRaise.fields.proposedSalary")}
                      type="number"
                      value={raiseSalary}
                      onChange={(event) => setRaiseSalary(event.target.value)}
                      fullWidth
                    />
                    <TextField
                      label={t("compensationRaise.fields.effectiveDate")}
                      type="date"
                      value={raiseEffectiveDate}
                      onChange={(event) => setRaiseEffectiveDate(event.target.value)}
                      fullWidth
                      InputLabelProps={{ shrink: true }}
                    />
                  </Stack>
                  <Button
                    variant="contained"
                    onClick={handleCreateRaise}
                    disabled={createRaiseMutation.isPending}
                  >
                    {createRaiseMutation.isPending
                      ? t("compensationRaise.manager.createPending")
                      : t("compensationRaise.manager.createAction")}
                  </Button>
                </>
              )}
            </Stack>
          </Paper>
        </Grid2>

        <Grid2 size={{ xs: 12, lg: 7 }}>
          <Paper sx={{ p: 2, overflowX: "auto" }}>
            <Stack spacing={1.5}>
              <Typography variant="h6">{t("compensationRaise.list.title")}</Typography>
              <Typography variant="body2" color="text.secondary">
                {t("compensationRaise.list.subtitle")}
              </Typography>
            </Stack>
            {raiseQuery.isLoading ? (
              <Stack spacing={2} alignItems="center" sx={{ py: 4 }}>
                <CircularProgress size={24} />
                <Typography variant="body2">{t("compensationRaise.list.loading")}</Typography>
              </Stack>
            ) : raiseQuery.isError ? (
              <Alert severity="error" sx={{ borderRadius: 0, mt: 2 }}>
                {resolveCompensationApiError(raiseQuery.error, t)}
              </Alert>
            ) : raiseItems.length === 0 ? (
              <Alert severity="info" sx={{ borderRadius: 0, mt: 2 }}>
                {t("compensationRaise.list.empty")}
              </Alert>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{t("compensationRaise.list.columns.employee")}</TableCell>
                    <TableCell>{t("compensationRaise.list.columns.salary")}</TableCell>
                    <TableCell>{t("compensationRaise.list.columns.effectiveDate")}</TableCell>
                    <TableCell>{t("compensationRaise.list.columns.status")}</TableCell>
                    <TableCell>{t("compensationRaise.list.columns.confirmations")}</TableCell>
                    <TableCell align="right">{t("compensationRaise.list.columns.actions")}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {raiseItems.map((item) => (
                    <TableRow key={item.request_id}>
                      <TableCell>
                        <Stack spacing={0.5}>
                          <Typography variant="body2" fontWeight={600}>
                            {employeeLookup.get(item.employee_id) ?? formatShortUuid(item.employee_id)}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {formatShortUuid(item.employee_id)}
                          </Typography>
                        </Stack>
                      </TableCell>
                      <TableCell>{formatMoneyValue(item.proposed_base_salary, item.currency, t)}</TableCell>
                      <TableCell>{formatDateValue(item.effective_date)}</TableCell>
                      <TableCell>{t(`compensationRaise.status.${item.status}`)}</TableCell>
                      <TableCell>
                        {t("compensationRaise.confirmations", {
                          count: item.confirmation_count,
                          quorum: item.confirmation_quorum,
                        })}
                      </TableCell>
                      <TableCell align="right">
                        {item.status === "pending_confirmations" ? (
                          <Button
                            size="small"
                            onClick={() => confirmRaiseMutation.mutate(item.request_id)}
                            disabled={
                              confirmRaiseMutation.isPending
                              && confirmRaiseMutation.variables === item.request_id
                            }
                          >
                            {confirmRaiseMutation.isPending
                            && confirmRaiseMutation.variables === item.request_id
                              ? t("compensationRaise.list.confirmPending")
                              : t("compensationRaise.list.confirmAction")}
                          </Button>
                        ) : (
                          <Typography variant="caption" color="text.secondary">
                            {t("compensationRaise.list.noActions")}
                          </Typography>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Paper>
        </Grid2>
      </Grid2>

      <CompensationTablePanel
        accessToken={accessToken}
        title={t("compensationTable.managerTitle")}
        subtitle={t("compensationTable.managerSubtitle")}
        showBonusForm={false}
        onRowsLoaded={setCompensationRows}
      />

      <OnboardingDashboardPanel mode="embedded" />
    </Stack>
  );
}

type CandidateSnapshotProps = {
  snapshot: ManagerWorkspaceCandidateSnapshotResponse;
};

function CandidateSnapshot({ snapshot }: CandidateSnapshotProps) {
  const { t } = useTranslation();

  return (
    <Stack spacing={2}>
      <Stack spacing={0.5}>
        <Typography variant="h6">{snapshot.vacancy.title}</Typography>
        <Typography variant="body2" color="text.secondary">
          {t("managerDashboard.snapshot.subtitle", {
            department: snapshot.vacancy.department,
            status: snapshot.vacancy.status,
          })}
        </Typography>
      </Stack>

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip
          label={t("managerDashboard.snapshot.summary.candidates", {
            value: snapshot.summary.candidate_count,
          })}
          color="primary"
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.snapshot.summary.activeInterviews", {
            value: snapshot.summary.active_interview_count,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.snapshot.summary.upcomingInterviews", {
            value: snapshot.summary.upcoming_interview_count,
          })}
          variant="outlined"
        />
      </Stack>

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip
          label={t("managerDashboard.snapshot.stageCounts.applied", {
            value: snapshot.summary.stage_counts.applied,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.snapshot.stageCounts.screening", {
            value: snapshot.summary.stage_counts.screening,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.snapshot.stageCounts.shortlist", {
            value: snapshot.summary.stage_counts.shortlist,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.snapshot.stageCounts.interview", {
            value: snapshot.summary.stage_counts.interview,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.snapshot.stageCounts.offer", {
            value: snapshot.summary.stage_counts.offer,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.snapshot.stageCounts.hired", {
            value: snapshot.summary.stage_counts.hired,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.snapshot.stageCounts.rejected", {
            value: snapshot.summary.stage_counts.rejected,
          })}
          variant="outlined"
        />
      </Stack>

      {snapshot.items.length === 0 ? (
        <Alert severity="info">{t("managerDashboard.snapshot.empty")}</Alert>
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t("managerDashboard.snapshot.table.candidate")}</TableCell>
              <TableCell>{t("managerDashboard.snapshot.table.stage")}</TableCell>
              <TableCell>{t("managerDashboard.snapshot.table.interview")}</TableCell>
              <TableCell>{t("managerDashboard.snapshot.table.offer")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {snapshot.items.map((item) => (
              <TableRow key={item.candidate_id}>
                <TableCell>
                  <Stack spacing={0.5}>
                    <Typography variant="body2" fontWeight={600}>
                      {t("managerDashboard.snapshot.candidateId", {
                        value: formatShortUuid(item.candidate_id),
                      })}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {item.candidate_id}
                    </Typography>
                  </Stack>
                </TableCell>
                <TableCell>
                  <Stack spacing={0.5}>
                    <Chip
                      size="small"
                      label={t(`hrDashboard.stages.${item.stage}`)}
                      color={resolveStageChipColor(item.stage)}
                    />
                    <Typography variant="caption" color="text.secondary">
                      {formatDateTimeValue(item.stage_updated_at)}
                    </Typography>
                  </Stack>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {formatInterviewSummary(item, t)}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {formatOfferSummary(item, t)}
                  </Typography>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Stack>
  );
}

function resolveManagerWorkspaceError(
  error: unknown,
  t: ReturnType<typeof useTranslation>["t"],
) {
  if (error instanceof ApiError) {
    if (error.detail === "manager_workspace_vacancy_not_found") {
      return t("managerDashboard.errors.vacancyNotFound");
    }
    return t(`managerDashboard.errors.${error.detail}`, {
      defaultValue: t(`managerDashboard.errors.http_${error.status}`, {
        defaultValue: t("managerDashboard.errors.generic"),
      }),
    });
  }
  return t("managerDashboard.errors.generic");
}

function formatMoneyValue(
  value: number | null | undefined,
  currency: string,
  t: ReturnType<typeof useTranslation>["t"],
) {
  if (value === null || value === undefined) {
    return t("compensationTable.notAvailable");
  }
  return `${value.toFixed(2)} ${currency}`;
}

function resolveStageChipColor(stage: ManagerWorkspaceCandidateSnapshotResponse["items"][number]["stage"]) {
  if (stage === "hired") {
    return "success" as const;
  }
  if (stage === "offer" || stage === "interview") {
    return "warning" as const;
  }
  return "default" as const;
}

function formatInterviewSummary(
  item: ManagerWorkspaceCandidateSnapshotResponse["items"][number],
  t: ReturnType<typeof useTranslation>["t"],
) {
  if (!item.interview_status || !item.interview_scheduled_start_at) {
    return t("managerDashboard.snapshot.noInterview");
  }
  return t("managerDashboard.snapshot.interviewValue", {
    status: t(`candidateInterview.status.${item.interview_status}`),
    value: formatDateTimeValue(item.interview_scheduled_start_at),
  });
}

function formatOfferSummary(
  item: ManagerWorkspaceCandidateSnapshotResponse["items"][number],
  t: ReturnType<typeof useTranslation>["t"],
) {
  if (!item.offer_status) {
    return t("managerDashboard.snapshot.noOffer");
  }
  return t("managerDashboard.snapshot.offerValue", {
    value: t(`hrDashboard.offers.status.${item.offer_status}`),
  });
}

function formatDateTimeValue(value: string | null) {
  if (!value) {
    return "n/a";
  }
  return new Date(value).toLocaleString();
}

function formatDateValue(value: string | null) {
  if (!value) {
    return "n/a";
  }
  return new Date(value).toLocaleDateString();
}

function formatShortUuid(value: string) {
  return value.slice(0, 8);
}
