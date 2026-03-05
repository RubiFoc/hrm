import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Switch,
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
  listAdminStaff,
  updateAdminStaff,
  type AdminStaffListItem,
  type AdminStaffListQuery,
  type AdminStaffUpdateRequest,
  type StaffRoleClaim,
} from "../api";

const STAFF_ROLES: StaffRoleClaim[] = [
  "admin",
  "hr",
  "manager",
  "employee",
  "leader",
  "accountant",
];

type RowDraft = {
  role: StaffRoleClaim;
  is_active: boolean;
};

type StatusFilter = "all" | "active" | "inactive";

type FeedbackState = {
  type: "success" | "error";
  message: string;
};

const DEFAULT_LIMIT = 20;

export function AdminStaffManagementPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [searchInput, setSearchInput] = useState("");
  const [roleFilter, setRoleFilter] = useState<StaffRoleClaim | "all">("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [query, setQuery] = useState<AdminStaffListQuery>({
    limit: DEFAULT_LIMIT,
    offset: 0,
  });
  const [rowDrafts, setRowDrafts] = useState<Record<string, RowDraft>>({});
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  const staffListQuery = useQuery({
    queryKey: ["admin-staff-list", query],
    queryFn: () => listAdminStaff(query),
  });

  const updateMutation = useMutation({
    mutationFn: ({ staffId, payload }: { staffId: string; payload: AdminStaffUpdateRequest }) =>
      updateAdminStaff(staffId, payload),
    onSuccess: () => {
      setFeedback({ type: "success", message: t("adminStaff.updateSuccess") });
      void queryClient.invalidateQueries({ queryKey: ["admin-staff-list"] });
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveApiErrorMessage(error, t) });
    },
  });

  const items = staffListQuery.data?.items ?? [];
  const total = staffListQuery.data?.total ?? 0;
  const page = Math.floor(query.offset / query.limit);

  const hasErrorBanner = Boolean(staffListQuery.error) && !feedback;

  const listErrorMessage = useMemo(() => {
    if (!staffListQuery.error) {
      return "";
    }
    return resolveApiErrorMessage(staffListQuery.error, t);
  }, [staffListQuery.error, t]);

  const handleApplyFilters = () => {
    setFeedback(null);
    setQuery((prev) => ({
      ...prev,
      offset: 0,
      search: normalizeFilterValue(searchInput),
      role: roleFilter === "all" ? undefined : roleFilter,
      is_active: resolveStatusFilter(statusFilter),
    }));
  };

  const handleResetFilters = () => {
    setSearchInput("");
    setRoleFilter("all");
    setStatusFilter("all");
    setFeedback(null);
    setQuery((prev) => ({
      ...prev,
      offset: 0,
      search: undefined,
      role: undefined,
      is_active: undefined,
    }));
  };

  const handleDraftRoleChange = (staffId: string, role: StaffRoleClaim, currentIsActive: boolean) => {
    setRowDrafts((prev) => ({
      ...prev,
      [staffId]: {
        role,
        is_active: prev[staffId]?.is_active ?? currentIsActive,
      },
    }));
  };

  const handleDraftActiveChange = (staffId: string, isActive: boolean, currentRole: StaffRoleClaim) => {
    setRowDrafts((prev) => ({
      ...prev,
      [staffId]: {
        role: prev[staffId]?.role ?? currentRole,
        is_active: isActive,
      },
    }));
  };

  const handleSaveRow = (item: AdminStaffListItem) => {
    const draft = rowDrafts[item.staff_id] ?? {
      role: item.role as StaffRoleClaim,
      is_active: item.is_active,
    };
    const payload: AdminStaffUpdateRequest = {};
    if (draft.role !== item.role) {
      payload.role = draft.role;
    }
    if (draft.is_active !== item.is_active) {
      payload.is_active = draft.is_active;
    }

    if (!payload.role && payload.is_active === undefined) {
      return;
    }

    setFeedback(null);
    updateMutation.mutate({ staffId: item.staff_id, payload });
  };

  return (
    <Stack spacing={2}>
      <Box>
        <Typography variant="h4">{t("adminStaff.title")}</Typography>
        <Typography variant="body2">{t("adminStaff.subtitle")}</Typography>
      </Box>

      <Paper sx={{ p: 2 }}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems="center">
          <TextField
            size="small"
            label={t("adminStaff.filters.search")}
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            sx={{ minWidth: 220 }}
          />
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel id="admin-staff-role-filter-label">
              {t("adminStaff.filters.role")}
            </InputLabel>
            <Select
              labelId="admin-staff-role-filter-label"
              value={roleFilter}
              label={t("adminStaff.filters.role")}
              onChange={(event) => setRoleFilter(event.target.value as StaffRoleClaim | "all")}
            >
              <MenuItem value="all">{t("adminStaff.filters.any")}</MenuItem>
              {STAFF_ROLES.map((role) => (
                <MenuItem key={role} value={role}>
                  {t(`adminStaff.roles.${role}`)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel id="admin-staff-active-filter-label">
              {t("adminStaff.filters.isActive")}
            </InputLabel>
            <Select
              labelId="admin-staff-active-filter-label"
              value={statusFilter}
              label={t("adminStaff.filters.isActive")}
              onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
            >
              <MenuItem value="all">{t("adminStaff.filters.any")}</MenuItem>
              <MenuItem value="active">{t("adminStaff.filters.active")}</MenuItem>
              <MenuItem value="inactive">{t("adminStaff.filters.inactive")}</MenuItem>
            </Select>
          </FormControl>
          <Button variant="contained" onClick={handleApplyFilters}>
            {t("adminStaff.filters.apply")}
          </Button>
          <Button variant="outlined" onClick={handleResetFilters}>
            {t("adminStaff.filters.reset")}
          </Button>
        </Stack>
      </Paper>

      {feedback ? <Alert severity={feedback.type}>{feedback.message}</Alert> : null}
      {hasErrorBanner ? <Alert severity="error">{listErrorMessage}</Alert> : null}

      <Paper>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t("adminStaff.table.login")}</TableCell>
              <TableCell>{t("adminStaff.table.email")}</TableCell>
              <TableCell>{t("adminStaff.table.role")}</TableCell>
              <TableCell>{t("adminStaff.table.active")}</TableCell>
              <TableCell>{t("adminStaff.table.actions")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {staffListQuery.isLoading ? (
              <TableRow>
                <TableCell colSpan={5}>{t("adminStaff.loading")}</TableCell>
              </TableRow>
            ) : null}

            {!staffListQuery.isLoading && items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5}>{t("adminStaff.empty")}</TableCell>
              </TableRow>
            ) : null}

            {items.map((item) => {
              const draft = rowDrafts[item.staff_id] ?? {
                role: item.role as StaffRoleClaim,
                is_active: item.is_active,
              };
              const changed = draft.role !== item.role || draft.is_active !== item.is_active;

              return (
                <TableRow key={item.staff_id}>
                  <TableCell>{item.login}</TableCell>
                  <TableCell>{item.email}</TableCell>
                  <TableCell>
                    <FormControl size="small" fullWidth>
                      <Select
                        value={draft.role}
                        onChange={(event) =>
                          handleDraftRoleChange(
                            item.staff_id,
                            event.target.value as StaffRoleClaim,
                            draft.is_active,
                          )
                        }
                      >
                        {STAFF_ROLES.map((role) => (
                          <MenuItem key={role} value={role}>
                            {t(`adminStaff.roles.${role}`)}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </TableCell>
                  <TableCell>
                    <FormControlLabel
                      label={draft.is_active ? t("adminStaff.status.active") : t("adminStaff.status.inactive")}
                      control={
                        <Switch
                          checked={draft.is_active}
                          onChange={(event) =>
                            handleDraftActiveChange(item.staff_id, event.target.checked, draft.role)
                          }
                        />
                      }
                    />
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="contained"
                      size="small"
                      disabled={!changed || updateMutation.isPending}
                      onClick={() => handleSaveRow(item)}
                    >
                      {t("adminStaff.actions.save")}
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
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

function resolveStatusFilter(filter: StatusFilter): boolean | undefined {
  if (filter === "active") {
    return true;
  }
  if (filter === "inactive") {
    return false;
  }
  return undefined;
}

function resolveApiErrorMessage(error: unknown, t: (key: string) => string): string {
  if (error instanceof ApiError) {
    const mapped = t(`adminStaff.errors.${error.detail}`);
    if (mapped !== `adminStaff.errors.${error.detail}`) {
      return mapped;
    }
    return t("adminStaff.errors.validation_failed");
  }
  return t("adminStaff.errors.validation_failed");
}
