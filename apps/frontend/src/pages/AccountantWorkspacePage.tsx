import { FormEvent, useState } from "react";
import {
  Alert,
  Button,
  CircularProgress,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import {
  ApiError,
  downloadAccountingWorkspaceExport,
  listAccountingWorkspace,
  type AccountingWorkspaceExportFormat,
  type AccountingWorkspaceRowResponse,
} from "../api";
import { readAuthSession } from "../app/auth/session";
import { useSentryRouteTags } from "../app/observability/sentry";
import { NotificationsPanel } from "../components/NotificationsPanel";

const ROWS_PER_PAGE = 20;

/**
 * Read-only accountant workspace with controlled CSV/XLSX export actions.
 */
export function AccountantWorkspacePage() {
  const { t } = useTranslation();
  useSentryRouteTags("/");
  const session = readAuthSession();
  const accessToken = session.accessToken;
  const [page, setPage] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [exportError, setExportError] = useState<string | null>(null);
  const [pendingExportFormat, setPendingExportFormat] =
    useState<AccountingWorkspaceExportFormat | null>(null);

  const workspaceQuery = useQuery({
    queryKey: ["accounting-workspace", accessToken, search, page],
    queryFn: () =>
      listAccountingWorkspace(accessToken!, {
        limit: ROWS_PER_PAGE,
        offset: page * ROWS_PER_PAGE,
        search: search || undefined,
      }),
    enabled: Boolean(accessToken),
    retry: false,
  });

  if (!accessToken) {
    return <Alert severity="warning">{t("accountantDashboard.authRequired")}</Alert>;
  }

  const handleSearchSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPage(0);
    setSearch(searchInput.trim());
  };

  const handleSearchReset = () => {
    setSearchInput("");
    setSearch("");
    setPage(0);
  };

  const handleExport = async (format: AccountingWorkspaceExportFormat) => {
    setExportError(null);
    setPendingExportFormat(format);
    try {
      await downloadAccountingWorkspaceExport(accessToken, format, search || undefined);
    } catch (error) {
      setExportError(resolveAccountantWorkspaceError(error, t));
    } finally {
      setPendingExportFormat(null);
    }
  };

  const items = workspaceQuery.data?.items ?? [];
  const total = workspaceQuery.data?.total ?? 0;

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4">{t("accountantWorkspace")}</Typography>
        <Typography variant="body2" color="text.secondary">
          {t("accountantWorkspaceSubtitle")}
        </Typography>
      </Stack>

      <NotificationsPanel accessToken={accessToken} workspace="accountant" />

      <Stack
        component="form"
        direction={{ xs: "column", md: "row" }}
        spacing={1.5}
        onSubmit={handleSearchSubmit}
      >
        <TextField
          label={t("accountantDashboard.searchLabel")}
          placeholder={t("accountantDashboard.searchPlaceholder")}
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          fullWidth
        />
        <Button type="submit" variant="contained">
          {t("accountantDashboard.searchAction")}
        </Button>
        <Button type="button" variant="outlined" onClick={handleSearchReset}>
          {t("accountantDashboard.resetAction")}
        </Button>
      </Stack>

      <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
        <Button
          variant="outlined"
          onClick={() => void handleExport("csv")}
          disabled={pendingExportFormat !== null}
        >
          {pendingExportFormat === "csv"
            ? t("accountantDashboard.exportCsvPending")
            : t("accountantDashboard.exportCsv")}
        </Button>
        <Button
          variant="outlined"
          onClick={() => void handleExport("xlsx")}
          disabled={pendingExportFormat !== null}
        >
          {pendingExportFormat === "xlsx"
            ? t("accountantDashboard.exportXlsxPending")
            : t("accountantDashboard.exportXlsx")}
        </Button>
      </Stack>

      {exportError ? <Alert severity="error">{exportError}</Alert> : null}

      <Paper sx={{ overflowX: "auto" }}>
        {workspaceQuery.isLoading ? (
          <Stack spacing={2} alignItems="center" sx={{ py: 4 }}>
            <CircularProgress size={28} />
            <Typography variant="body2">{t("accountantDashboard.loading")}</Typography>
          </Stack>
        ) : workspaceQuery.isError ? (
          <Alert severity="error" sx={{ borderRadius: 0 }}>
            {resolveAccountantWorkspaceError(workspaceQuery.error, t)}
          </Alert>
        ) : items.length === 0 ? (
          <Alert severity="info" sx={{ borderRadius: 0 }}>
            {t("accountantDashboard.empty")}
          </Alert>
        ) : (
          <>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t("accountantDashboard.table.employee")}</TableCell>
                  <TableCell>{t("accountantDashboard.table.location")}</TableCell>
                  <TableCell>{t("accountantDashboard.table.title")}</TableCell>
                  <TableCell>{t("accountantDashboard.table.startDate")}</TableCell>
                  <TableCell>{t("accountantDashboard.table.offerTerms")}</TableCell>
                  <TableCell>{t("accountantDashboard.table.status")}</TableCell>
                  <TableCell>{t("accountantDashboard.table.taskSummary")}</TableCell>
                  <TableCell>{t("accountantDashboard.table.latestDueAt")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.onboarding_id}>
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
                    <TableCell>{item.location || t("accountantDashboard.notAvailable")}</TableCell>
                    <TableCell>
                      {item.current_title || t("accountantDashboard.notAvailable")}
                    </TableCell>
                    <TableCell>
                      {formatDateValue(item.start_date, t("accountantDashboard.notAvailable"))}
                    </TableCell>
                    <TableCell>
                      {item.offer_terms_summary || t("accountantDashboard.notAvailable")}
                    </TableCell>
                    <TableCell>{t(`accountantDashboard.status.${item.onboarding_status}`)}</TableCell>
                    <TableCell>{renderTaskSummary(item, t)}</TableCell>
                    <TableCell>
                      {formatDateTimeValue(
                        item.latest_accountant_due_at,
                        t("accountantDashboard.notAvailable"),
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <TablePagination
              component="div"
              count={total}
              page={page}
              onPageChange={(_event, nextPage) => setPage(nextPage)}
              rowsPerPage={ROWS_PER_PAGE}
              rowsPerPageOptions={[ROWS_PER_PAGE]}
            />
          </>
        )}
      </Paper>
    </Stack>
  );
}

function renderTaskSummary(
  item: AccountingWorkspaceRowResponse,
  t: (key: string, options?: Record<string, unknown>) => string,
) {
  return t("accountantDashboard.taskSummary", {
    total: item.accountant_task_total,
    pending: item.accountant_task_pending,
    inProgress: item.accountant_task_in_progress,
    completed: item.accountant_task_completed,
    overdue: item.accountant_task_overdue,
  });
}

function formatDateValue(value: string | null, fallback: string): string {
  if (!value) {
    return fallback;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleDateString();
}

function formatDateTimeValue(value: string | null, fallback: string): string {
  if (!value) {
    return fallback;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function resolveAccountantWorkspaceError(
  error: unknown,
  t: (key: string) => string,
): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return t("accountantDashboard.errors.http_401");
    }
    if (error.status === 403) {
      return t("accountantDashboard.errors.http_403");
    }
    if (error.status === 422) {
      return t("accountantDashboard.errors.http_422");
    }
  }
  return t("accountantDashboard.errors.generic");
}
