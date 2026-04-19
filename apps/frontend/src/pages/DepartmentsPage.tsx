import { useMemo, useState } from "react";
import {
  Alert,
  Box,
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
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import {
  ApiError,
  createDepartment,
  listDepartments,
  updateDepartment,
  type DepartmentListQuery,
  type DepartmentListResponse,
} from "../api";
import { readAuthSession } from "../app/auth/session";
import { useSentryRouteTags } from "../app/observability/sentry";
import { formatDateTime } from "./admin/adminUtils";

const DEFAULT_LIMIT = 20;

type FeedbackState = {
  type: "success" | "error";
  message: string;
};

type DepartmentListItem = DepartmentListResponse["items"][number];

/**
 * Shared departments directory page with read-only access for most staff roles.
 */
export function DepartmentsPage() {
  const { t } = useTranslation();
  useSentryRouteTags("/departments");
  const session = readAuthSession();
  const accessToken = session.accessToken;
  const canEdit = session.role === "admin" || session.role === "leader";
  const queryClient = useQueryClient();

  const [searchInput, setSearchInput] = useState("");
  const [query, setQuery] = useState<DepartmentListQuery>({
    limit: DEFAULT_LIMIT,
    offset: 0,
  });
  const [createName, setCreateName] = useState("");
  const [selectedDepartment, setSelectedDepartment] = useState<DepartmentListItem | null>(null);
  const [editName, setEditName] = useState("");
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  const listQuery = useQuery({
    queryKey: ["departments", accessToken, query],
    queryFn: () => listDepartments(accessToken!, query),
    enabled: Boolean(accessToken),
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: () => createDepartment(accessToken!, { name: createName }),
    onSuccess: () => {
      setCreateName("");
      setFeedback({ type: "success", message: t("departments.create.success") });
      void queryClient.invalidateQueries({ queryKey: ["departments"] });
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveDepartmentsError(error, t) });
    },
  });

  const updateMutation = useMutation({
    mutationFn: () =>
      updateDepartment(accessToken!, selectedDepartment!.department_id, { name: editName }),
    onSuccess: () => {
      setFeedback({ type: "success", message: t("departments.edit.success") });
      setSelectedDepartment(null);
      setEditName("");
      void queryClient.invalidateQueries({ queryKey: ["departments"] });
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveDepartmentsError(error, t) });
    },
  });

  const total = listQuery.data?.total ?? 0;
  const limit = query.limit ?? DEFAULT_LIMIT;
  const offset = query.offset ?? 0;
  const page = Math.floor(offset / limit);

  const listErrorMessage = useMemo(() => {
    if (!listQuery.error) {
      return "";
    }
    return resolveDepartmentsError(listQuery.error, t);
  }, [listQuery.error, t]);

  const handleApplyFilters = () => {
    setFeedback(null);
    setQuery((prev) => ({
      ...prev,
      offset: 0,
      search: normalizeFilterValue(searchInput),
    }));
  };

  const handleResetFilters = () => {
    setSearchInput("");
    setFeedback(null);
    setQuery((prev) => ({
      ...prev,
      offset: 0,
      search: undefined,
    }));
  };

  const handleCreate = () => {
    setFeedback(null);
    createMutation.mutate();
  };

  const handleSelectForEdit = (item: DepartmentListItem) => {
    setFeedback(null);
    setSelectedDepartment(item);
    setEditName(item.name);
  };

  const handleCancelEdit = () => {
    setSelectedDepartment(null);
    setEditName("");
  };

  if (!accessToken) {
    return (
      <Stack spacing={2}>
        <Box>
          <Typography variant="h4">{t("departments.title")}</Typography>
          <Typography variant="body2">{t("departments.subtitle")}</Typography>
        </Box>
        <Alert severity="warning">{t("departments.authRequired")}</Alert>
      </Stack>
    );
  }

  return (
    <Stack spacing={2}>
      <Box>
        <Typography variant="h4">{t("departments.title")}</Typography>
        <Typography variant="body2">{t("departments.subtitle")}</Typography>
      </Box>

      {!canEdit ? <Alert severity="info">{t("departments.readOnly")}</Alert> : null}

      {canEdit ? (
        <Paper sx={{ p: 2 }}>
          <Stack spacing={1.5}>
            <Typography variant="h6">{t("departments.create.title")}</Typography>
            <Typography variant="body2" color="text.secondary">
              {t("departments.create.subtitle")}
            </Typography>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems="center">
              <TextField
                fullWidth
                size="small"
                label={t("departments.fields.name")}
                value={createName}
                onChange={(event) => setCreateName(event.target.value)}
              />
              <Button
                variant="contained"
                onClick={handleCreate}
                disabled={createMutation.isPending || !createName.trim()}
              >
                {t("departments.create.action")}
              </Button>
            </Stack>
          </Stack>
        </Paper>
      ) : null}

      {selectedDepartment && canEdit ? (
        <Paper sx={{ p: 2 }}>
          <Stack spacing={1.5}>
            <Typography variant="h6">{t("departments.edit.title")}</Typography>
            <Typography variant="body2" color="text.secondary">
              {t("departments.edit.subtitle")}
            </Typography>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems="center">
              <TextField
                fullWidth
                size="small"
                label={t("departments.fields.name")}
                value={editName}
                onChange={(event) => setEditName(event.target.value)}
              />
              <Button
                variant="contained"
                onClick={() => updateMutation.mutate()}
                disabled={updateMutation.isPending || !editName.trim()}
              >
                {t("departments.edit.action")}
              </Button>
              <Button variant="outlined" onClick={handleCancelEdit}>
                {t("departments.edit.cancel")}
              </Button>
            </Stack>
          </Stack>
        </Paper>
      ) : null}

      <Paper sx={{ p: 2 }}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems="center">
          <TextField
            size="small"
            label={t("departments.filters.search")}
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            sx={{ minWidth: 240 }}
          />
          <Button variant="contained" onClick={handleApplyFilters}>
            {t("departments.filters.apply")}
          </Button>
          <Button variant="outlined" onClick={handleResetFilters}>
            {t("departments.filters.reset")}
          </Button>
        </Stack>
      </Paper>

      {feedback ? <Alert severity={feedback.type}>{feedback.message}</Alert> : null}
      {listQuery.isError ? <Alert severity="error">{listErrorMessage}</Alert> : null}

      <Paper>
        {listQuery.isLoading ? (
          <Stack spacing={1} alignItems="center" sx={{ py: 4 }}>
            <CircularProgress size={28} />
            <Typography variant="body2">{t("departments.loading")}</Typography>
          </Stack>
        ) : (
          <>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t("departments.table.name")}</TableCell>
                  <TableCell>{t("departments.table.created")}</TableCell>
                  <TableCell>{t("departments.table.updated")}</TableCell>
                  <TableCell align="right">{t("departments.table.actions")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {listQuery.data?.items?.length ? (
                  listQuery.data.items.map((item) => (
                    <TableRow key={item.department_id} hover>
                      <TableCell>{item.name}</TableCell>
                      <TableCell>
                        {formatDateTime(item.created_at, t("departments.emptyValue"))}
                      </TableCell>
                      <TableCell>
                        {formatDateTime(item.updated_at, t("departments.emptyValue"))}
                      </TableCell>
                      <TableCell align="right">
                        {canEdit ? (
                          <Button size="small" onClick={() => handleSelectForEdit(item)}>
                            {t("departments.actions.edit")}
                          </Button>
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            {t("departments.actions.view")}
                          </Typography>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={4}>
                      <Typography variant="body2" color="text.secondary">
                        {t("departments.empty")}
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
            <TablePagination
              component="div"
              count={total}
              page={page}
              rowsPerPage={limit}
              onPageChange={(_, nextPage) =>
                setQuery((prev) => ({
                  ...prev,
                  offset: nextPage * (prev.limit ?? DEFAULT_LIMIT),
                }))
              }
              onRowsPerPageChange={(event) => {
                const nextLimit = Number.parseInt(event.target.value, 10) || DEFAULT_LIMIT;
                setQuery({
                  limit: nextLimit,
                  offset: 0,
                  search: query.search,
                });
              }}
              rowsPerPageOptions={[10, 20, 50]}
            />
          </>
        )}
      </Paper>
    </Stack>
  );
}

function normalizeFilterValue(value: string): string | undefined {
  const normalized = value.trim();
  return normalized ? normalized : undefined;
}

function resolveDepartmentsError(error: unknown, t: (key: string) => string): string {
  if (isApiError(error)) {
    const detailKey = `departments.errors.${error.detail}`;
    const mappedDetail = t(detailKey);
    if (mappedDetail !== detailKey) {
      return mappedDetail;
    }
    const statusKey = `departments.errors.http_${error.status}`;
    const mappedStatus = t(statusKey);
    if (mappedStatus !== statusKey) {
      return mappedStatus;
    }
  }
  return t("departments.errors.generic");
}

function isApiError(error: unknown): error is ApiError {
  return Boolean(error && typeof error === "object" && "status" in error && "detail" in error);
}
