import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  CircularProgress,
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
  listCompensationTable,
  upsertBonusEntry,
  type BonusUpsertRequest,
  type CompensationTableRowResponse,
} from "../api";
import { resolveCompensationApiError } from "../pages/compensation/compensationErrors";

type FeedbackState = {
  type: "success" | "error";
  message: string;
};

type CompensationTablePanelProps = {
  accessToken: string;
  title: string;
  subtitle?: string;
  showBonusForm?: boolean;
  onRowsLoaded?: (rows: CompensationTableRowResponse[]) => void;
};

const TABLE_LIMIT = 100;

export function CompensationTablePanel({
  accessToken,
  title,
  subtitle,
  showBonusForm = false,
  onRowsLoaded,
}: CompensationTablePanelProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [bonusEmployeeId, setBonusEmployeeId] = useState("");
  const [bonusMonth, setBonusMonth] = useState("");
  const [bonusAmount, setBonusAmount] = useState("");
  const [bonusNote, setBonusNote] = useState("");
  const [bonusFeedback, setBonusFeedback] = useState<FeedbackState | null>(null);

  const tableQuery = useQuery({
    queryKey: ["compensation-table", accessToken],
    queryFn: () =>
      listCompensationTable(accessToken, {
        limit: TABLE_LIMIT,
        offset: 0,
      }),
    enabled: Boolean(accessToken),
    retry: false,
  });

  const rows = useMemo(() => tableQuery.data?.items ?? [], [tableQuery.data]);

  useEffect(() => {
    if (tableQuery.data && Array.isArray(tableQuery.data.items)) {
      onRowsLoaded?.(tableQuery.data.items);
    }
  }, [onRowsLoaded, tableQuery.data]);

  const employeeOptions = useMemo(
    () =>
      rows.map((row) => ({
        id: row.employee_id,
        label: `${row.full_name} (${shortId(row.employee_id)})`,
      })),
    [rows],
  );

  const bonusMutation = useMutation({
    mutationFn: (payload: BonusUpsertRequest) => upsertBonusEntry(accessToken, payload),
    onSuccess: () => {
      setBonusFeedback({ type: "success", message: t("compensationBonus.success") });
      setBonusAmount("");
      setBonusNote("");
      void queryClient.invalidateQueries({ queryKey: ["compensation-table", accessToken] });
    },
    onError: (error: unknown) => {
      setBonusFeedback({ type: "error", message: resolveCompensationApiError(error, t) });
    },
  });

  const handleBonusSubmit = () => {
    if (!bonusEmployeeId) {
      setBonusFeedback({ type: "error", message: t("compensationBonus.errors.employeeRequired") });
      return;
    }
    if (!bonusMonth) {
      setBonusFeedback({ type: "error", message: t("compensationBonus.errors.monthRequired") });
      return;
    }
    const amountValue = Number.parseFloat(bonusAmount);
    if (!Number.isFinite(amountValue) || amountValue <= 0) {
      setBonusFeedback({ type: "error", message: t("compensationBonus.errors.amountRequired") });
      return;
    }
    const periodMonth = `${bonusMonth}-01`;
    setBonusFeedback(null);
    bonusMutation.mutate({
      employee_id: bonusEmployeeId,
      period_month: periodMonth,
      amount: amountValue,
      note: bonusNote || undefined,
    });
  };

  return (
    <Paper sx={{ p: 2 }}>
      <Stack spacing={2}>
        <Stack spacing={0.5}>
          <Typography variant="h6">{title}</Typography>
          {subtitle ? (
            <Typography variant="body2" color="text.secondary">
              {subtitle}
            </Typography>
          ) : null}
        </Stack>

        {showBonusForm ? (
          <Stack spacing={2}>
            <Typography variant="subtitle1">{t("compensationBonus.title")}</Typography>
            <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
              <TextField
                select
                label={t("compensationBonus.employeeLabel")}
                value={bonusEmployeeId}
                onChange={(event) => setBonusEmployeeId(event.target.value)}
                fullWidth
              >
                {employeeOptions.map((option) => (
                  <MenuItem key={option.id} value={option.id}>
                    {option.label}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                label={t("compensationBonus.monthLabel")}
                type="month"
                value={bonusMonth}
                onChange={(event) => setBonusMonth(event.target.value)}
                fullWidth
              />
              <TextField
                label={t("compensationBonus.amountLabel")}
                type="number"
                value={bonusAmount}
                onChange={(event) => setBonusAmount(event.target.value)}
                fullWidth
              />
            </Stack>
            <TextField
              label={t("compensationBonus.noteLabel")}
              value={bonusNote}
              onChange={(event) => setBonusNote(event.target.value)}
              multiline
              minRows={2}
            />
            <Stack direction="row" spacing={1} alignItems="center">
              <Button
                variant="contained"
                onClick={handleBonusSubmit}
                disabled={bonusMutation.isPending}
              >
                {bonusMutation.isPending
                  ? t("compensationBonus.submitPending")
                  : t("compensationBonus.submit")}
              </Button>
            </Stack>
            {bonusFeedback ? <Alert severity={bonusFeedback.type}>{bonusFeedback.message}</Alert> : null}
          </Stack>
        ) : null}

        {tableQuery.isLoading ? (
          <Stack spacing={2} alignItems="center" sx={{ py: 4 }}>
            <CircularProgress size={24} />
            <Typography variant="body2">{t("compensationTable.loading")}</Typography>
          </Stack>
        ) : tableQuery.isError ? (
          <Alert severity="error">
            {resolveCompensationApiError(tableQuery.error, t)}
          </Alert>
        ) : rows.length === 0 ? (
          <Alert severity="info">{t("compensationTable.empty")}</Alert>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t("compensationTable.columns.employee")}</TableCell>
                <TableCell>{t("compensationTable.columns.department")}</TableCell>
                <TableCell>{t("compensationTable.columns.position")}</TableCell>
                <TableCell>{t("compensationTable.columns.baseSalary")}</TableCell>
                <TableCell>{t("compensationTable.columns.bonus")}</TableCell>
                <TableCell>{t("compensationTable.columns.bonusPeriod")}</TableCell>
                <TableCell>{t("compensationTable.columns.band")}</TableCell>
                <TableCell>{t("compensationTable.columns.bandStatus")}</TableCell>
                <TableCell>{t("compensationTable.columns.lastRaise")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.employee_id}>
                  <TableCell>
                    <Stack spacing={0.5}>
                      <Typography variant="body2" fontWeight={600}>
                        {row.full_name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {shortId(row.employee_id)}
                      </Typography>
                    </Stack>
                  </TableCell>
                  <TableCell>{row.department || t("compensationTable.notAvailable")}</TableCell>
                  <TableCell>{row.position_title || t("compensationTable.notAvailable")}</TableCell>
                  <TableCell>{formatMoney(row.base_salary, row.currency, t)}</TableCell>
                  <TableCell>{formatMoney(row.bonus_amount, row.currency, t)}</TableCell>
                  <TableCell>
                    {row.bonus_period_month
                      ? formatMonth(row.bonus_period_month)
                      : t("compensationTable.notAvailable")}
                  </TableCell>
                  <TableCell>
                    {row.salary_band_min !== null && row.salary_band_max !== null
                      ? `${row.salary_band_min.toFixed(2)} - ${row.salary_band_max.toFixed(2)} ${row.currency}`
                      : t("compensationTable.notAvailable")}
                  </TableCell>
                  <TableCell>
                    {row.band_alignment_status
                      ? t(`compensationTable.bandStatus.${row.band_alignment_status}`)
                      : t("compensationTable.notAvailable")}
                  </TableCell>
                  <TableCell>
                    <Stack spacing={0.5}>
                      <Typography variant="body2">
                        {row.last_raise_effective_date
                          ? formatDate(row.last_raise_effective_date)
                          : t("compensationTable.notAvailable")}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {row.last_raise_status
                          ? t(`compensationRaise.status.${row.last_raise_status}`)
                          : t("compensationTable.notAvailable")}
                      </Typography>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Stack>
    </Paper>
  );
}

function formatMoney(
  value: number | null | undefined,
  currency: string,
  t: ReturnType<typeof useTranslation>["t"],
) {
  if (value === null || value === undefined) {
    return t("compensationTable.notAvailable");
  }
  return `${value.toFixed(2)} ${currency}`;
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString();
}

function formatMonth(value: string) {
  return new Date(value).toLocaleDateString(undefined, { year: "numeric", month: "short" });
}

function shortId(value: string) {
  return value.slice(0, 8);
}
