import { type FormEvent, useEffect, useMemo, useState } from "react";
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
  createCandidateProfile,
  getCandidateProfile,
  listCandidateProfiles,
  updateCandidateProfile,
  type CandidateCreateRequest,
  type CandidateListQuery,
  type CandidateResponse,
  type CandidateUpdateRequest,
} from "../../api";
import {
  formatDateTime,
  normalizeFilterValue,
  resolveApiErrorMessage,
} from "./adminUtils";

const DEFAULT_LIMIT = 20;
type AnalysisReadyFilter = "all" | "ready" | "not-ready";

type CandidateDraft = {
  ownerSubjectId: string;
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  location: string;
  currentTitle: string;
  extraData: string;
};

type FeedbackState = {
  type: "success" | "error";
  message: string;
};

const EMPTY_DRAFT: CandidateDraft = {
  ownerSubjectId: "",
  firstName: "",
  lastName: "",
  email: "",
  phone: "",
  location: "",
  currentTitle: "",
  extraData: "{}",
};

/**
 * Admin candidate console for profile review, creation, and edits.
 */
export function AdminCandidatesPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [searchInput, setSearchInput] = useState("");
  const [locationInput, setLocationInput] = useState("");
  const [currentTitleInput, setCurrentTitleInput] = useState("");
  const [skillInput, setSkillInput] = useState("");
  const [analysisReadyFilter, setAnalysisReadyFilter] = useState<AnalysisReadyFilter>("all");
  const [minYearsExperienceInput, setMinYearsExperienceInput] = useState("");
  const [query, setQuery] = useState<CandidateListQuery>({
    limit: DEFAULT_LIMIT,
    offset: 0,
  });
  const [selectedCandidateId, setSelectedCandidateId] = useState("");
  const [createDraft, setCreateDraft] = useState<CandidateDraft>(EMPTY_DRAFT);
  const [editDraft, setEditDraft] = useState<CandidateDraft>(EMPTY_DRAFT);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  const listQuery = useQuery({
    queryKey: ["admin-candidates-list", query],
    queryFn: () => listCandidateProfiles(query),
  });

  const selectedCandidateQuery = useQuery({
    queryKey: ["admin-candidate-detail", selectedCandidateId],
    queryFn: () => getCandidateProfile(selectedCandidateId),
    enabled: Boolean(selectedCandidateId),
  });

  const createMutation = useMutation({
    mutationFn: (payload: CandidateCreateRequest) => createCandidateProfile(payload),
    onSuccess: (result) => {
      setFeedback({
        type: "success",
        message: t("adminCandidates.createSuccess", {
          candidateId: result.candidate_id,
        }),
      });
      setSelectedCandidateId(String(result.candidate_id));
      setCreateDraft(EMPTY_DRAFT);
      void queryClient.invalidateQueries({ queryKey: ["admin-candidates-list"] });
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveApiErrorMessage(error, t, "adminCandidates") });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      candidateId,
      payload,
    }: {
      candidateId: string;
      payload: CandidateUpdateRequest;
    }) => updateCandidateProfile(candidateId, payload),
    onSuccess: (result) => {
      setFeedback({
        type: "success",
        message: t("adminCandidates.updateSuccess", {
          candidateId: result.candidate_id,
        }),
      });
      void queryClient.invalidateQueries({ queryKey: ["admin-candidates-list"] });
      void queryClient.invalidateQueries({ queryKey: ["admin-candidate-detail"] });
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveApiErrorMessage(error, t, "adminCandidates") });
    },
  });

  useEffect(() => {
    const candidate = selectedCandidateQuery.data;
    if (!candidate) {
      return;
    }
    setEditDraft(toDraft(candidate));
  }, [selectedCandidateQuery.data]);

  const items = listQuery.data?.items ?? [];
  const total = listQuery.data?.total ?? 0;
  const page = Math.floor(query.offset / query.limit);
  const selectedCandidate = selectedCandidateQuery.data ?? null;
  const listErrorMessage = useMemo(() => {
    if (!listQuery.error) {
      return "";
    }
    return resolveApiErrorMessage(listQuery.error, t, "adminCandidates");
  }, [listQuery.error, t]);

  const applyFilters = () => {
    setFeedback(null);
    setQuery((prev) => ({
      ...prev,
      offset: 0,
      search: normalizeFilterValue(searchInput),
      location: normalizeFilterValue(locationInput),
      currentTitle: normalizeFilterValue(currentTitleInput),
      skill: normalizeFilterValue(skillInput),
      analysisReady:
        analysisReadyFilter === "all" ? undefined : analysisReadyFilter === "ready",
      minYearsExperience: normalizeYearsExperience(minYearsExperienceInput),
    }));
  };

  const resetFilters = () => {
    setSearchInput("");
    setLocationInput("");
    setCurrentTitleInput("");
    setSkillInput("");
    setAnalysisReadyFilter("all");
    setMinYearsExperienceInput("");
    setFeedback(null);
    setQuery({
      limit: DEFAULT_LIMIT,
      offset: 0,
    });
  };

  const handleCreateSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFeedback(null);
    try {
      createMutation.mutate(buildCreatePayload(createDraft));
    } catch (error) {
      if (error instanceof Error && error.message === "invalid_extra_data") {
        setFeedback({
          type: "error",
          message: t("adminCandidates.errors.invalidExtraData"),
        });
        return;
      }
      throw error;
    }
  };

  const handleUpdateSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedCandidateId) {
      setFeedback({
        type: "error",
        message: t("adminCandidates.errors.selectCandidate"),
      });
      return;
    }
    setFeedback(null);
    try {
      updateMutation.mutate({
        candidateId: selectedCandidateId,
        payload: buildUpdatePayload(editDraft),
      });
    } catch (error) {
      if (error instanceof Error && error.message === "invalid_extra_data") {
        setFeedback({
          type: "error",
          message: t("adminCandidates.errors.invalidExtraData"),
        });
        return;
      }
      throw error;
    }
  };

  return (
    <Stack spacing={2}>
      <Box>
        <Typography variant="h4">{t("adminCandidates.title")}</Typography>
        <Typography variant="body2">{t("adminCandidates.subtitle")}</Typography>
      </Box>

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2} component="form" onSubmit={handleCreateSubmit}>
          <Typography variant="h6">{t("adminCandidates.createSectionTitle")}</Typography>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField
              required
              fullWidth
              label={t("adminCandidates.fields.firstName")}
              value={createDraft.firstName}
              onChange={(event) => setCreateDraft((prev) => ({ ...prev, firstName: event.target.value }))}
            />
            <TextField
              required
              fullWidth
              label={t("adminCandidates.fields.lastName")}
              value={createDraft.lastName}
              onChange={(event) => setCreateDraft((prev) => ({ ...prev, lastName: event.target.value }))}
            />
          </Stack>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField
              required
              fullWidth
              label={t("adminCandidates.fields.email")}
              value={createDraft.email}
              onChange={(event) => setCreateDraft((prev) => ({ ...prev, email: event.target.value }))}
            />
            <TextField
              fullWidth
              label={t("adminCandidates.fields.ownerSubjectId")}
              value={createDraft.ownerSubjectId}
              onChange={(event) =>
                setCreateDraft((prev) => ({ ...prev, ownerSubjectId: event.target.value }))
              }
            />
          </Stack>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField
              fullWidth
              label={t("adminCandidates.fields.phone")}
              value={createDraft.phone}
              onChange={(event) => setCreateDraft((prev) => ({ ...prev, phone: event.target.value }))}
            />
            <TextField
              fullWidth
              label={t("adminCandidates.fields.location")}
              value={createDraft.location}
              onChange={(event) =>
                setCreateDraft((prev) => ({ ...prev, location: event.target.value }))
              }
            />
            <TextField
              fullWidth
              label={t("adminCandidates.fields.currentTitle")}
              value={createDraft.currentTitle}
              onChange={(event) =>
                setCreateDraft((prev) => ({ ...prev, currentTitle: event.target.value }))
              }
            />
          </Stack>
          <TextField
            multiline
            minRows={4}
            fullWidth
            label={t("adminCandidates.fields.extraData")}
            value={createDraft.extraData}
            onChange={(event) => setCreateDraft((prev) => ({ ...prev, extraData: event.target.value }))}
          />
          <Stack direction="row" spacing={1.5}>
            <Button type="submit" variant="contained" disabled={createMutation.isPending}>
              {createMutation.isPending
                ? t("adminCandidates.createPending")
                : t("adminCandidates.createAction")}
            </Button>
          </Stack>
        </Stack>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Typography variant="h6">{t("adminCandidates.filters.title")}</Typography>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField
              size="small"
              label={t("adminCandidates.filters.search")}
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              sx={{ minWidth: 220 }}
            />
            <TextField
              size="small"
              label={t("adminCandidates.filters.location")}
              value={locationInput}
              onChange={(event) => setLocationInput(event.target.value)}
              sx={{ minWidth: 180 }}
            />
            <TextField
              size="small"
              label={t("adminCandidates.filters.currentTitle")}
              value={currentTitleInput}
              onChange={(event) => setCurrentTitleInput(event.target.value)}
              sx={{ minWidth: 220 }}
            />
            <TextField
              size="small"
              label={t("adminCandidates.filters.skill")}
              value={skillInput}
              onChange={(event) => setSkillInput(event.target.value)}
              sx={{ minWidth: 180 }}
            />
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel id="admin-candidates-analysis-ready-filter-label">
                {t("adminCandidates.filters.analysisReady")}
              </InputLabel>
              <Select
                labelId="admin-candidates-analysis-ready-filter-label"
                value={analysisReadyFilter}
                label={t("adminCandidates.filters.analysisReady")}
                onChange={(event) => setAnalysisReadyFilter(event.target.value as AnalysisReadyFilter)}
              >
                <MenuItem value="all">{t("adminCandidates.filters.any")}</MenuItem>
                <MenuItem value="ready">{t("adminCandidates.filters.ready")}</MenuItem>
                <MenuItem value="not-ready">{t("adminCandidates.filters.notReady")}</MenuItem>
              </Select>
            </FormControl>
            <TextField
              size="small"
              type="number"
              label={t("adminCandidates.filters.minYearsExperience")}
              value={minYearsExperienceInput}
              onChange={(event) => setMinYearsExperienceInput(event.target.value)}
              sx={{ minWidth: 180 }}
            />
            <Button variant="contained" onClick={applyFilters}>
              {t("adminCandidates.filters.apply")}
            </Button>
            <Button variant="outlined" onClick={resetFilters}>
              {t("adminCandidates.filters.reset")}
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
              <TableCell>{t("adminCandidates.table.candidate")}</TableCell>
              <TableCell>{t("adminCandidates.table.profile")}</TableCell>
              <TableCell>{t("adminCandidates.table.analysis")}</TableCell>
              <TableCell>{t("adminCandidates.table.experience")}</TableCell>
              <TableCell>{t("adminCandidates.table.updatedAt")}</TableCell>
              <TableCell>{t("adminCandidates.table.actions")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {listQuery.isLoading ? (
              <TableRow>
                <TableCell colSpan={6}>{t("adminCandidates.loading")}</TableCell>
              </TableRow>
            ) : null}
            {!listQuery.isLoading && items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6}>{t("adminCandidates.empty")}</TableCell>
              </TableRow>
            ) : null}
            {items.map((item) => (
              <TableRow key={item.candidate_id}>
                <TableCell>
                  <Stack spacing={0.25}>
                    <Typography variant="body2" fontWeight={600}>
                      {item.first_name} {item.last_name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {item.email}
                    </Typography>
                  </Stack>
                </TableCell>
                <TableCell>
                  <Stack spacing={0.25}>
                    <Typography variant="body2">{item.location || t("adminCandidates.notAvailable")}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {item.current_title || t("adminCandidates.notAvailable")}
                    </Typography>
                  </Stack>
                </TableCell>
                <TableCell>
                  <Stack spacing={0.25}>
                    <Typography variant="body2">
                      {item.analysis_ready
                        ? t("candidateCvAnalysis.yes")
                        : t("candidateCvAnalysis.no")}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {t(`candidateCvAnalysis.language.${item.detected_language}`)}
                    </Typography>
                  </Stack>
                </TableCell>
                <TableCell>
                  <Stack spacing={0.25}>
                    <Typography variant="body2">
                      {formatYearsExperience(item.years_experience, t("adminCandidates.notAvailable"))}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {renderSkillsSummary(item.skills, t)}
                    </Typography>
                  </Stack>
                </TableCell>
                <TableCell>{formatDateTime(item.updated_at, t("adminCandidates.notAvailable"))}</TableCell>
                <TableCell>
                  <Button
                    size="small"
                    variant="contained"
                    onClick={() => setSelectedCandidateId(String(item.candidate_id))}
                  >
                    {t("adminCandidates.actions.edit")}
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

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Typography variant="h6">{t("adminCandidates.editSectionTitle")}</Typography>
          {!selectedCandidateId ? (
            <Alert severity="info">{t("adminCandidates.selectPrompt")}</Alert>
          ) : selectedCandidateQuery.isLoading ? (
            <Alert severity="info">{t("adminCandidates.loadingSelected")}</Alert>
          ) : selectedCandidateQuery.isError ? (
            <Alert severity="error">
              {resolveApiErrorMessage(selectedCandidateQuery.error, t, "adminCandidates")}
            </Alert>
          ) : selectedCandidate ? (
            <Stack spacing={2} component="form" onSubmit={handleUpdateSubmit}>
              <Stack spacing={0.5}>
                <Typography variant="body2" fontWeight={600}>
                  {t("adminCandidates.selectedSummary", {
                    name: `${selectedCandidate.first_name} ${selectedCandidate.last_name}`,
                    candidateId: selectedCandidate.candidate_id,
                  })}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("adminCandidates.fields.ownerSubjectId")}: {selectedCandidate.owner_subject_id}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("adminCandidates.fields.phone")}:{" "}
                  {selectedCandidate.phone || t("adminCandidates.notAvailable")}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("adminCandidates.fields.location")}:{" "}
                  {selectedCandidate.location || t("adminCandidates.notAvailable")}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("adminCandidates.fields.currentTitle")}:{" "}
                  {selectedCandidate.current_title || t("adminCandidates.notAvailable")}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("adminCandidates.fields.extraData")}:{" "}
                  {JSON.stringify(selectedCandidate.extra_data)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("adminCandidates.detail.createdAt")}:{" "}
                  {formatDateTime(selectedCandidate.created_at, t("adminCandidates.notAvailable"))}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("adminCandidates.detail.updatedAt")}:{" "}
                  {formatDateTime(selectedCandidate.updated_at, t("adminCandidates.notAvailable"))}
                </Typography>
              </Stack>

              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField
                  required
                  fullWidth
                  label={t("adminCandidates.fields.firstName")}
                  value={editDraft.firstName}
                  onChange={(event) => setEditDraft((prev) => ({ ...prev, firstName: event.target.value }))}
                />
                <TextField
                  required
                  fullWidth
                  label={t("adminCandidates.fields.lastName")}
                  value={editDraft.lastName}
                  onChange={(event) => setEditDraft((prev) => ({ ...prev, lastName: event.target.value }))}
                />
              </Stack>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField
                  required
                  fullWidth
                  label={t("adminCandidates.fields.email")}
                  value={editDraft.email}
                  onChange={(event) => setEditDraft((prev) => ({ ...prev, email: event.target.value }))}
                />
                <TextField
                  fullWidth
                  label={t("adminCandidates.fields.phone")}
                  value={editDraft.phone}
                  onChange={(event) => setEditDraft((prev) => ({ ...prev, phone: event.target.value }))}
                />
              </Stack>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField
                  fullWidth
                  label={t("adminCandidates.fields.location")}
                  value={editDraft.location}
                  onChange={(event) =>
                    setEditDraft((prev) => ({ ...prev, location: event.target.value }))
                  }
                />
                <TextField
                  fullWidth
                  label={t("adminCandidates.fields.currentTitle")}
                  value={editDraft.currentTitle}
                  onChange={(event) =>
                    setEditDraft((prev) => ({ ...prev, currentTitle: event.target.value }))
                  }
                />
              </Stack>
              <TextField
                multiline
                minRows={4}
                fullWidth
                label={t("adminCandidates.fields.extraData")}
                value={editDraft.extraData}
                onChange={(event) => setEditDraft((prev) => ({ ...prev, extraData: event.target.value }))}
              />
              <Stack direction="row" spacing={1.5}>
                <Button type="submit" variant="contained" disabled={updateMutation.isPending}>
                  {updateMutation.isPending
                    ? t("adminCandidates.updatePending")
                    : t("adminCandidates.updateAction")}
                </Button>
              </Stack>
            </Stack>
          ) : (
            <Alert severity="warning">{t("adminCandidates.errors.selectCandidate")}</Alert>
          )}
        </Stack>
      </Paper>
    </Stack>
  );
}

