import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
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
  downloadAuditEventsExport,
  listAuditEvents,
  type AuditEventExportFormat,
  type AuditEventListQuery,
} from "../../api";
import { formatDateTime, normalizeFilterValue, resolveApiErrorMessage } from "./adminUtils";

const DEFAULT_LIMIT = 20;

type FeedbackState = {
  type: "success" | "error";
  message: string;
};

type AuditFilterDraft = {
  action: string;
  resourceType: string;
  correlationId: string;
  source: AuditEventListQuery["source"] | "all";
  result: AuditEventListQuery["result"] | "all";
  occurredFrom: string;
  occurredTo: string;
};

const EMPTY_DRAFT: AuditFilterDraft = {
  action: "",
  resourceType: "",
  correlationId: "",
  source: "all",
  result: "all",
  occurredFrom: "",
  occurredTo: "",
};

/**
 * Admin audit console for filtered read-only inspection and evidence exports.
 */
export function AdminAuditPage() {
  const { t } = useTranslation();

  const [draft, setDraft] = useState<AuditFilterDraft>(EMPTY_DRAFT);
  const [query, setQuery] = useState<AuditEventListQuery>({
    limit: DEFAULT_LIMIT,
    offset: 0,
  });
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const [pendingExportFormat, setPendingExportFormat] =
    useState<AuditEventExportFormat | null>(null);

  const listQuery = useQuery({
    queryKey: ["admin-audit-list", query],
    queryFn: () => listAuditEvents(query),
  });

  const exportQuery = useMemo(
    () => ({
      action: query.action,
      result: query.result,
      source: query.source,
      resourceType: query.resourceType,
      correlationId: query.correlationId,
      occurredFrom: query.occurredFrom,
      occurredTo: query.occurredTo,
    }),
    [
      query.action,
      query.correlationId,
      query.occurredFrom,
      query.occurredTo,
      query.resourceType,
      query.result,
      query.source,
    ],
  );

  const items = listQuery.data?.items ?? [];
  const total = listQuery.data?.total ?? 0;
  const page = Math.floor(query.offset / query.limit);
  const listErrorMessage = useMemo(() => {
    if (!listQuery.error) {
      return "";
    }
    return resolveApiErrorMessage(listQuery.error, t, "adminAudit");
  }, [listQuery.error, t]);

  const handleApplyFilters = () => {
    setFeedback(null);
    setQuery((prev) => ({
      ...prev,
      offset: 0,
      action: normalizeFilterValue(draft.action),
      resourceType: normalizeFilterValue(draft.resourceType),
      correlationId: normalizeFilterValue(draft.correlationId),
      source: draft.source === "all" ? undefined : draft.source,
      result: draft.result === "all" ? undefined : draft.result,
      occurredFrom: normalizeDateTimeFilter(draft.occurredFrom),
      occurredTo: normalizeDateTimeFilter(draft.occurredTo),
    }));
  };

  const handleResetFilters = () => {
    setDraft(EMPTY_DRAFT);
    setFeedback(null);
    setQuery({
      limit: DEFAULT_LIMIT,
      offset: 0,
    });
  };

  const handleExport = async (format: AuditEventExportFormat) => {
    setFeedback(null);
    setPendingExportFormat(format);
    try {
      await downloadAuditEventsExport(format, exportQuery);
      setFeedback({
        type: "success",
        message: t("adminAudit.exportSuccess", {
          format: t(`adminAudit.exportFormats.${format}`),
        }),
      });
    } catch (error) {
      setFeedback({ type: "error", message: resolveApiErrorMessage(error, t, "adminAudit") });
    } finally {
      setPendingExportFormat(null);
    }
  };

  return (
    <Stack spacing={2}>
      <Box>
        <Typography variant="h4">{t("adminAudit.title")}</Typography>
        <Typography variant="body2">{t("adminAudit.subtitle")}</Typography>
      </Box>

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Typography variant="h6">{t("adminAudit.filters.title")}</Typography>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField
              size="small"
              label={t("adminAudit.filters.action")}
              value={draft.action}
              onChange={(event) => setDraft((prev) => ({ ...prev, action: event.target.value }))}
            />
            <TextField
              size="small"
              label={t("adminAudit.filters.resourceType")}
              value={draft.resourceType}
              onChange={(event) =>
                setDraft((prev) => ({ ...prev, resourceType: event.target.value }))
              }
            />
            <TextField
              size="small"
              label={t("adminAudit.filters.correlationId")}
              value={draft.correlationId}
              onChange={(event) =>
                setDraft((prev) => ({ ...prev, correlationId: event.target.value }))
              }
            />
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="admin-audit-source-label">{t("adminAudit.filters.source")}</InputLabel>
              <Select
                labelId="admin-audit-source-label"
                value={draft.source}
                label={t("adminAudit.filters.source")}
                onChange={(event) =>
                  setDraft((prev) => ({
                    ...prev,
                    source: event.target.value as AuditFilterDraft["source"],
                  }))
                }
              >
                <MenuItem value="all">{t("adminAudit.filters.any")}</MenuItem>
                <MenuItem value="api">{t("adminAudit.source.api")}</MenuItem>
                <MenuItem value="job">{t("adminAudit.source.job")}</MenuItem>
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="admin-audit-result-label">{t("adminAudit.filters.result")}</InputLabel>
              <Select
                labelId="admin-audit-result-label"
                value={draft.result}
                label={t("adminAudit.filters.result")}
                onChange={(event) =>
                  setDraft((prev) => ({
                    ...prev,
                    result: event.target.value as AuditFilterDraft["result"],
                  }))
                }
              >
                <MenuItem value="all">{t("adminAudit.filters.any")}</MenuItem>
                <MenuItem value="allowed">{t("adminAudit.result.allowed")}</MenuItem>
                <MenuItem value="denied">{t("adminAudit.result.denied")}</MenuItem>
                <MenuItem value="success">{t("adminAudit.result.success")}</MenuItem>
                <MenuItem value="failure">{t("adminAudit.result.failure")}</MenuItem>
              </Select>
            </FormControl>
          </Stack>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField
              size="small"
              type="datetime-local"
              label={t("adminAudit.filters.occurredFrom")}
              value={draft.occurredFrom}
              onChange={(event) =>
                setDraft((prev) => ({ ...prev, occurredFrom: event.target.value }))
              }
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              size="small"
              type="datetime-local"
              label={t("adminAudit.filters.occurredTo")}
              value={draft.occurredTo}
              onChange={(event) =>
                setDraft((prev) => ({ ...prev, occurredTo: event.target.value }))
              }
              InputLabelProps={{ shrink: true }}
            />
            <Button variant="contained" onClick={handleApplyFilters}>
              {t("adminAudit.filters.apply")}
            </Button>
            <Button variant="outlined" onClick={handleResetFilters}>
              {t("adminAudit.filters.reset")}
            </Button>
          </Stack>
        </Stack>
      </Paper>

      <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
        <Button
          variant="outlined"
          onClick={() => void handleExport("csv")}
          disabled={pendingExportFormat !== null}
        >
          {pendingExportFormat === "csv"
            ? t("adminAudit.exportCsvPending")
            : t("adminAudit.exportCsv")}
        </Button>
        <Button
          variant="outlined"
          onClick={() => void handleExport("jsonl")}
          disabled={pendingExportFormat !== null}
        >
          {pendingExportFormat === "jsonl"
            ? t("adminAudit.exportJsonlPending")
            : t("adminAudit.exportJsonl")}
        </Button>
        <Button
          variant="outlined"
          onClick={() => void handleExport("xlsx")}
          disabled={pendingExportFormat !== null}
        >
          {pendingExportFormat === "xlsx"
            ? t("adminAudit.exportXlsxPending")
            : t("adminAudit.exportXlsx")}
        </Button>
      </Stack>

      {feedback ? <Alert severity={feedback.type}>{feedback.message}</Alert> : null}
      {listQuery.error ? <Alert severity="error">{listErrorMessage}</Alert> : null}

      <Paper>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t("adminAudit.table.occurredAt")}</TableCell>
              <TableCell>{t("adminAudit.table.source")}</TableCell>
              <TableCell>{t("adminAudit.table.actor")}</TableCell>
              <TableCell>{t("adminAudit.table.action")}</TableCell>
              <TableCell>{t("adminAudit.table.resource")}</TableCell>
              <TableCell>{t("adminAudit.table.result")}</TableCell>
              <TableCell>{t("adminAudit.table.reason")}</TableCell>
              <TableCell>{t("adminAudit.table.correlationId")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {listQuery.isLoading ? (
              <TableRow>
                <TableCell colSpan={8}>{t("adminAudit.loading")}</TableCell>
              </TableRow>
            ) : null}
            {!listQuery.isLoading && items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8}>{t("adminAudit.empty")}</TableCell>
              </TableRow>
            ) : null}
            {items.map((item) => (
              <TableRow key={item.event_id}>
                <TableCell>{formatDateTime(item.occurred_at, t("adminAudit.notAvailable"))}</TableCell>
                <TableCell>{t(`adminAudit.source.${item.source}`)}</TableCell>
                <TableCell>
                  <Stack spacing={0.25}>
                    <Typography variant="body2">{item.actor_sub || t("adminAudit.notAvailable")}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {item.actor_role || t("adminAudit.notAvailable")}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {item.ip || t("adminAudit.notAvailable")}
                    </Typography>
                  </Stack>
                </TableCell>
                <TableCell>{item.action}</TableCell>
                <TableCell>
                  <Stack spacing={0.25}>
                    <Typography variant="body2">{item.resource_type}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {item.resource_id || t("adminAudit.notAvailable")}
                    </Typography>
                  </Stack>
                </TableCell>
                <TableCell>{t(`adminAudit.result.${item.result}`)}</TableCell>
                <TableCell>
                  <Stack spacing={0.25}>
                    <Typography variant="body2">{item.reason || t("adminAudit.notAvailable")}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {item.user_agent || t("adminAudit.notAvailable")}
                    </Typography>
                  </Stack>
                </TableCell>
                <TableCell>{item.correlation_id || t("adminAudit.notAvailable")}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={total}
          page={page}
          rowsPerPage={query.limit}
          onPageChange={(_event, nextPage) =>
            setQuery((prev) => ({ ...prev, offset: nextPage * prev.limit }))
          }
          onRowsPerPageChange={(event) => {
            const nextLimit = Number.parseInt(event.target.value, 10);
            setQuery((prev) => ({ ...prev, limit: nextLimit, offset: 0 }));
          }}
          rowsPerPageOptions={[10, 20, 50, 100]}
        />
      </Paper>
    </Stack>
  );
}

function normalizeDateTimeFilter(value: string): string | undefined {
  const normalized = value.trim();
  if (!normalized) {
    return undefined;
  }
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) {
    return undefined;
  }
  return parsed.toISOString();
}
