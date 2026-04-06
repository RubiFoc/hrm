import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  CircularProgress,
  Grid2,
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
  approveRaiseRequest,
  downloadKpiSnapshotExport,
  listRaiseRequests,
  readKpiSnapshot,
  rejectRaiseRequest,
  type KpiSnapshotExportFormat,
  type KpiSnapshotMetric,
  type KpiSnapshotReadResponse,
} from "../api";
import { readAuthSession } from "../app/auth/session";
import { useSentryRouteTags } from "../app/observability/sentry";
import { PageHero } from "../components/PageHero";
import { resolveCompensationApiError } from "../pages/compensation/compensationErrors";

type MetricKey = KpiSnapshotMetric["metric_key"];
type SnapshotLookupResult = {
  attemptedMonths: string[];
  requestedMonth: string;
  resolvedMonth: string;
  response: KpiSnapshotReadResponse;
};
type FeedbackState = {
  type: "success" | "error";
  message: string;
};

const DEFAULT_MONTH = resolveCurrentMonthValue();
const LOOKBACK_MONTHS = 12;
const METRIC_ORDER: MetricKey[] = [
  "vacancies_created_count",
  "candidates_applied_count",
  "interviews_scheduled_count",
  "offers_sent_count",
  "offers_accepted_count",
  "hires_count",
  "onboarding_started_count",
  "onboarding_tasks_completed_count",
  "total_hr_operations_count",
  "automated_hr_operations_count",
  "automated_hr_operations_share_percent",
];

/**
 * Leader-facing KPI workspace built on stored monthly snapshots.
 */