function buildCreatePayload(draft: CandidateDraft): CandidateCreateRequest {
  const extraData = parseJsonObject(draft.extraData, {});
  return {
    owner_subject_id: normalizeNullableString(draft.ownerSubjectId),
    first_name: draft.firstName.trim(),
    last_name: draft.lastName.trim(),
    email: draft.email.trim(),
    phone: normalizeNullableString(draft.phone),
    location: normalizeNullableString(draft.location),
    current_title: normalizeNullableString(draft.currentTitle),
    extra_data: extraData,
  };
}

function buildUpdatePayload(draft: CandidateDraft): CandidateUpdateRequest {
  return {
    first_name: draft.firstName.trim(),
    last_name: draft.lastName.trim(),
    email: draft.email.trim(),
    phone: normalizeNullableString(draft.phone),
    location: normalizeNullableString(draft.location),
    current_title: normalizeNullableString(draft.currentTitle),
    extra_data: parseJsonObject(draft.extraData, null),
  };
}

function toDraft(candidate: CandidateResponse): CandidateDraft {
  return {
    ownerSubjectId: candidate.owner_subject_id ?? "",
    firstName: candidate.first_name,
    lastName: candidate.last_name,
    email: candidate.email,
    phone: candidate.phone ?? "",
    location: candidate.location ?? "",
    currentTitle: candidate.current_title ?? "",
    extraData: JSON.stringify(candidate.extra_data ?? {}, null, 2),
  };
}

function normalizeYearsExperience(value: string): number | undefined {
  const normalized = value.trim();
  if (!normalized) {
    return undefined;
  }
  const parsed = Number.parseFloat(normalized);
  return Number.isNaN(parsed) ? undefined : parsed;
}

function normalizeNullableString(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function parseJsonObject(
  value: string,
  fallback: Record<string, unknown> | null,
): Record<string, unknown> | null {
  const normalized = value.trim();
  if (!normalized) {
    return fallback;
  }
  try {
    const parsed = JSON.parse(normalized) as unknown;
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  } catch {
    // The backend contract expects structured JSON; invalid input must be rejected locally.
  }
  throw new Error("invalid_extra_data");
}

function renderSkillsSummary(skills: string[], fallback: string): string {
  return skills.length > 0 ? skills.join(", ") : fallback;
}

function formatYearsExperience(value: number | null | undefined, fallback: string): string {
  if (value === null || value === undefined) {
    return fallback;
  }
  return Number.isInteger(value) ? String(value) : value.toLocaleString();
}
