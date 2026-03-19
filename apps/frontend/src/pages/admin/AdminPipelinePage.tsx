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
import { useSearchParams } from "react-router-dom";

import {
  createPipelineTransition,
  listCandidateProfiles,
  listPipelineTransitions,
  listVacancies,
  type CandidateListItemResponse,
  type CandidateListQuery,
  type PipelineTransitionCreateRequest,
  type PipelineTransitionResponse,
  type VacancyResponse,
} from "../../api";
import { formatDateTime, normalizeFilterValue, resolveApiErrorMessage } from "./adminUtils";

const DEFAULT_CANDIDATE_LIMIT = 10;
const PIPELINE_STAGE_OPTIONS: PipelineTransitionCreateRequest["to_stage"][] = [
  "applied",
  "screening",
  "shortlist",
  "interview",
  "offer",
  "hired",
  "rejected",
];

type FeedbackState = {
  type: "success" | "error";
  message: string;
};

type VacancySelection = VacancyResponse | null;
type CandidateSelection = CandidateListItemResponse | null;

/**
 * Admin pipeline console for ordered transition history and transition appends.
 */
export function AdminPipelinePage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();

  const [vacancySearchInput, setVacancySearchInput] = useState("");
  const [candidateSearchInput, setCandidateSearchInput] = useState("");
  const [candidateQuery, setCandidateQuery] = useState<CandidateListQuery>({
    limit: DEFAULT_CANDIDATE_LIMIT,
    offset: 0,
  });
  const [selectedVacancyId, setSelectedVacancyId] = useState(
    searchParams.get("vacancyId") ?? "",
  );
  const [selectedCandidateId, setSelectedCandidateId] = useState("");
  const [selectedVacancySnapshot, setSelectedVacancySnapshot] =
    useState<VacancySelection>(null);
  const [selectedCandidateSnapshot, setSelectedCandidateSnapshot] =
    useState<CandidateSelection>(null);
  const [transitionStage, setTransitionStage] =
    useState<PipelineTransitionCreateRequest["to_stage"]>("applied");
  const [transitionReason, setTransitionReason] = useState("");
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  const vacanciesQuery = useQuery({
    queryKey: ["admin-pipeline-vacancies"],
    queryFn: () => listVacancies(),
  });

  const candidatesQuery = useQuery({
    queryKey: ["admin-pipeline-candidates", candidateQuery],
    queryFn: () => listCandidateProfiles(candidateQuery),
  });

  const transitionsQuery = useQuery({
    queryKey: ["admin-pipeline-transitions", selectedVacancyId, selectedCandidateId],
    queryFn: () => listPipelineTransitions(selectedVacancyId, selectedCandidateId),
    enabled: Boolean(selectedVacancyId && selectedCandidateId),
  });

  const transitionMutation = useMutation({
    mutationFn: (payload: PipelineTransitionCreateRequest) => createPipelineTransition(payload),
    onSuccess: () => {
      setFeedback({ type: "success", message: t("adminPipeline.transitionSuccess") });
      setTransitionReason("");
      void queryClient.invalidateQueries({ queryKey: ["admin-pipeline-transitions"] });
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveApiErrorMessage(error, t, "adminPipeline") });
    },
  });

  useEffect(() => {
    if (!selectedVacancyId) {
      setSelectedVacancySnapshot(null);
      return;
    }
    const vacancy = vacanciesQuery.data?.items.find(
      (item) => String(item.vacancy_id) === selectedVacancyId,
    );
    if (vacancy) {
      setSelectedVacancySnapshot(vacancy);
    }
  }, [selectedVacancyId, vacanciesQuery.data?.items]);

  const vacancyItems = useMemo(() => vacanciesQuery.data?.items ?? [], [vacanciesQuery.data?.items]);
  const candidateItems = useMemo(() => candidatesQuery.data?.items ?? [], [candidatesQuery.data?.items]);
  const filteredVacancies = useMemo(
    () => filterVacancies(vacancyItems, vacancySearchInput),
    [vacancyItems, vacancySearchInput],
  );
  const selectedVacancy = selectedVacancySnapshot;
  const selectedCandidate = selectedCandidateSnapshot;
  const candidatePage = Math.floor(candidateQuery.offset / candidateQuery.limit);
  const historyItems = transitionsQuery.data?.items ?? [];
  const listErrorMessage = useMemo(() => {
    if (!vacanciesQuery.error) {
      return "";
    }
    return resolveApiErrorMessage(vacanciesQuery.error, t, "adminPipeline");
  }, [t, vacanciesQuery.error]);
  const candidateErrorMessage = useMemo(() => {
    if (!candidatesQuery.error) {
      return "";
    }
    return resolveApiErrorMessage(candidatesQuery.error, t, "adminPipeline");
  }, [candidatesQuery.error, t]);
  const historyErrorMessage = useMemo(() => {
    if (!transitionsQuery.error) {
      return "";
    }
    return resolveApiErrorMessage(transitionsQuery.error, t, "adminPipeline");
  }, [t, transitionsQuery.error]);

  const applyCandidateFilters = () => {
    setFeedback(null);
    setCandidateQuery((prev) => ({
      ...prev,
      offset: 0,
      search: normalizeFilterValue(candidateSearchInput),
    }));
  };

  const resetCandidateFilters = () => {
    setCandidateSearchInput("");
    setFeedback(null);
    setCandidateQuery((prev) => ({
      ...prev,
      offset: 0,
      search: undefined,
    }));
  };

  const handleSelectVacancy = (vacancy: VacancyResponse) => {
    setFeedback(null);
    setSelectedVacancyId(String(vacancy.vacancy_id));
    setSelectedVacancySnapshot(vacancy);
    setSelectedCandidateId("");
    setSelectedCandidateSnapshot(null);
  };

  const handleSelectCandidate = (candidate: CandidateListItemResponse) => {
    setFeedback(null);
    setSelectedCandidateId(String(candidate.candidate_id));
    setSelectedCandidateSnapshot(candidate);
  };

  const handleTransitionSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedVacancyId || !selectedCandidateId) {
      setFeedback({
        type: "error",
        message: t("adminPipeline.errors.selectTransitionContext"),
      });
      return;
    }
    setFeedback(null);
    transitionMutation.mutate({
      vacancy_id: selectedVacancyId,
      candidate_id: selectedCandidateId,
      to_stage: transitionStage,
      reason: normalizeNullableString(transitionReason),
    });
  };

  return (
    <Stack spacing={2}>
      <Box>
        <Typography variant="h4">{t("adminPipeline.title")}</Typography>
        <Typography variant="body2">{t("adminPipeline.subtitle")}</Typography>
      </Box>

      <Stack direction={{ xs: "column", lg: "row" }} spacing={2}>
        <Paper sx={{ p: 2, flex: 1 }}>
          <Stack spacing={2}>
            <Typography variant="h6">{t("adminPipeline.vacancySelectorTitle")}</Typography>
            <TextField
              size="small"
              label={t("adminPipeline.filters.vacancySearch")}
              value={vacancySearchInput}
              onChange={(event) => setVacancySearchInput(event.target.value)}
            />
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t("adminPipeline.table.vacancy")}</TableCell>
                  <TableCell>{t("adminPipeline.table.department")}</TableCell>
                  <TableCell>{t("adminPipeline.table.status")}</TableCell>
                  <TableCell>{t("adminPipeline.table.actions")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {vacanciesQuery.isLoading ? (
                  <TableRow>
                    <TableCell colSpan={4}>{t("adminPipeline.loadingVacancies")}</TableCell>
                  </TableRow>
                ) : null}
                {!vacanciesQuery.isLoading && filteredVacancies.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4}>{t("adminPipeline.emptyVacancies")}</TableCell>
                  </TableRow>
                ) : null}
                {filteredVacancies.map((item) => (
                  <TableRow key={item.vacancy_id}>
                    <TableCell>
                      <Stack spacing={0.25}>
                        <Typography variant="body2" fontWeight={600}>
                          {item.title}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {item.hiring_manager_login || t("adminPipeline.notAvailable")}
                        </Typography>
                      </Stack>
                    </TableCell>
                    <TableCell>{item.department}</TableCell>
                    <TableCell>{item.status}</TableCell>
                    <TableCell>
                      <Button variant="contained" size="small" onClick={() => handleSelectVacancy(item)}>
                        {t("adminPipeline.actions.selectVacancy")}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Stack>
        </Paper>

        <Paper sx={{ p: 2, flex: 1 }}>
          <Stack spacing={2}>
            <Typography variant="h6">{t("adminPipeline.candidateSelectorTitle")}</Typography>
            <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
              <TextField
                size="small"
                fullWidth
                label={t("adminPipeline.filters.candidateSearch")}
                value={candidateSearchInput}
                onChange={(event) => setCandidateSearchInput(event.target.value)}
              />
              <Button variant="contained" onClick={applyCandidateFilters}>
                {t("adminPipeline.filters.apply")}
              </Button>
              <Button variant="outlined" onClick={resetCandidateFilters}>
                {t("adminPipeline.filters.reset")}
              </Button>
            </Stack>
            {candidatesQuery.error ? <Alert severity="error">{candidateErrorMessage}</Alert> : null}
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t("adminPipeline.table.candidate")}</TableCell>
                  <TableCell>{t("adminPipeline.table.stage")}</TableCell>
                  <TableCell>{t("adminPipeline.table.analysis")}</TableCell>
                  <TableCell>{t("adminPipeline.table.actions")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {candidatesQuery.isLoading ? (
                  <TableRow>
                    <TableCell colSpan={4}>{t("adminPipeline.loadingCandidates")}</TableCell>
                  </TableRow>
                ) : null}
                {!candidatesQuery.isLoading && candidateItems.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4}>{t("adminPipeline.emptyCandidates")}</TableCell>
                  </TableRow>
                ) : null}
                {candidateItems.map((item) => (
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
                      {item.vacancy_stage
                        ? t(`hrDashboard.stages.${item.vacancy_stage}`)
                        : t("adminPipeline.notAvailable")}
                    </TableCell>
                    <TableCell>
                      {item.analysis_ready ? t("candidateCvAnalysis.yes") : t("candidateCvAnalysis.no")}
                    </TableCell>
                    <TableCell>
                      <Button variant="contained" size="small" onClick={() => handleSelectCandidate(item)}>
                        {t("adminPipeline.actions.selectCandidate")}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <TablePagination
              component="div"
              count={candidatesQuery.data?.total ?? 0}
              page={candidatePage}
              rowsPerPage={candidateQuery.limit}
              onPageChange={(_event, nextPage) =>
                setCandidateQuery((prev) => ({ ...prev, offset: nextPage * prev.limit }))
              }
              onRowsPerPageChange={(event) => {
                const nextLimit = Number.parseInt(event.target.value, 10);
                setCandidateQuery((prev) => ({ ...prev, limit: nextLimit, offset: 0 }));
              }}
              rowsPerPageOptions={[5, 10, 20, 50]}
            />
          </Stack>
        </Paper>
      </Stack>

      {feedback ? <Alert severity={feedback.type}>{feedback.message}</Alert> : null}
      {vacanciesQuery.error ? <Alert severity="error">{listErrorMessage}</Alert> : null}

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Typography variant="h6">{t("adminPipeline.contextTitle")}</Typography>
          {selectedVacancyId || selectedCandidateId ? (
            <Stack spacing={0.5}>
              <Typography variant="body2" fontWeight={600}>
                {selectedVacancy
                  ? t("adminPipeline.selectedVacancySummary", {
                      title: selectedVacancy.title,
                      vacancyId: selectedVacancy.vacancy_id,
                    })
                  : t("adminPipeline.selectedVacancyFallback", { vacancyId: selectedVacancyId })}
              </Typography>
              <Typography variant="body2" fontWeight={600}>
                {selectedCandidate
                  ? t("adminPipeline.selectedCandidateSummary", {
                      name: `${selectedCandidate.first_name} ${selectedCandidate.last_name}`,
                      candidateId: selectedCandidate.candidate_id,
                    })
                  : t("adminPipeline.selectedCandidateFallback", {
                      candidateId: selectedCandidateId,
                    })}
              </Typography>
            </Stack>
          ) : (
            <Alert severity="info">{t("adminPipeline.selectPrompt")}</Alert>
          )}
        </Stack>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2} component="form" onSubmit={handleTransitionSubmit}>
          <Typography variant="h6">{t("adminPipeline.transitionSectionTitle")}</Typography>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <FormControl size="small" fullWidth>
              <InputLabel id="admin-pipeline-stage-label">{t("adminPipeline.fields.transitionStage")}</InputLabel>
              <Select
                labelId="admin-pipeline-stage-label"
                value={transitionStage}
                label={t("adminPipeline.fields.transitionStage")}
                onChange={(event) =>
                  setTransitionStage(event.target.value as PipelineTransitionCreateRequest["to_stage"])
                }
              >
                {PIPELINE_STAGE_OPTIONS.map((stage) => (
                  <MenuItem key={stage} value={stage}>
                    {t(`hrDashboard.stages.${stage}`)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              fullWidth
              label={t("adminPipeline.fields.transitionReason")}
              value={transitionReason}
              onChange={(event) => setTransitionReason(event.target.value)}
            />
          </Stack>
          <Stack direction="row" spacing={1.5}>
            <Button
              type="submit"
              variant="contained"
              disabled={transitionMutation.isPending || !selectedVacancyId || !selectedCandidateId}
            >
              {transitionMutation.isPending
                ? t("adminPipeline.transitionPending")
                : t("adminPipeline.transitionAction")}
            </Button>
          </Stack>
        </Stack>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Typography variant="h6">{t("adminPipeline.timelineTitle")}</Typography>
          {!selectedVacancyId || !selectedCandidateId ? (
            <Alert severity="info">{t("adminPipeline.selectContextHint")}</Alert>
          ) : transitionsQuery.isLoading ? (
            <Alert severity="info">{t("adminPipeline.loadingTimeline")}</Alert>
          ) : transitionsQuery.error ? (
            <Alert severity="error">{historyErrorMessage}</Alert>
          ) : historyItems.length === 0 ? (
            <Alert severity="info">{t("adminPipeline.emptyTimeline")}</Alert>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t("adminPipeline.table.fromStage")}</TableCell>
                  <TableCell>{t("adminPipeline.table.toStage")}</TableCell>
                  <TableCell>{t("adminPipeline.table.reason")}</TableCell>
                  <TableCell>{t("adminPipeline.table.changedBy")}</TableCell>
                  <TableCell>{t("adminPipeline.table.transitionedAt")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {historyItems.map((item) => (
                  <TableRow key={item.transition_id}>
                    <TableCell>{renderStageLabel(item.from_stage, t)}</TableCell>
                    <TableCell>{renderStageLabel(item.to_stage, t)}</TableCell>
                    <TableCell>{item.reason || t("hrDashboard.timeline.noReason")}</TableCell>
                    <TableCell>
                      <Stack spacing={0.25}>
                        <Typography variant="body2">{item.changed_by_role}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {item.changed_by_sub}
                        </Typography>
                      </Stack>
                    </TableCell>
                    <TableCell>{formatDateTime(item.transitioned_at, t("adminPipeline.notAvailable"))}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Stack>
      </Paper>
    </Stack>
  );
}

function filterVacancies(items: VacancyResponse[], searchInput: string): VacancyResponse[] {
  const search = searchInput.trim().toLowerCase();
  if (!search) {
    return items;
  }
  return items.filter((item) =>
    [item.title, item.department, item.status, item.hiring_manager_login, item.hiring_manager_staff_id]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(search)),
  );
}

function normalizeNullableString(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function renderStageLabel(
  value: PipelineTransitionResponse["from_stage"] | PipelineTransitionResponse["to_stage"],
  t: (key: string) => string,
): string {
  if (!value) {
    return t("hrDashboard.timeline.start");
  }
  return t(`hrDashboard.stages.${value}`);
}
