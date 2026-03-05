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
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import {
  ApiError,
  createAdminEmployeeKey,
  listAdminEmployeeKeys,
  revokeAdminEmployeeKey,
  type AdminEmployeeKeyListItem,
  type AdminEmployeeKeyListQuery,
  type EmployeeKeyStatus,
  type StaffRoleClaim,
} from "../api";

const CREATE_TARGET_ROLES: StaffRoleClaim[] = ["hr", "manager", "employee", "leader", "accountant"];
const FILTER_TARGET_ROLES: StaffRoleClaim[] = [
  "admin",
  "hr",
  "manager",
  "employee",
  "leader",
  "accountant",
];
const STATUS_OPTIONS: EmployeeKeyStatus[] = ["active", "used", "expired", "revoked"];
const DEFAULT_LIMIT = 20;

type FeedbackState = {
  type: "success" | "error";
  message: string;
};

export function AdminEmployeeKeysManagementPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [searchInput, setSearchInput] = useState("");
  const [targetRoleFilter, setTargetRoleFilter] = useState<StaffRoleClaim | "all">("all");
  const [statusFilter, setStatusFilter] = useState<EmployeeKeyStatus | "all">("all");
  const [createdByFilter, setCreatedByFilter] = useState("");
  const [query, setQuery] = useState<AdminEmployeeKeyListQuery>({
    limit: DEFAULT_LIMIT,
    offset: 0,
  });

  const [createRole, setCreateRole] = useState<StaffRoleClaim>("employee");
  const [createTtlInput, setCreateTtlInput] = useState(String(7 * 24 * 60 * 60));
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  const listQuery = useQuery({
    queryKey: ["admin-employee-keys-list", query],
    queryFn: () => listAdminEmployeeKeys(query),
  });

  const createMutation = useMutation({
    mutationFn: () => {
      const ttlSeconds = Number.parseInt(createTtlInput, 10);
      return createAdminEmployeeKey({
        target_role: createRole,
        ttl_seconds: Number.isNaN(ttlSeconds) ? 0 : ttlSeconds,
      });
    },
    onSuccess: (result) => {
      setFeedback({
        type: "success",
        message: t("adminEmployeeKeys.createSuccess", { key: result.employee_key }),
      });
      void queryClient.invalidateQueries({ queryKey: ["admin-employee-keys-list"] });
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveApiErrorMessage(error, t) });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (keyId: string) => revokeAdminEmployeeKey(keyId),
    onSuccess: () => {
      setFeedback({ type: "success", message: t("adminEmployeeKeys.revokeSuccess") });
      void queryClient.invalidateQueries({ queryKey: ["admin-employee-keys-list"] });
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveApiErrorMessage(error, t) });
    },
  });

  const items = listQuery.data?.items ?? [];
  const total = listQuery.data?.total ?? 0;
  const page = Math.floor(query.offset / query.limit);

  const hasErrorBanner = Boolean(listQuery.error) && !feedback;

  const listErrorMessage = useMemo(() => {
    if (!listQuery.error) {
      return "";
    }
    return resolveApiErrorMessage(listQuery.error, t);
  }, [listQuery.error, t]);

  const handleApplyFilters = () => {
    setFeedback(null);
    setQuery((prev) => ({
      ...prev,
      offset: 0,
      search: normalizeFilterValue(searchInput),
      target_role: targetRoleFilter === "all" ? undefined : targetRoleFilter,
      status: statusFilter === "all" ? undefined : statusFilter,
      created_by_staff_id: normalizeFilterValue(createdByFilter),
    }));
  };

  const handleResetFilters = () => {
    setSearchInput("");
    setTargetRoleFilter("all");
    setStatusFilter("all");
    setCreatedByFilter("");
    setFeedback(null);
    setQuery((prev) => ({
      ...prev,
      offset: 0,
      search: undefined,
      target_role: undefined,
      status: undefined,
      created_by_staff_id: undefined,
    }));
  };

  const handleCreateKey = () => {
    setFeedback(null);
    createMutation.mutate();
  };

  return (
    <Stack spacing={2}>
      <Box>
        <Typography variant="h4">{t("adminEmployeeKeys.title")}</Typography>
        <Typography variant="body2">{t("adminEmployeeKeys.subtitle")}</Typography>
      </Box>

      <Paper sx={{ p: 2 }}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems="center">
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel id="admin-employee-keys-create-role-label">
              {t("adminEmployeeKeys.create.targetRole")}
            </InputLabel>
            <Select
              labelId="admin-employee-keys-create-role-label"
              value={createRole}
              label={t("adminEmployeeKeys.create.targetRole")}
              onChange={(event) => setCreateRole(event.target.value as StaffRoleClaim)}
            >
              {CREATE_TARGET_ROLES.map((role) => (
                <MenuItem key={role} value={role}>
                  {t(`adminStaff.roles.${role}`)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            size="small"
            label={t("adminEmployeeKeys.create.ttlSeconds")}
            value={createTtlInput}
            onChange={(event) => setCreateTtlInput(event.target.value)}
            sx={{ minWidth: 200 }}
          />
          <Button variant="contained" onClick={handleCreateKey} disabled={createMutation.isPending}>
            {t("adminEmployeeKeys.create.submit")}
          </Button>
        </Stack>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems="center">
          <TextField
            size="small"
            label={t("adminEmployeeKeys.filters.search")}
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            sx={{ minWidth: 220 }}
          />
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel id="admin-employee-keys-target-role-filter-label">
              {t("adminEmployeeKeys.filters.targetRole")}
            </InputLabel>
            <Select
              labelId="admin-employee-keys-target-role-filter-label"
              value={targetRoleFilter}
              label={t("adminEmployeeKeys.filters.targetRole")}
              onChange={(event) => setTargetRoleFilter(event.target.value as StaffRoleClaim | "all")}
            >
              <MenuItem value="all">{t("adminEmployeeKeys.filters.any")}</MenuItem>
              {FILTER_TARGET_ROLES.map((role) => (
                <MenuItem key={role} value={role}>
                  {t(`adminStaff.roles.${role}`)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel id="admin-employee-keys-status-filter-label">
              {t("adminEmployeeKeys.filters.status")}
            </InputLabel>
            <Select
              labelId="admin-employee-keys-status-filter-label"
              value={statusFilter}
              label={t("adminEmployeeKeys.filters.status")}
              onChange={(event) => setStatusFilter(event.target.value as EmployeeKeyStatus | "all")}
            >
              <MenuItem value="all">{t("adminEmployeeKeys.filters.any")}</MenuItem>
              {STATUS_OPTIONS.map((status) => (
                <MenuItem key={status} value={status}>
                  {t(`adminEmployeeKeys.status.${status}`)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            size="small"
            label={t("adminEmployeeKeys.filters.createdBy")}
            value={createdByFilter}
            onChange={(event) => setCreatedByFilter(event.target.value)}
            sx={{ minWidth: 260 }}
          />
          <Button variant="contained" onClick={handleApplyFilters}>
            {t("adminEmployeeKeys.filters.apply")}
          </Button>
          <Button variant="outlined" onClick={handleResetFilters}>
            {t("adminEmployeeKeys.filters.reset")}
          </Button>
        </Stack>
      </Paper>

      {feedback ? <Alert severity={feedback.type}>{feedback.message}</Alert> : null}
      {hasErrorBanner ? <Alert severity="error">{listErrorMessage}</Alert> : null}

      <Paper>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t("adminEmployeeKeys.table.employeeKey")}</TableCell>
              <TableCell>{t("adminEmployeeKeys.table.targetRole")}</TableCell>
              <TableCell>{t("adminEmployeeKeys.table.status")}</TableCell>
              <TableCell>{t("adminEmployeeKeys.table.expiresAt")}</TableCell>
              <TableCell>{t("adminEmployeeKeys.table.usedAt")}</TableCell>
              <TableCell>{t("adminEmployeeKeys.table.revokedAt")}</TableCell>
              <TableCell>{t("adminEmployeeKeys.table.createdBy")}</TableCell>
              <TableCell>{t("adminEmployeeKeys.table.actions")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {listQuery.isLoading ? (
              <TableRow>
                <TableCell colSpan={8}>{t("adminEmployeeKeys.loading")}</TableCell>
              </TableRow>
            ) : null}

            {!listQuery.isLoading && items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8}>{t("adminEmployeeKeys.empty")}</TableCell>
              </TableRow>
            ) : null}

            {items.map((item) => (
              <TableRow key={item.key_id}>
                <TableCell>{item.employee_key}</TableCell>
                <TableCell>{t(`adminStaff.roles.${item.target_role}`)}</TableCell>
                <TableCell>{t(`adminEmployeeKeys.status.${item.status}`)}</TableCell>
                <TableCell>{formatDateTime(item.expires_at)}</TableCell>
                <TableCell>{formatDateTime(item.used_at)}</TableCell>
                <TableCell>{formatDateTime(item.revoked_at)}</TableCell>
                <TableCell>{item.created_by_staff_id}</TableCell>
                <TableCell>
                  <Button
                    variant="contained"
                    size="small"
                    disabled={!canRevokeKey(item) || revokeMutation.isPending}
                    onClick={() => revokeMutation.mutate(item.key_id)}
                  >
                    {t("adminEmployeeKeys.actions.revoke")}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={total}
          page={page}
          rowsPerPage={query.limit}
          onPageChange={(_, nextPage) => {
            setQuery((prev) => ({ ...prev, offset: nextPage * prev.limit }));
          }}
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

function normalizeFilterValue(value: string): string | undefined {
  const normalized = value.trim();
  return normalized ? normalized : undefined;
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "-";
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function resolveApiErrorMessage(error: unknown, t: (key: string, options?: Record<string, unknown>) => string): string {
  if (error instanceof ApiError) {
    const mapped = t(`adminEmployeeKeys.errors.${error.detail}`);
    if (mapped !== `adminEmployeeKeys.errors.${error.detail}`) {
      return mapped;
    }
    return t("adminEmployeeKeys.errors.validation_failed");
  }
  return t("adminEmployeeKeys.errors.validation_failed");
}

export function canRevokeKey(item: AdminEmployeeKeyListItem): boolean {
  return item.status === "active";
}
