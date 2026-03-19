import { type FormEvent, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
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
import { Link } from "react-router-dom";

import {
  createVacancy,
  getVacancy,
  listVacancies,
  updateVacancy,
  type VacancyCreateRequest,
  type VacancyListResponse,
  type VacancyResponse,
  type VacancyUpdateRequest,
} from "../../api";
import { formatDateTime, normalizeFilterValue, resolveApiErrorMessage } from "./adminUtils";

type VacancyDraft = {
  title: string;
  description: string;
  department: string;
  status: string;
  hiringManagerLogin: string;
};

type FeedbackState = {
  type: "success" | "error";
  message: string;
};

const EMPTY_CREATE_DRAFT: VacancyDraft = {
  title: "",
  description: "",
  department: "",
  status: "open",
  hiringManagerLogin: "",
};

/**
 * Admin vacancy console for CRUD lifecycle operations and pipeline handoff.
 */
export function AdminVacanciesPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [searchInput, setSearchInput] = useState("");
  const [departmentInput, setDepartmentInput] = useState("");
  const [statusInput, setStatusInput] = useState("");
  const [query, setQuery] = useState({
    search: "",
    department: "",
    status: "",
  });
  const [selectedVacancyId, setSelectedVacancyId] = useState("");
  const [createDraft, setCreateDraft] = useState<VacancyDraft>(EMPTY_CREATE_DRAFT);
  const [editDraft, setEditDraft] = useState<VacancyDraft>(EMPTY_CREATE_DRAFT);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  const listQuery = useQuery({
    queryKey: ["admin-vacancies-list"],
    queryFn: () => listVacancies(),
  });

  const selectedVacancyQuery = useQuery({
    queryKey: ["admin-vacancy-detail", selectedVacancyId],
    queryFn: () => getVacancy(selectedVacancyId),
    enabled: Boolean(selectedVacancyId),
  });

  const createMutation = useMutation({
    mutationFn: (payload: VacancyCreateRequest) => createVacancy(payload),
    onSuccess: (result) => {
      setFeedback({
        type: "success",
        message: t("adminVacancies.createSuccess", { vacancyId: result.vacancy_id }),
      });
      setSelectedVacancyId(String(result.vacancy_id));
      setCreateDraft(EMPTY_CREATE_DRAFT);
      void queryClient.invalidateQueries({ queryKey: ["admin-vacancies-list"] });
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveApiErrorMessage(error, t, "adminVacancies") });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      vacancyId,
      payload,
    }: {
      vacancyId: string;
      payload: VacancyUpdateRequest;
    }) => updateVacancy(vacancyId, payload),
    onSuccess: (result) => {
      setFeedback({
        type: "success",
        message: t("adminVacancies.updateSuccess", { vacancyId: result.vacancy_id }),
      });
      void queryClient.invalidateQueries({ queryKey: ["admin-vacancies-list"] });
      void queryClient.invalidateQueries({ queryKey: ["admin-vacancy-detail"] });
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveApiErrorMessage(error, t, "adminVacancies") });
    },
  });

  useEffect(() => {
    const vacancy = selectedVacancyQuery.data;
    if (!vacancy) {
      return;
    }
    setEditDraft(toDraft(vacancy));
  }, [selectedVacancyQuery.data]);

  const items = useMemo(() => listQuery.data?.items ?? [], [listQuery.data?.items]);
  const filteredItems = useMemo(() => filterVacancies(items, query), [items, query]);
  const selectedVacancy = selectedVacancyQuery.data ?? null;
  const listErrorMessage = useMemo(() => {
    if (!listQuery.error) {
      return "";
    }
    return resolveApiErrorMessage(listQuery.error, t, "adminVacancies");
  }, [listQuery.error, t]);

  const handleApplyFilters = () => {
    setFeedback(null);
    setQuery({
      search: normalizeFilterValue(searchInput) ?? "",
      department: normalizeFilterValue(departmentInput) ?? "",
      status: normalizeFilterValue(statusInput) ?? "",
    });
  };

  const handleResetFilters = () => {
    setSearchInput("");
    setDepartmentInput("");
    setStatusInput("");
    setFeedback(null);
    setQuery({
      search: "",
      department: "",
      status: "",
    });
  };

  const handleCreateSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFeedback(null);
    createMutation.mutate(buildCreatePayload(createDraft));
  };

  const handleUpdateSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedVacancyId) {
      setFeedback({
        type: "error",
        message: t("adminVacancies.errors.selectVacancy"),
      });
      return;
    }
    setFeedback(null);
    updateMutation.mutate({
      vacancyId: selectedVacancyId,
      payload: buildUpdatePayload(editDraft),
    });
  };

  return (
    <Stack spacing={2}>
      <Box>
        <Typography variant="h4">{t("adminVacancies.title")}</Typography>
        <Typography variant="body2">{t("adminVacancies.subtitle")}</Typography>
      </Box>

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2} component="form" onSubmit={handleCreateSubmit}>
          <Typography variant="h6">{t("adminVacancies.createSectionTitle")}</Typography>
          <TextField
            required
            fullWidth
            label={t("adminVacancies.fields.title")}
            value={createDraft.title}
            onChange={(event) => setCreateDraft((prev) => ({ ...prev, title: event.target.value }))}
          />
          <TextField
            required
            multiline
            minRows={4}
            fullWidth
            label={t("adminVacancies.fields.description")}
            value={createDraft.description}
            onChange={(event) =>
              setCreateDraft((prev) => ({ ...prev, description: event.target.value }))
            }
          />
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField
              required
              fullWidth
              label={t("adminVacancies.fields.department")}
              value={createDraft.department}
              onChange={(event) =>
                setCreateDraft((prev) => ({ ...prev, department: event.target.value }))
              }
            />
            <TextField
              required
              fullWidth
              label={t("adminVacancies.fields.status")}
              value={createDraft.status}
              onChange={(event) => setCreateDraft((prev) => ({ ...prev, status: event.target.value }))}
            />
            <TextField
              fullWidth
              label={t("adminVacancies.fields.hiringManagerLogin")}
              value={createDraft.hiringManagerLogin}
              onChange={(event) =>
                setCreateDraft((prev) => ({ ...prev, hiringManagerLogin: event.target.value }))
              }
            />
          </Stack>
          <Stack direction="row" spacing={1.5}>
            <Button type="submit" variant="contained" disabled={createMutation.isPending}>
              {createMutation.isPending
                ? t("adminVacancies.createPending")
                : t("adminVacancies.createAction")}
            </Button>
          </Stack>
        </Stack>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Typography variant="h6">{t("adminVacancies.filters.title")}</Typography>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField
              size="small"
              label={t("adminVacancies.filters.search")}
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              sx={{ minWidth: 220 }}
            />
            <TextField
              size="small"
              label={t("adminVacancies.filters.department")}
              value={departmentInput}
              onChange={(event) => setDepartmentInput(event.target.value)}
              sx={{ minWidth: 220 }}
            />
            <TextField
              size="small"
              label={t("adminVacancies.filters.status")}
              value={statusInput}
              onChange={(event) => setStatusInput(event.target.value)}
              sx={{ minWidth: 180 }}
            />
            <Button variant="contained" onClick={handleApplyFilters}>
              {t("adminVacancies.filters.apply")}
            </Button>
            <Button variant="outlined" onClick={handleResetFilters}>
              {t("adminVacancies.filters.reset")}
            </Button>
          </Stack>
        </Stack>
      </Paper>

      {feedback ? <Alert severity={feedback.type}>{feedback.message}</Alert> : null}
      {listQuery.error ? <Alert severity="error">{listErrorMessage}</Alert> : null}

      <Paper>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t("adminVacancies.table.title")}</TableCell>
              <TableCell>{t("adminVacancies.table.department")}</TableCell>
              <TableCell>{t("adminVacancies.table.status")}</TableCell>
              <TableCell>{t("adminVacancies.table.hiringManager")}</TableCell>
              <TableCell>{t("adminVacancies.table.updatedAt")}</TableCell>
              <TableCell>{t("adminVacancies.table.actions")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {listQuery.isLoading ? (
              <TableRow>
                <TableCell colSpan={6}>{t("adminVacancies.loading")}</TableCell>
              </TableRow>
            ) : null}
            {!listQuery.isLoading && filteredItems.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6}>{t("adminVacancies.empty")}</TableCell>
              </TableRow>
            ) : null}
            {filteredItems.map((item) => (
              <TableRow key={item.vacancy_id}>
                <TableCell>
                  <Stack spacing={0.25}>
                    <Typography variant="body2" fontWeight={600}>
                      {item.title}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {item.description.slice(0, 120)}
                    </Typography>
                  </Stack>
                </TableCell>
                <TableCell>{item.department}</TableCell>
                <TableCell>{item.status}</TableCell>
                <TableCell>
                  <Stack spacing={0.25}>
                    <Typography variant="body2">{item.hiring_manager_login || t("adminVacancies.notAvailable")}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {item.hiring_manager_staff_id || t("adminVacancies.notAvailable")}
                    </Typography>
                  </Stack>
                </TableCell>
                <TableCell>{formatDateTime(item.updated_at, t("adminVacancies.notAvailable"))}</TableCell>
                <TableCell>
                  <Stack direction="row" spacing={1}>
                    <Button
                      size="small"
                      variant="contained"
                      onClick={() => setSelectedVacancyId(String(item.vacancy_id))}
                    >
                      {t("adminVacancies.actions.edit")}
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      component={Link}
                      to={`/admin/pipeline?vacancyId=${encodeURIComponent(String(item.vacancy_id))}`}
                    >
                      {t("adminVacancies.actions.pipeline")}
                    </Button>
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Typography variant="h6">{t("adminVacancies.editSectionTitle")}</Typography>
          {!selectedVacancyId ? (
            <Alert severity="info">{t("adminVacancies.selectPrompt")}</Alert>
          ) : selectedVacancyQuery.isLoading ? (
            <Alert severity="info">{t("adminVacancies.loadingSelected")}</Alert>
          ) : selectedVacancyQuery.isError ? (
            <Alert severity="error">
              {resolveApiErrorMessage(selectedVacancyQuery.error, t, "adminVacancies")}
            </Alert>
          ) : selectedVacancy ? (
            <Stack spacing={2} component="form" onSubmit={handleUpdateSubmit}>
              <Stack spacing={0.5}>
                <Typography variant="body2" fontWeight={600}>
                  {t("adminVacancies.selectedSummary", {
                    title: selectedVacancy.title,
                    vacancyId: selectedVacancy.vacancy_id,
                  })}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("adminVacancies.detail.department")}: {selectedVacancy.department}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("adminVacancies.detail.status")}: {selectedVacancy.status}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("adminVacancies.detail.hiringManagerLogin")}:{" "}
                  {selectedVacancy.hiring_manager_login || t("adminVacancies.notAvailable")}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("adminVacancies.detail.hiringManagerStaffId")}:{" "}
                  {selectedVacancy.hiring_manager_staff_id || t("adminVacancies.notAvailable")}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("adminVacancies.detail.createdAt")}:{" "}
                  {formatDateTime(selectedVacancy.created_at, t("adminVacancies.notAvailable"))}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("adminVacancies.detail.updatedAt")}:{" "}
                  {formatDateTime(selectedVacancy.updated_at, t("adminVacancies.notAvailable"))}
                </Typography>
              </Stack>
              <TextField
                required
                fullWidth
                label={t("adminVacancies.fields.title")}
                value={editDraft.title}
                onChange={(event) => setEditDraft((prev) => ({ ...prev, title: event.target.value }))}
              />
              <TextField
                required
                multiline
                minRows={4}
                fullWidth
                label={t("adminVacancies.fields.description")}
                value={editDraft.description}
                onChange={(event) =>
                  setEditDraft((prev) => ({ ...prev, description: event.target.value }))
                }
              />
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField
                  required
                  fullWidth
                  label={t("adminVacancies.fields.department")}
                  value={editDraft.department}
                  onChange={(event) =>
                    setEditDraft((prev) => ({ ...prev, department: event.target.value }))
                  }
                />
                <TextField
                  required
                  fullWidth
                  label={t("adminVacancies.fields.status")}
                  value={editDraft.status}
                  onChange={(event) => setEditDraft((prev) => ({ ...prev, status: event.target.value }))}
                />
                <TextField
                  fullWidth
                  label={t("adminVacancies.fields.hiringManagerLogin")}
                  value={editDraft.hiringManagerLogin}
                  onChange={(event) =>
                    setEditDraft((prev) => ({ ...prev, hiringManagerLogin: event.target.value }))
                  }
                />
              </Stack>
              <Stack direction="row" spacing={1.5}>
                <Button type="submit" variant="contained" disabled={updateMutation.isPending}>
                  {updateMutation.isPending
                    ? t("adminVacancies.updatePending")
                    : t("adminVacancies.updateAction")}
                </Button>
              </Stack>
            </Stack>
          ) : (
            <Alert severity="warning">{t("adminVacancies.errors.selectVacancy")}</Alert>
          )}
        </Stack>
      </Paper>
    </Stack>
  );
}

