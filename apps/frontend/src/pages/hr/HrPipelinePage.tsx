import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Chip,
  Box,
  Divider,
  FormControl,
  FormControlLabel,
  InputLabel,
  List,
  ListItem,
  ListItemText,
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
  createMatchScore,
  getMatchScore,
  createPipelineTransition,
  listCandidateProfiles,
  listPipelineTransitions,
  listVacancies,
  type CandidateListItemResponse,
  type CandidateListQuery,
  type MatchScoreResponse,
  type PipelineTransitionCreateRequest,
  type VacancyResponse,
} from "../../api";
import { readAuthSession } from "../../app/auth/session";
import { PageHero } from "../../components/PageHero";
import { HrWorkspaceNav } from "./HrWorkspaceNav";
import {
  DEFAULT_CANDIDATE_LIMIT,
  MATCH_SCORE_POLL_INTERVAL_MS,
  PIPELINE_STAGE_OPTIONS,
  type CandidateStageFilterValue,
  type FeedbackState,
  buildMatchScoreManualReviewMessage,
  formatCandidateLabel,
  formatConfidence,
  formatDateTime,
  formatScore,
  mergeCandidateSelectItems,
  normalizeCandidateFilterValue,
  normalizeInput,
  renderStringList,
  resolveMatchScoreChipColor,
  resolveRecruitmentApiError,
} from "./hrWorkspaceShared";

/**
 * Focused pipeline and shortlist page for the HR workspace.
 */