export function LeaderWorkspacePage() {
  const { t, i18n } = useTranslation();
  useSentryRouteTags("/leader");
  const queryClient = useQueryClient();
  const session = readAuthSession();
  const accessToken = session.accessToken;
  const [monthInput, setMonthInput] = useState(DEFAULT_MONTH);
  const [requestedMonth, setRequestedMonth] = useState(DEFAULT_MONTH);
  const [isAutoLookupEnabled, setIsAutoLookupEnabled] = useState(true);
  const [autoLookupNotice, setAutoLookupNotice] = useState<{
    fromMonth: string;
    toMonth: string;
  } | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [pendingExportFormat, setPendingExportFormat] =
    useState<KpiSnapshotExportFormat | null>(null);
  const [decisionNotes, setDecisionNotes] = useState<Record<string, string>>({});
  const [decisionFeedback, setDecisionFeedback] = useState<FeedbackState | null>(null);

  const periodMonth = useMemo(() => toPeriodMonth(requestedMonth), [requestedMonth]);

  const snapshotQuery = useQuery<SnapshotLookupResult>({
    queryKey: ["leader-kpi-snapshot", accessToken, requestedMonth, isAutoLookupEnabled],
    queryFn: () => lookupLatestSnapshot(accessToken!, requestedMonth, isAutoLookupEnabled),
    enabled: Boolean(accessToken && periodMonth),
    retry: false,
    refetchOnWindowFocus: false,
    staleTime: 60_000,
  });

  const raiseQuery = useQuery({
    queryKey: ["compensation-approvals", accessToken],
    queryFn: () =>
      listRaiseRequests(accessToken!, {
        status: "awaiting_leader",
        limit: 50,
        offset: 0,
      }),
    enabled: Boolean(accessToken),
    retry: false,
  });

  const approveRaiseMutation = useMutation({
    mutationFn: ({ requestId, note }: { requestId: string; note: string }) =>
      approveRaiseRequest(accessToken!, requestId, { note: note || undefined }),
    onSuccess: (_, variables) => {
      setDecisionFeedback({ type: "success", message: t("compensationRaise.leader.approveSuccess") });
      setDecisionNotes((prev) => ({ ...prev, [variables.requestId]: "" }));
      void queryClient.invalidateQueries({ queryKey: ["compensation-approvals", accessToken] });
    },
    onError: (error: unknown) => {
      setDecisionFeedback({ type: "error", message: resolveCompensationApiError(error, t) });
    },
  });

  const rejectRaiseMutation = useMutation({
    mutationFn: ({ requestId, note }: { requestId: string; note: string }) =>
      rejectRaiseRequest(accessToken!, requestId, { note: note || undefined }),
    onSuccess: (_, variables) => {
      setDecisionFeedback({ type: "success", message: t("compensationRaise.leader.rejectSuccess") });
      setDecisionNotes((prev) => ({ ...prev, [variables.requestId]: "" }));
      void queryClient.invalidateQueries({ queryKey: ["compensation-approvals", accessToken] });
    },
    onError: (error: unknown) => {
      setDecisionFeedback({ type: "error", message: resolveCompensationApiError(error, t) });
    },
  });

  useEffect(() => {
    if (!snapshotQuery.data || !accessToken) {
      return;
    }
    if (!isAutoLookupEnabled) {
      return;
    }

    const resolvedMonth = snapshotQuery.data.resolvedMonth;
    const fromMonth = snapshotQuery.data.requestedMonth;
    if (resolvedMonth !== fromMonth) {
      setAutoLookupNotice({ fromMonth, toMonth: resolvedMonth });
    } else {
      setAutoLookupNotice(null);
    }

    const nextQueryKey = ["leader-kpi-snapshot", accessToken, resolvedMonth, false] as const;
    queryClient.setQueryData(nextQueryKey, {
      attemptedMonths: [resolvedMonth],
      requestedMonth: resolvedMonth,
      resolvedMonth,
      response: snapshotQuery.data.response,
    });

    if (monthInput.trim() === requestedMonth) {
      setMonthInput(resolvedMonth);
    }
    setRequestedMonth(resolvedMonth);
    setIsAutoLookupEnabled(false);
  }, [
    accessToken,
    isAutoLookupEnabled,
    monthInput,
    queryClient,
    requestedMonth,
    snapshotQuery.data,
  ]);

  const effectivePeriodMonth = useMemo(
    () => snapshotQuery.data?.response.period_month ?? periodMonth,
    [periodMonth, snapshotQuery.data?.response.period_month],
  );
  const metrics = useMemo(
    () => snapshotQuery.data?.response.metrics ?? [],
    [snapshotQuery.data?.response.metrics],
  );
  const sortedMetrics = useMemo(
    () =>
      [...metrics].sort(
        (left, right) => METRIC_ORDER.indexOf(left.metric_key) - METRIC_ORDER.indexOf(right.metric_key),
      ),
    [metrics],
  );
  const generatedAt = useMemo(
    () => sortedMetrics.find((metric) => metric.generated_at)?.generated_at ?? null,
    [sortedMetrics],
  );
  const locale = i18n.language?.startsWith("ru") ? "ru-RU" : "en-US";
  const raiseItems = raiseQuery.data?.items ?? [];

  const handleDecisionNoteChange = (requestId: string, value: string) => {
    setDecisionNotes((prev) => ({ ...prev, [requestId]: value }));
  };

  if (!accessToken) {
    return <Alert severity="warning">{t("leaderDashboard.authRequired")}</Alert>;
  }

  const handleMonthSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalized = normalizeMonthValue(monthInput);
    setAutoLookupNotice(null);
    setIsAutoLookupEnabled(true);
    setRequestedMonth(normalized);
    setMonthInput(normalized);
  };

  const handleMonthReset = () => {
    setMonthInput(DEFAULT_MONTH);
    setRequestedMonth(DEFAULT_MONTH);
    setIsAutoLookupEnabled(true);
    setAutoLookupNotice(null);
  };

  const handleExport = async (format: KpiSnapshotExportFormat) => {
    setExportError(null);
    setPendingExportFormat(format);
    try {
      await downloadKpiSnapshotExport(accessToken, format, effectivePeriodMonth);
    } catch (error) {
      setExportError(resolveLeaderWorkspaceError(error, t));
    } finally {
      setPendingExportFormat(null);
    }
  };

  return (
    <Stack spacing={3}>
      <PageHero
        title={t("leaderWorkspace")}
        description={t("leaderWorkspaceSubtitle")}
        imageSrc="/images/company-hero.jpg"
        imageAlt={t("leaderWorkspace")}
      />

      <Stack
        component="form"
        direction={{ xs: "column", md: "row" }}
        spacing={1.5}
        onSubmit={handleMonthSubmit}
      >
        <TextField
          label={t("leaderDashboard.periodLabel")}
          helperText={t("leaderDashboard.periodHelp")}
          type="month"
          value={monthInput}
          onChange={(event) => setMonthInput(event.target.value)}
          fullWidth
        />
        <Button type="submit" variant="contained">
          {t("leaderDashboard.loadAction")}
        </Button>
        <Button type="button" variant="outlined" onClick={handleMonthReset}>
          {t("leaderDashboard.resetAction")}
        </Button>
      </Stack>

      <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
        <Button
          variant="outlined"
          onClick={() => void handleExport("csv")}
          disabled={pendingExportFormat !== null || !effectivePeriodMonth}
        >
          {pendingExportFormat === "csv"
            ? t("leaderDashboard.exportCsvPending")
            : t("leaderDashboard.exportCsv")}
        </Button>
        <Button
          variant="outlined"
          onClick={() => void handleExport("xlsx")}
          disabled={pendingExportFormat !== null || !effectivePeriodMonth}
        >
          {pendingExportFormat === "xlsx"
            ? t("leaderDashboard.exportXlsxPending")
            : t("leaderDashboard.exportXlsx")}
        </Button>
      </Stack>

      {exportError ? <Alert severity="error">{exportError}</Alert> : null}
      {autoLookupNotice ? (
        <Alert severity="info">
          {t("leaderDashboard.autoResolved", {
            from: autoLookupNotice.fromMonth,
            to: autoLookupNotice.toMonth,
          })}
        </Alert>
      ) : null}

      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Stack spacing={0.5}>
            <Typography variant="h6">{t("leaderDashboard.metrics.title")}</Typography>
            <Typography variant="body2" color="text.secondary">
              {t("leaderDashboard.metrics.subtitle")}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {t("leaderDashboard.periodMeta", { value: effectivePeriodMonth })}
              {generatedAt
                ? ` • ${t("leaderDashboard.generatedAtMeta", {
                    value: formatDateTimeValue(generatedAt, locale),
                  })}`
                : ""}
            </Typography>
          </Stack>

          {snapshotQuery.isLoading ? (
            <Stack spacing={2} alignItems="center" sx={{ py: 4 }}>
              <CircularProgress size={28} />
              <Typography variant="body2">{t("leaderDashboard.loading")}</Typography>
            </Stack>
          ) : snapshotQuery.isError ? (
            <Alert severity="error" sx={{ borderRadius: 0 }}>
              {resolveLeaderWorkspaceError(snapshotQuery.error, t)}
            </Alert>
          ) : metrics.length === 0 ? (
            <Alert severity="info" sx={{ borderRadius: 0 }}>
              <Stack spacing={0.5}>
                <Typography variant="body2">{t("leaderDashboard.empty")}</Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("leaderDashboard.emptyHint")}
                </Typography>
              </Stack>
            </Alert>
          ) : (
            <>
              <Grid2 container spacing={2}>
                {sortedMetrics.map((metric) => (
                  <Grid2 key={metric.metric_key} size={{ xs: 12, sm: 6, lg: 3 }}>
                    <Paper variant="outlined" sx={{ p: 2 }}>
                      <Typography variant="caption" color="text.secondary">
                        {t(`leaderDashboard.metricKey.${metric.metric_key}`)}
                      </Typography>
                      <Typography variant="h5" sx={{ mt: 0.5 }}>
                        {new Intl.NumberFormat(locale).format(metric.metric_value)}
                      </Typography>
                    </Paper>
                  </Grid2>
                ))}
              </Grid2>

              <Paper variant="outlined" sx={{ overflowX: "auto" }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>{t("leaderDashboard.table.metric")}</TableCell>
                      <TableCell>{t("leaderDashboard.table.value")}</TableCell>
                      <TableCell>{t("leaderDashboard.table.generatedAt")}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {sortedMetrics.map((metric) => (
                      <TableRow key={`row-${metric.metric_key}`}>
                        <TableCell>{t(`leaderDashboard.metricKey.${metric.metric_key}`)}</TableCell>
                        <TableCell>{new Intl.NumberFormat(locale).format(metric.metric_value)}</TableCell>
                        <TableCell>
                          {metric.generated_at
                            ? formatDateTimeValue(metric.generated_at, locale)
                            : t("leaderDashboard.notAvailable")}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Paper>
            </>
          )}
        </Stack>
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Stack spacing={2}>
          <Stack spacing={0.5}>
            <Typography variant="h6">{t("compensationRaise.leader.title")}</Typography>
            <Typography variant="body2" color="text.secondary">
              {t("compensationRaise.leader.subtitle")}
            </Typography>
          </Stack>

          {decisionFeedback ? (
            <Alert severity={decisionFeedback.type}>{decisionFeedback.message}</Alert>
          ) : null}

          {raiseQuery.isLoading ? (
            <Stack spacing={2} alignItems="center" sx={{ py: 4 }}>
              <CircularProgress size={24} />
              <Typography variant="body2">{t("compensationRaise.leader.loading")}</Typography>
            </Stack>
          ) : raiseQuery.isError ? (
            <Alert severity="error" sx={{ borderRadius: 0 }}>
              {resolveCompensationApiError(raiseQuery.error, t)}
            </Alert>
          ) : raiseItems.length === 0 ? (
            <Alert severity="info" sx={{ borderRadius: 0 }}>
              {t("compensationRaise.leader.empty")}
            </Alert>
          ) : (
            <Paper variant="outlined" sx={{ overflowX: "auto" }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>{t("compensationRaise.leader.columns.employee")}</TableCell>
                    <TableCell>{t("compensationRaise.leader.columns.salary")}</TableCell>
                    <TableCell>{t("compensationRaise.leader.columns.effectiveDate")}</TableCell>
                    <TableCell>{t("compensationRaise.leader.columns.confirmations")}</TableCell>
                    <TableCell>{t("compensationRaise.leader.columns.note")}</TableCell>
                    <TableCell align="right">{t("compensationRaise.leader.columns.actions")}</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {raiseItems.map((item) => (
                    <TableRow key={item.request_id}>
                      <TableCell>
                        <Stack spacing={0.5}>
                          <Typography variant="body2" fontWeight={600}>
                            {formatShortUuid(item.employee_id)}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {item.employee_id}
                          </Typography>
                        </Stack>
                      </TableCell>
                      <TableCell>
                        {formatMoneyValue(item.proposed_base_salary, item.currency, t)}
                      </TableCell>
                      <TableCell>{formatDateValue(item.effective_date, locale)}</TableCell>
                      <TableCell>
                        {t("compensationRaise.confirmations", {
                          count: item.confirmation_count,
                          quorum: item.confirmation_quorum,
                        })}
                      </TableCell>
                      <TableCell sx={{ minWidth: 220 }}>
                        <TextField
                          size="small"
                          fullWidth
                          placeholder={t("compensationRaise.leader.notePlaceholder")}
                          value={decisionNotes[item.request_id] ?? ""}
                          onChange={(event) =>
                            handleDecisionNoteChange(item.request_id, event.target.value)
                          }
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={1} justifyContent="flex-end">
                          <Button
                            size="small"
                            variant="contained"
                            onClick={() =>
                              approveRaiseMutation.mutate({
                                requestId: item.request_id,
                                note: decisionNotes[item.request_id] ?? "",
                              })
                            }
                            disabled={
                              approveRaiseMutation.isPending
                              && approveRaiseMutation.variables?.requestId === item.request_id
                            }
                          >
                            {approveRaiseMutation.isPending
                            && approveRaiseMutation.variables?.requestId === item.request_id
                              ? t("compensationRaise.leader.approvePending")
                              : t("compensationRaise.leader.approveAction")}
                          </Button>
                          <Button
                            size="small"
                            variant="outlined"
                            color="error"
                            onClick={() =>
                              rejectRaiseMutation.mutate({
                                requestId: item.request_id,
                                note: decisionNotes[item.request_id] ?? "",
                              })
                            }
                            disabled={
                              rejectRaiseMutation.isPending
                              && rejectRaiseMutation.variables?.requestId === item.request_id
                            }
                          >
                            {rejectRaiseMutation.isPending
                            && rejectRaiseMutation.variables?.requestId === item.request_id
                              ? t("compensationRaise.leader.rejectPending")
                              : t("compensationRaise.leader.rejectAction")}
                          </Button>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Paper>
          )}
        </Stack>
      </Paper>
    </Stack>
  );
}

function resolveCurrentMonthValue(): string {
  const now = new Date();
  const year = String(now.getFullYear());
  const month = String(now.getMonth() + 1).padStart(2, "0");
  return `${year}-${month}`;
}

async function lookupLatestSnapshot(
  accessToken: string,
  startMonth: string,
  isAutoLookupEnabled: boolean,
): Promise<SnapshotLookupResult> {
  const periodMonth = toPeriodMonth(startMonth);
  if (!periodMonth) {
    return {
      attemptedMonths: [startMonth],
      requestedMonth: startMonth,
      resolvedMonth: startMonth,
      response: { period_month: "", metrics: [] },
    };
  }

  if (!isAutoLookupEnabled) {
    const response = await readKpiSnapshot(accessToken, periodMonth);
    return {
      attemptedMonths: [startMonth],
      requestedMonth: startMonth,
      resolvedMonth: startMonth,
      response,
    };
  }

  const attemptedMonths: string[] = [];
  let initialResponse: KpiSnapshotReadResponse | null = null;
  for (let offset = 0; offset <= LOOKBACK_MONTHS; offset += 1) {
    const candidateMonth = shiftMonth(startMonth, -offset);
    attemptedMonths.push(candidateMonth);
    const response = await readKpiSnapshot(accessToken, toPeriodMonth(candidateMonth));
    if (offset === 0) {
      initialResponse = response;
    }
    if (response.metrics.length > 0) {
      return {
        attemptedMonths,
        requestedMonth: startMonth,
        resolvedMonth: candidateMonth,
        response,
      };
    }
  }

  return {
    attemptedMonths,
    requestedMonth: startMonth,
    resolvedMonth: startMonth,
    response: initialResponse ?? { period_month: periodMonth, metrics: [] },
  };
}

function shiftMonth(value: string, deltaMonths: number): string {
  const match = value.match(/^(\d{4})-(\d{2})$/);
  if (!match) {
    return value;
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  if (Number.isNaN(year) || Number.isNaN(month)) {
    return value;
  }
  const shifted = new Date(Date.UTC(year, month - 1 + deltaMonths, 1));
  const shiftedYear = String(shifted.getUTCFullYear());
  const shiftedMonth = String(shifted.getUTCMonth() + 1).padStart(2, "0");
  return `${shiftedYear}-${shiftedMonth}`;
}

function normalizeMonthValue(value: string): string {
  const trimmed = value.trim();
  if (!/^\d{4}-\d{2}$/.test(trimmed)) {
    return DEFAULT_MONTH;
  }
  return trimmed;
}

function toPeriodMonth(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return "";
  }
  return `${trimmed}-01`;
}

function formatDateTimeValue(value: string, locale: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString(locale);
}

function formatDateValue(value: string, locale: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleDateString(locale);
}

function formatMoneyValue(
  value: number | null | undefined,
  currency: string,
  t: (key: string) => string,
): string {
  if (value === null || value === undefined) {
    return t("compensationTable.notAvailable");
  }
  return `${value.toFixed(2)} ${currency}`;
}

function formatShortUuid(value: string): string {
  return value.slice(0, 8);
}

function resolveLeaderWorkspaceError(error: unknown, t: (key: string) => string): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return t("leaderDashboard.errors.http_401");
    }
    if (error.status === 403) {
      return t("leaderDashboard.errors.http_403");
    }
    if (error.status === 422) {
      return t("leaderDashboard.errors.http_422");
    }
  }
  return t("leaderDashboard.errors.generic");
}