function buildCreatePayload(draft: VacancyDraft): VacancyCreateRequest {
  return {
    title: draft.title.trim(),
    description: draft.description.trim(),
    department: draft.department.trim(),
    status: draft.status.trim() || "open",
    hiring_manager_login: normalizeNullableString(draft.hiringManagerLogin),
  };
}

function buildUpdatePayload(draft: VacancyDraft): VacancyUpdateRequest {
  return {
    title: draft.title.trim(),
    description: draft.description.trim(),
    department: draft.department.trim(),
    status: draft.status.trim(),
    hiring_manager_login: normalizeNullableString(draft.hiringManagerLogin),
  };
}

function toDraft(vacancy: VacancyResponse): VacancyDraft {
  return {
    title: vacancy.title,
    description: vacancy.description,
    department: vacancy.department,
    status: vacancy.status,
    hiringManagerLogin: vacancy.hiring_manager_login ?? "",
  };
}

function normalizeNullableString(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function filterVacancies(items: VacancyListResponse["items"], query: {
  search: string;
  department: string;
  status: string;
}): VacancyListResponse["items"] {
  const search = query.search.trim().toLowerCase();
  const department = query.department.trim().toLowerCase();
  const status = query.status.trim().toLowerCase();
  return items.filter((item) => {
    const searchMatch =
      !search
      || [item.title, item.description, item.department, item.status, item.hiring_manager_login, item.hiring_manager_staff_id]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(search));
    const departmentMatch = !department || item.department.toLowerCase().includes(department);
    const statusMatch = !status || item.status.toLowerCase().includes(status);
    return searchMatch && departmentMatch && statusMatch;
  });
}