export function HrPipelinePage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const session = readAuthSession();
  const accessToken = session.accessToken;
  const [selectedVacancyId, setSelectedVacancyId] = useState("");
  const [selectedCandidateId, setSelectedCandidateId] = useState("");
  const [transitionStage, setTransitionStage] =
    useState<PipelineTransitionCreateRequest["to_stage"]>("applied");
  const [transitionReason, setTransitionReason] = useState("");
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const [scoreFeedback, setScoreFeedback] = useState<FeedbackState | null>(null);
  const [candidateSearchInput, setCandidateSearchInput] = useState("");
  const [candidateAnalysisReadyOnly, setCandidateAnalysisReadyOnly] = useState(false);
  const [candidateInPipelineOnly, setCandidateInPipelineOnly] = useState(false);
  const [candidateStageFilter, setCandidateStageFilter] =
    useState<CandidateStageFilterValue>("all");
  const [candidateQuery, setCandidateQuery] = useState<CandidateListQuery>({
    limit: DEFAULT_CANDIDATE_LIMIT,
    offset: 0,
  });
  const [selectedCandidateSnapshot, setSelectedCandidateSnapshot] =
    useState<CandidateListItemResponse | null>(null);
  const matchScoreQueryKey = [
    "hr-match-score",
    accessToken,
    selectedVacancyId,
    selectedCandidateId,
  ];

  const vacanciesQuery = useQuery({
    queryKey: ["hr-vacancies", accessToken],
    queryFn: () => listVacancies(),
    enabled: Boolean(accessToken),
  });

  const effectiveCandidateQuery: CandidateListQuery = {
    limit: candidateQuery.limit ?? DEFAULT_CANDIDATE_LIMIT,
    offset: candidateQuery.offset ?? 0,
    search: candidateQuery.search,
    analysisReady: candidateQuery.analysisReady,
    vacancyId: selectedVacancyId || undefined,
    inPipelineOnly: selectedVacancyId ? candidateQuery.inPipelineOnly : undefined,
    stage: selectedVacancyId ? candidateQuery.stage : undefined,
  };

  const candidatesQuery = useQuery({
    queryKey: ["hr-candidates", accessToken, effectiveCandidateQuery],
    queryFn: () => listCandidateProfiles(effectiveCandidateQuery),
    enabled: Boolean(accessToken),
  });

  const transitionsQuery = useQuery({
    queryKey: ["hr-pipeline-history", accessToken, selectedVacancyId, selectedCandidateId],
    queryFn: () => listPipelineTransitions(selectedVacancyId, selectedCandidateId),
    enabled: Boolean(accessToken && selectedVacancyId && selectedCandidateId),
  });

  const matchScoreQuery = useQuery({
    queryKey: matchScoreQueryKey,
    queryFn: async () => {
      try {
        return await getMatchScore(accessToken!, selectedVacancyId, selectedCandidateId);
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          return null;
        }
        throw error;
      }
    },
    enabled: Boolean(accessToken && selectedVacancyId && selectedCandidateId),
    refetchInterval: (query) => {
      const item = query.state.data as MatchScoreResponse | null | undefined;
      if (item && (item.status === "queued" || item.status === "running")) {
        return MATCH_SCORE_POLL_INTERVAL_MS;
      }
      return false;
    },
  });

  const vacancyItems = useMemo(() => vacanciesQuery.data?.items ?? [], [vacanciesQuery.data?.items]);
  const candidateItems = useMemo(() => candidatesQuery.data?.items ?? [], [candidatesQuery.data?.items]);
  const candidateTotal = candidatesQuery.data?.total ?? 0;
  const candidatePage = Math.floor(
    (effectiveCandidateQuery.offset ?? 0) / (effectiveCandidateQuery.limit ?? DEFAULT_CANDIDATE_LIMIT),
  );
  const selectedVacancy =
    vacancyItems.find((item) => item.vacancy_id === selectedVacancyId) ?? null;
  const selectedCandidate =
    candidateItems.find((item) => item.candidate_id === selectedCandidateId)
    ?? (selectedCandidateSnapshot?.candidate_id === selectedCandidateId
      ? selectedCandidateSnapshot
      : null);
  const candidateSelectItems = mergeCandidateSelectItems(candidateItems, selectedCandidate);
  const matchScore = matchScoreQuery.data ?? null;
  const matchedRequirements = matchScore?.matched_requirements ?? [];
  const missingRequirements = matchScore?.missing_requirements ?? [];
  const matchScoreEvidence = matchScore?.evidence ?? [];
  const hasSelectionContext = Boolean(selectedVacancyId && selectedCandidateId);
  const candidateListErrorMessage = candidatesQuery.error
    ? resolveRecruitmentApiError(candidatesQuery.error, t)
    : "";

  const transitionMutation = useMutation({
    mutationFn: (payload: PipelineTransitionCreateRequest) => createPipelineTransition(payload),
    onSuccess: () => {
      setFeedback({ type: "success", message: t("hrDashboard.transitionSuccess") });
      setTransitionReason("");
      void queryClient.invalidateQueries({ queryKey: ["hr-pipeline-history"] });
      void queryClient.invalidateQueries({ queryKey: matchScoreQueryKey });
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveRecruitmentApiError(error, t) });
    },
  });

  const runScoreMutation = useMutation({
    mutationFn: () =>
      createMatchScore(accessToken!, selectedVacancyId, {
        candidate_id: selectedCandidateId,
      }),
    onSuccess: (payload) => {
      setScoreFeedback(null);
      queryClient.setQueryData(matchScoreQueryKey, payload);
      void queryClient.invalidateQueries({ queryKey: matchScoreQueryKey });
    },
    onError: (error: unknown) => {
      setScoreFeedback({ type: "error", message: resolveRecruitmentApiError(error, t) });
    },
  });

  useEffect(() => {
    if (!selectedCandidateId) {
      setSelectedCandidateSnapshot(null);
      return;
    }
    const nextSelectedCandidate =
      candidateItems.find((item) => item.candidate_id === selectedCandidateId) ?? null;
    if (nextSelectedCandidate) {
      setSelectedCandidateSnapshot(nextSelectedCandidate);
    }
  }, [candidateItems, selectedCandidateId]);

  const handleSelectVacancy = (vacancy: VacancyResponse) => {
    setSelectedVacancyId(vacancy.vacancy_id);
    setSelectedCandidateId("");
    setSelectedCandidateSnapshot(null);
    setScoreFeedback(null);
    setFeedback(null);
  };

  const handleSelectCandidate = (candidateId: string) => {
    setSelectedCandidateId(candidateId);
    setSelectedCandidateSnapshot(
      candidateSelectItems.find((item) => item.candidate_id === candidateId) ?? null,
    );
    setScoreFeedback(null);
    setFeedback(null);
  };

  const handleApplyCandidateFilters = () => {
    setFeedback(null);
    setCandidateQuery((prev) => ({
      ...prev,
      offset: 0,
      search: normalizeCandidateFilterValue(candidateSearchInput),
      analysisReady: candidateAnalysisReadyOnly ? true : undefined,
      inPipelineOnly: selectedVacancyId && candidateInPipelineOnly ? true : undefined,
      stage:
        selectedVacancyId && candidateStageFilter !== "all"
          ? candidateStageFilter
          : undefined,
    }));
  };

  const handleResetCandidateFilters = () => {
    setCandidateSearchInput("");
    setCandidateAnalysisReadyOnly(false);
    setCandidateInPipelineOnly(false);
    setCandidateStageFilter("all");
    setFeedback(null);
    setCandidateQuery((prev) => ({
      ...prev,
      offset: 0,
      search: undefined,
      analysisReady: undefined,
      inPipelineOnly: undefined,
      stage: undefined,
    }));
  };

  const handleCreateTransition = () => {
    if (!selectedVacancyId || !selectedCandidateId) {
      setFeedback({ type: "error", message: t("hrDashboard.errors.selectTransitionContext") });
      return;
    }
    setFeedback(null);
    transitionMutation.mutate({
      vacancy_id: selectedVacancyId,
      candidate_id: selectedCandidateId,
      to_stage: transitionStage,
      reason: normalizeInput(transitionReason),
    });
  };

  const handleRunScore = () => {
    if (!selectedVacancyId || !selectedCandidateId) {
      setScoreFeedback({ type: "error", message: t("hrDashboard.errors.selectShortlistContext") });
      return;
    }
    setScoreFeedback(null);
    runScoreMutation.mutate();
  };

  if (!accessToken) {
    return <Alert severity="info">{t("hrDashboard.authRequired")}</Alert>;
  }

  return (
    <Stack spacing={3}>
      <PageHero
        eyebrow={t("hrDashboard.title")}
        title={t("hrWorkspacePages.pipeline.title")}
        description={t("hrWorkspacePages.pipeline.subtitle")}
        imageSrc="/images/company-hero.jpg"
        imageAlt={t("hrDashboard.title")}
        chips={[
          t("hrDashboard.pipelineTitle"),
          t("hrDashboard.shortlist.title"),
          t("hrWorkspaceNav.workbench"),
        ]}
      />

      <HrWorkspaceNav />

      {feedback ? <Alert severity={feedback.type}>{feedback.message}</Alert> : null}

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField
              select
              label={t("hrWorkspacePages.pipeline.vacancyLabel")}
              value={selectedVacancyId}
              onChange={(event) => {
                const nextVacancy = vacancyItems.find((item) => item.vacancy_id === event.target.value);
                if (nextVacancy) {
                  handleSelectVacancy(nextVacancy);
                }
              }}
              fullWidth
              SelectProps={{ native: true }}
            >
              <option value="">{t("hrWorkspacePages.pipeline.vacancyPlaceholder")}</option>
              {vacancyItems.map((vacancy) => (
                <option key={vacancy.vacancy_id} value={vacancy.vacancy_id}>
                  {vacancy.title} ({vacancy.department})
                </option>
              ))}
            </TextField>
            <TextField
              select
              label={t("hrDashboard.fields.candidate")}
              value={selectedCandidateId}
              onChange={(event) => handleSelectCandidate(event.target.value)}
              fullWidth
              SelectProps={{ native: true }}
            >
              <option value="">{t("hrDashboard.selectCandidateAction")}</option>
              {candidateSelectItems.map((candidate) => (
                <option key={candidate.candidate_id} value={candidate.candidate_id}>
                  {formatCandidateLabel(candidate)}
                </option>
              ))}
            </TextField>
          </Stack>

          <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems="center">
            <TextField
              size="small"
              label={t("hrDashboard.filters.candidateSearch")}
              value={candidateSearchInput}
              onChange={(event) => setCandidateSearchInput(event.target.value)}
              sx={{ minWidth: 220 }}
            />
            <FormControlLabel
              control={
                <Switch
                  checked={candidateAnalysisReadyOnly}
                  onChange={(event) => setCandidateAnalysisReadyOnly(event.target.checked)}
                />
              }
              label={t("hrDashboard.filters.analysisReady")}
            />
            <FormControlLabel
              control={
                <Switch
                  checked={candidateInPipelineOnly}
                  onChange={(event) => setCandidateInPipelineOnly(event.target.checked)}
                  disabled={!selectedVacancyId}
                />
              }
              label={t("hrDashboard.filters.inPipelineOnly")}
            />
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel id="hr-pipeline-stage-filter-label">
                {t("hrDashboard.filters.stage")}
              </InputLabel>
              <Select
                labelId="hr-pipeline-stage-filter-label"
                value={candidateStageFilter}
                label={t("hrDashboard.filters.stage")}
                disabled={!selectedVacancyId}
                onChange={(event) =>
                  setCandidateStageFilter(event.target.value as CandidateStageFilterValue)
                }
              >
                <MenuItem value="all">{t("hrDashboard.filters.anyStage")}</MenuItem>
                {PIPELINE_STAGE_OPTIONS.map((stage) => (
                  <MenuItem key={stage} value={stage}>
                    {t(`hrDashboard.stages.${stage}`)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button variant="contained" onClick={handleApplyCandidateFilters}>
              {t("hrDashboard.filters.apply")}
            </Button>
            <Button variant="outlined" onClick={handleResetCandidateFilters}>
              {t("hrDashboard.filters.reset")}
            </Button>
          </Stack>

          {candidatesQuery.error ? <Alert severity="error">{candidateListErrorMessage}</Alert> : null}

          <TablePagination
            component="div"
            count={candidateTotal}
            page={candidatePage}
            rowsPerPage={effectiveCandidateQuery.limit ?? DEFAULT_CANDIDATE_LIMIT}
            onPageChange={(_, nextPage) => {
              setCandidateQuery((prev) => ({
                ...prev,
                offset: nextPage * (prev.limit ?? DEFAULT_CANDIDATE_LIMIT),
              }));
            }}
            onRowsPerPageChange={(event) => {
              const nextLimit = Number.parseInt(event.target.value, 10);
              setCandidateQuery((prev) => ({
                ...prev,
                limit: nextLimit,
                offset: 0,
              }));
            }}
            rowsPerPageOptions={[10, 20, 50, 100]}
          />

          <Typography variant="body2" color="text.secondary">
            {selectedCandidate
              ? t("hrDashboard.selectedCandidateSummary", {
                  candidateName: formatCandidateLabel(selectedCandidate),
                  candidateId: selectedCandidate.candidate_id,
                })
              : t("hrWorkspacePages.pipeline.noCandidateSelected")}
          </Typography>
        </Stack>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Stack
            direction={{ xs: "column", md: "row" }}
            spacing={2}
            justifyContent="space-between"
            alignItems={{ xs: "stretch", md: "center" }}
          >
            <Stack spacing={1}>
              <Typography variant="h6">{t("hrDashboard.pipelineTitle")}</Typography>
              <Typography variant="body2" color="text.secondary">
                {t("hrDashboard.subtitle")}
              </Typography>
            </Stack>
            <Button
              variant="contained"
              onClick={handleCreateTransition}
              disabled={transitionMutation.isPending}
            >
              {transitionMutation.isPending
                ? t("hrDashboard.transitionPending")
                : t("hrDashboard.transitionAction")}
            </Button>
          </Stack>

          <TextField
            label={t("hrDashboard.fields.transitionStage")}
            value={transitionStage}
            onChange={(event) =>
              setTransitionStage(event.target.value as PipelineTransitionCreateRequest["to_stage"])
            }
            SelectProps={{ native: true }}
            select
          >
            {PIPELINE_STAGE_OPTIONS.map((stage) => (
              <option key={stage} value={stage}>
                {t(`hrDashboard.stages.${stage}`)}
              </option>
            ))}
          </TextField>

          <TextField
            label={t("hrDashboard.fields.transitionReason")}
            value={transitionReason}
            onChange={(event) => setTransitionReason(event.target.value)}
            multiline
            minRows={2}
          />

          {selectedVacancy ? (
            <Typography variant="body2" color="text.secondary">
              {t("hrDashboard.selectedVacancySummary", {
                vacancyTitle: selectedVacancy.title,
                vacancyId: selectedVacancy.vacancy_id,
              })}
            </Typography>
          ) : null}

          <Box>
            <Typography variant="subtitle1">{t("hrDashboard.timelineTitle")}</Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t("hrDashboard.timeline.fromStage")}</TableCell>
                  <TableCell>{t("hrDashboard.timeline.toStage")}</TableCell>
                  <TableCell>{t("hrDashboard.timeline.reason")}</TableCell>
                  <TableCell>{t("hrDashboard.timeline.changedBy")}</TableCell>
                  <TableCell>{t("hrDashboard.timeline.transitionedAt")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {transitionsQuery.isLoading ? (
                  <TableRow>
                    <TableCell colSpan={5}>{t("hrDashboard.loadingTimeline")}</TableCell>
                  </TableRow>
                ) : null}
                {!transitionsQuery.isLoading
                  && selectedVacancyId
                  && selectedCandidateId
                  && (transitionsQuery.data?.items.length ?? 0) === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5}>{t("hrDashboard.emptyTimeline")}</TableCell>
                  </TableRow>
                ) : null}
                {!selectedVacancyId || !selectedCandidateId ? (
                  <TableRow>
                    <TableCell colSpan={5}>{t("hrDashboard.selectTimelineContext")}</TableCell>
                  </TableRow>
                ) : null}
                {transitionsQuery.data?.items.map((transition) => (
                  <TableRow key={transition.transition_id}>
                    <TableCell>
                      {transition.from_stage
                        ? t(`hrDashboard.stages.${transition.from_stage}`)
                        : t("hrDashboard.timeline.start")}
                    </TableCell>
                    <TableCell>{t(`hrDashboard.stages.${transition.to_stage}`)}</TableCell>
                    <TableCell>{transition.reason || t("hrDashboard.timeline.noReason")}</TableCell>
                    <TableCell>{transition.changed_by_role}</TableCell>
                    <TableCell>{formatDateTime(transition.transitioned_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        </Stack>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Stack
            direction={{ xs: "column", md: "row" }}
            spacing={2}
            justifyContent="space-between"
            alignItems={{ xs: "stretch", md: "center" }}
          >
            <Stack spacing={1}>
              <Typography variant="h6">{t("hrDashboard.shortlist.title")}</Typography>
              <Typography variant="body2" color="text.secondary">
                {t("hrDashboard.shortlist.subtitle")}
              </Typography>
            </Stack>
            <Button
              variant="contained"
              onClick={handleRunScore}
              disabled={!selectedVacancyId || !selectedCandidateId || runScoreMutation.isPending}
            >
              {runScoreMutation.isPending
                ? t("hrDashboard.shortlist.runPending")
                : t("hrDashboard.shortlist.runAction")}
            </Button>
          </Stack>

          {scoreFeedback ? <Alert severity={scoreFeedback.type}>{scoreFeedback.message}</Alert> : null}

          {!hasSelectionContext ? (
            <Alert severity="info">{t("hrDashboard.shortlist.inactive")}</Alert>
          ) : null}

          {hasSelectionContext ? (
            <Stack spacing={2}>
              {matchScoreQuery.isLoading && !matchScore ? (
                <Typography variant="body2">{t("hrDashboard.shortlist.loading")}</Typography>
              ) : null}

              {matchScoreQuery.isError ? (
                <Alert severity="error">
                  {resolveRecruitmentApiError(matchScoreQuery.error, t)}
                </Alert>
              ) : null}

              {!matchScoreQuery.isError && !matchScoreQuery.isLoading && !matchScore ? (
                <Alert severity="info">{t("hrDashboard.shortlist.empty")}</Alert>
              ) : null}

              {matchScore ? (
                <Stack spacing={2}>
                  <Stack
                    direction={{ xs: "column", md: "row" }}
                    spacing={1}
                    alignItems={{ xs: "flex-start", md: "center" }}
                  >
                    <Typography variant="body2" color="text.secondary">
                      {t("hrDashboard.shortlist.statusLabel")}
                    </Typography>
                    <Chip
                      label={t(`hrDashboard.shortlist.status.${matchScore.status}`)}
                      color={resolveMatchScoreChipColor(matchScore.status)}
                      size="small"
                    />
                    {matchScore.scored_at ? (
                      <Typography variant="body2" color="text.secondary">
                        {t("hrDashboard.shortlist.scoredAt", {
                          value: formatDateTime(matchScore.scored_at),
                        })}
                      </Typography>
                    ) : null}
                    {matchScore.model_name && matchScore.model_version ? (
                      <Typography variant="body2" color="text.secondary">
                        {t("hrDashboard.shortlist.model", {
                          modelName: matchScore.model_name,
                          modelVersion: matchScore.model_version,
                        })}
                      </Typography>
                    ) : null}
                  </Stack>

                  {matchScore.status === "succeeded" && matchScore.requires_manual_review ? (
                    <Alert severity="warning">
                      <Typography variant="subtitle2">
                        {t("hrDashboard.shortlist.manualReview.title")}
                      </Typography>
                      <Typography variant="body2">
                        {buildMatchScoreManualReviewMessage(matchScore, t)}
                      </Typography>
                    </Alert>
                  ) : null}

                  {matchScore.status === "failed" ? (
                    <Alert severity="warning">{t("hrDashboard.shortlist.failedHint")}</Alert>
                  ) : null}

                  <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                    <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                      <Stack spacing={1}>
                        <Typography variant="overline">
                          {t("hrDashboard.shortlist.scoreLabel")}
                        </Typography>
                        <Typography variant="h4">{formatScore(matchScore.score, t)}</Typography>
                      </Stack>
                    </Paper>
                    <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                      <Stack spacing={1}>
                        <Typography variant="overline">
                          {t("hrDashboard.shortlist.confidenceLabel")}
                        </Typography>
                        <Typography variant="h4">
                          {formatConfidence(matchScore.confidence, t)}
                        </Typography>
                      </Stack>
                    </Paper>
                    <Paper variant="outlined" sx={{ p: 2, flex: 2 }}>
                      <Stack spacing={1}>
                        <Typography variant="overline">
                          {t("hrDashboard.shortlist.summaryLabel")}
                        </Typography>
                        <Typography variant="body1">
                          {matchScore.summary || t("hrDashboard.shortlist.noSummary")}
                        </Typography>
                      </Stack>
                    </Paper>
                  </Stack>

                  <Divider />

                  <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                    <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                      <Typography variant="subtitle1">
                        {t("hrDashboard.shortlist.matchedTitle")}
                      </Typography>
                      {renderStringList(matchedRequirements, t("hrDashboard.shortlist.noItems"))}
                    </Paper>
                    <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                      <Typography variant="subtitle1">
                        {t("hrDashboard.shortlist.missingTitle")}
                      </Typography>
                      {renderStringList(missingRequirements, t("hrDashboard.shortlist.noItems"))}
                    </Paper>
                  </Stack>

                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="subtitle1">
                      {t("hrDashboard.shortlist.evidenceTitle")}
                    </Typography>
                    {matchScoreEvidence.length === 0 ? (
                      <Typography variant="body2" color="text.secondary">
                        {t("hrDashboard.shortlist.noEvidence")}
                      </Typography>
                    ) : (
                      <List dense disablePadding>
                        {matchScoreEvidence.map((item) => (
                          <ListItem
                            key={`${item.requirement}:${item.snippet}`}
                            disableGutters
                            alignItems="flex-start"
                          >
                            <ListItemText
                              primary={`${item.requirement}: ${item.snippet}`}
                              secondary={item.source_field || undefined}
                            />
                          </ListItem>
                        ))}
                      </List>
                    )}
                  </Paper>
                </Stack>
              ) : null}
            </Stack>
          ) : null}
        </Stack>
      </Paper>
    </Stack>
  );
}
