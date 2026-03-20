import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Chip,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import {
  cancelInterview,
  createInterview,
  getInterviewFeedbackSummary,
  getMe,
  listCandidateProfiles,
  listInterviews,
  listPipelineTransitions,
  listVacancies,
  putMyInterviewFeedback,
  resendInterviewInvite,
  rescheduleInterview,
  type HRInterviewListResponse,
  type HRInterviewResponse,
  type InterviewFeedbackRecommendation,
  type InterviewFeedbackUpsertRequest,
} from "../../api";
import { readAuthSession } from "../../app/auth/session";
import { PageHero } from "../../components/PageHero";
import { HrWorkspaceNav } from "./HrWorkspaceNav";
import {
  FEEDBACK_RECOMMENDATION_OPTIONS,
  FEEDBACK_SCORE_OPTIONS,
  INTERVIEW_POLL_INTERVAL_MS,
  type FeedbackState,
  createEmptyInterviewDraft,
  createEmptyInterviewerFeedbackDraft,
  formatDateTime,
  formatInterviewDateTime,
  findFeedbackItemForInterviewer,
  hasInterviewFeedbackWindowOpened,
  isCurrentUserAssignedInterviewer,
  renderStringList,
  resolveInterviewApiError,
  resolveInterviewStatusChipColor,
  resolveInterviewSyncChipColor,
  resolveFeedbackEditorBlockedReason,
  buildFeedbackDraftFromItem,
  buildFeedbackGateMessage,
  buildInterviewCreatePayload,
  buildInterviewDraftFromResponse,
  buildInterviewFeedbackPayload,
  buildInterviewReschedulePayload,
} from "./hrWorkspaceShared";

/**
 * Focused interview scheduling and feedback page for the HR workspace.
 */
export function HrInterviewsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const session = readAuthSession();
  const accessToken = session.accessToken;
  const [selectedVacancyId, setSelectedVacancyId] = useState("");
  const [selectedCandidateId, setSelectedCandidateId] = useState("");
  const [interviewDraft, setInterviewDraft] = useState(createEmptyInterviewDraft);
  const [feedbackDraft, setFeedbackDraft] = useState(createEmptyInterviewerFeedbackDraft);
  const [interviewFeedback, setInterviewFeedback] = useState<FeedbackState | null>(null);
  const [feedbackPanelState, setFeedbackPanelState] = useState<FeedbackState | null>(null);

  const vacanciesQuery = useQuery({
    queryKey: ["hr-vacancies", accessToken],
    queryFn: () => listVacancies(),
    enabled: Boolean(accessToken),
  });

  const candidatesQuery = useQuery({
    queryKey: ["hr-interview-candidates", accessToken, selectedVacancyId],
    queryFn: () =>
      listCandidateProfiles({
        limit: 20,
        offset: 0,
        vacancyId: selectedVacancyId || undefined,
      }),
    enabled: Boolean(accessToken),
  });

  const interviewsQuery = useQuery({
    queryKey: ["hr-interviews", accessToken, selectedVacancyId, selectedCandidateId],
    queryFn: () =>
      listInterviews(accessToken!, selectedVacancyId, {
        candidateId: selectedCandidateId,
      }),
    enabled: Boolean(accessToken && selectedVacancyId && selectedCandidateId),
    refetchInterval: (query) => {
      const payload = query.state.data as HRInterviewListResponse | undefined;
      const interview = selectInterviewState(payload?.items ?? []).latest;
      if (
        interview
        && (interview.calendar_sync_status === "queued"
          || interview.calendar_sync_status === "running")
      ) {
        return INTERVIEW_POLL_INTERVAL_MS;
      }
      return false;
    },
  });

  const interviewItems = interviewsQuery.data?.items ?? [];
  const interviewState = selectInterviewState(interviewItems);
  const activeInterview = interviewState.active;
  const latestInterview = interviewState.latest;
  const pipelineTransitionsQuery = useQuery({
    queryKey: ["hr-pipeline-history", accessToken, selectedVacancyId, selectedCandidateId],
    queryFn: () => listPipelineTransitions(selectedVacancyId, selectedCandidateId),
    enabled: Boolean(accessToken && selectedVacancyId && selectedCandidateId),
  });
  const currentPipelineStage = pipelineTransitionsQuery.data
    ? (pipelineTransitionsQuery.data.items[pipelineTransitionsQuery.data.items.length - 1]?.to_stage ?? null)
    : null;
  const meQueryKey = ["auth-me", accessToken];
  const feedbackSummaryQueryKey = [
    "hr-interview-feedback",
    accessToken,
    selectedVacancyId,
    latestInterview?.interview_id ?? "",
  ];

  const meQuery = useQuery({
    queryKey: meQueryKey,
    queryFn: () => getMe(accessToken!),
    enabled: Boolean(accessToken),
  });

  const feedbackSummaryQuery = useQuery({
    queryKey: feedbackSummaryQueryKey,
    queryFn: () =>
      getInterviewFeedbackSummary(accessToken!, selectedVacancyId, latestInterview!.interview_id),
    enabled: Boolean(accessToken && selectedVacancyId && latestInterview),
  });

  const vacancyItems = useMemo(() => vacanciesQuery.data?.items ?? [], [vacanciesQuery.data?.items]);
  const candidateItems = useMemo(() => candidatesQuery.data?.items ?? [], [candidatesQuery.data?.items]);
  const selectedVacancy =
    vacancyItems.find((item) => item.vacancy_id === selectedVacancyId) ?? null;
  const selectedCandidate =
    candidateItems.find((item) => item.candidate_id === selectedCandidateId) ?? null;
  const currentUser = meQuery.data ?? null;
  const currentUserCanWriteFeedback = isCurrentUserAssignedInterviewer(
    latestInterview,
    currentUser,
  );
  const currentUserFeedbackItem = findFeedbackItemForInterviewer(
    feedbackSummaryQuery.data ?? null,
    currentUser?.subject_id ?? null,
  );
  const feedbackWindowOpen = hasInterviewFeedbackWindowOpened(latestInterview);
  const feedbackEditorBlockedReason = resolveFeedbackEditorBlockedReason({
    latestInterview,
    currentPipelineStage,
    currentUserCanWriteFeedback,
    feedbackWindowOpen,
    t,
  });
  const selectedContextReady = Boolean(selectedVacancyId && selectedCandidateId);
  const currentUserFeedbackSummary = feedbackSummaryQuery.data ?? null;

  const createInterviewMutation = useMutation({
    mutationFn: () =>
      createInterview(
        accessToken!,
        selectedVacancyId,
        buildInterviewCreatePayload(interviewDraft, selectedCandidateId, t),
      ),
    onSuccess: (payload) => {
      setInterviewFeedback({ type: "success", message: t("hrDashboard.interviews.createSuccess") });
      queryClient.setQueryData(["hr-interviews", accessToken, selectedVacancyId, selectedCandidateId], {
        items: [payload],
      });
      void queryClient.invalidateQueries({
        queryKey: ["hr-interviews", accessToken, selectedVacancyId, selectedCandidateId],
      });
    },
    onError: (error: unknown) => {
      setInterviewFeedback({ type: "error", message: resolveInterviewApiError(error, t) });
    },
  });

  const rescheduleInterviewMutation = useMutation({
    mutationFn: (interviewId: string) =>
      rescheduleInterview(
        accessToken!,
        selectedVacancyId,
        interviewId,
        buildInterviewReschedulePayload(interviewDraft, t),
      ),
    onSuccess: (payload) => {
      setInterviewFeedback({
        type: "success",
        message: t("hrDashboard.interviews.rescheduleSuccess"),
      });
      queryClient.setQueryData(["hr-interviews", accessToken, selectedVacancyId, selectedCandidateId], {
        items: [payload],
      });
      void queryClient.invalidateQueries({
        queryKey: ["hr-interviews", accessToken, selectedVacancyId, selectedCandidateId],
      });
    },
    onError: (error: unknown) => {
      setInterviewFeedback({ type: "error", message: resolveInterviewApiError(error, t) });
    },
  });

  const cancelInterviewMutation = useMutation({
    mutationFn: (interviewId: string) =>
      cancelInterview(accessToken!, selectedVacancyId, interviewId, {
        cancel_reason_code: interviewDraft.cancelReasonCode.trim() || "cancelled_by_staff",
      }),
    onSuccess: (payload) => {
      setInterviewFeedback({ type: "success", message: t("hrDashboard.interviews.cancelSuccess") });
      queryClient.setQueryData(["hr-interviews", accessToken, selectedVacancyId, selectedCandidateId], {
        items: [payload],
      });
      void queryClient.invalidateQueries({
        queryKey: ["hr-interviews", accessToken, selectedVacancyId, selectedCandidateId],
      });
    },
    onError: (error: unknown) => {
      setInterviewFeedback({ type: "error", message: resolveInterviewApiError(error, t) });
    },
  });

  const resendInterviewInviteMutation = useMutation({
    mutationFn: (interviewId: string) =>
      resendInterviewInvite(accessToken!, selectedVacancyId, interviewId),
    onSuccess: (payload) => {
      setInterviewFeedback({
        type: "success",
        message: t("hrDashboard.interviews.resendSuccess"),
      });
      queryClient.setQueryData(["hr-interviews", accessToken, selectedVacancyId, selectedCandidateId], {
        items: [payload],
      });
      void queryClient.invalidateQueries({
        queryKey: ["hr-interviews", accessToken, selectedVacancyId, selectedCandidateId],
      });
    },
    onError: (error: unknown) => {
      setInterviewFeedback({ type: "error", message: resolveInterviewApiError(error, t) });
    },
  });

  const putInterviewFeedbackMutation = useMutation({
    mutationFn: (payload: InterviewFeedbackUpsertRequest) =>
      putMyInterviewFeedback(accessToken!, selectedVacancyId, latestInterview!.interview_id, payload),
    onSuccess: async () => {
      setFeedbackPanelState({
        type: "success",
        message: t("hrDashboard.interviews.feedback.submitSuccess"),
      });
      await queryClient.invalidateQueries({ queryKey: feedbackSummaryQueryKey });
    },
    onError: (error: unknown) => {
      setFeedbackPanelState({ type: "error", message: resolveInterviewApiError(error, t) });
    },
  });

  useEffect(() => {
    if (!latestInterview) {
      setInterviewDraft(createEmptyInterviewDraft());
      return;
    }
    setInterviewDraft(buildInterviewDraftFromResponse(latestInterview));
  }, [latestInterview]);

  useEffect(() => {
    if (!latestInterview) {
      setFeedbackDraft(createEmptyInterviewerFeedbackDraft());
      return;
    }
    setFeedbackDraft(buildFeedbackDraftFromItem(currentUserFeedbackItem));
  }, [currentUserFeedbackItem, latestInterview]);

  const handleCreateInterview = () => {
    if (!selectedVacancyId || !selectedCandidateId) {
      setInterviewFeedback({
        type: "error",
        message: t("hrDashboard.interviews.errors.selectContext"),
      });
      return;
    }
    setInterviewFeedback(null);
    createInterviewMutation.mutate();
  };

  const handleRescheduleInterview = () => {
    if (!activeInterview) {
      setInterviewFeedback({
        type: "error",
        message: t("hrDashboard.interviews.errors.noActiveInterview"),
      });
      return;
    }
    setInterviewFeedback(null);
    rescheduleInterviewMutation.mutate(activeInterview.interview_id);
  };

  const handleCancelInterview = () => {
    if (!activeInterview) {
      setInterviewFeedback({
        type: "error",
        message: t("hrDashboard.interviews.errors.noActiveInterview"),
      });
      return;
    }
    setInterviewFeedback(null);
    cancelInterviewMutation.mutate(activeInterview.interview_id);
  };

  const handleResendInterviewInvite = () => {
    if (!activeInterview) {
      setInterviewFeedback({
        type: "error",
        message: t("hrDashboard.interviews.errors.noActiveInterview"),
      });
      return;
    }
    setInterviewFeedback(null);
    resendInterviewInviteMutation.mutate(activeInterview.interview_id);
  };

  const handleSubmitInterviewFeedback = () => {
    if (!latestInterview || !selectedVacancyId) {
      setFeedbackPanelState({
        type: "error",
        message: t("hrDashboard.interviews.feedback.errors.selectContext"),
      });
      return;
    }
    if (feedbackEditorBlockedReason) {
      setFeedbackPanelState({
        type: "error",
        message: feedbackEditorBlockedReason,
      });
      return;
    }
    try {
      const payload = buildInterviewFeedbackPayload(feedbackDraft, t);
      setFeedbackPanelState(null);
      putInterviewFeedbackMutation.mutate(payload);
    } catch (error) {
      setFeedbackPanelState({
        type: "error",
        message: resolveInterviewApiError(error, t),
      });
    }
  };

  if (!accessToken) {
    return <Alert severity="info">{t("hrDashboard.authRequired")}</Alert>;
  }

  return (
    <Stack spacing={3}>
      <PageHero
        eyebrow={t("hrDashboard.title")}
        title={t("hrWorkspacePages.interviews.title")}
        description={t("hrWorkspacePages.interviews.subtitle")}
        imageSrc="/images/careers-team.jpg"
        imageAlt={t("hrDashboard.interviews.title")}
        chips={[
          t("hrDashboard.interviews.title"),
          t("hrDashboard.interviews.feedback.title"),
          t("hrWorkspaceNav.workbench"),
        ]}
      />

      <HrWorkspaceNav />

      {interviewFeedback ? (
        <Alert severity={interviewFeedback.type}>{interviewFeedback.message}</Alert>
      ) : null}

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField
              select
              label={t("hrWorkspacePages.interviews.vacancyLabel")}
              value={selectedVacancyId}
              onChange={(event) => {
                setSelectedVacancyId(event.target.value);
                setSelectedCandidateId("");
                setInterviewFeedback(null);
                setFeedbackPanelState(null);
                setInterviewDraft(createEmptyInterviewDraft());
                setFeedbackDraft(createEmptyInterviewerFeedbackDraft());
              }}
              fullWidth
              SelectProps={{ native: true }}
            >
              <option value="">{t("hrWorkspacePages.interviews.vacancyPlaceholder")}</option>
              {vacancyItems.map((vacancy) => (
                <option key={vacancy.vacancy_id} value={vacancy.vacancy_id}>
                  {vacancy.title}
                </option>
              ))}
            </TextField>
            <TextField
              select
              label={t("hrDashboard.fields.candidate")}
              value={selectedCandidateId}
              onChange={(event) => {
                setSelectedCandidateId(event.target.value);
                setInterviewFeedback(null);
                setFeedbackPanelState(null);
                setInterviewDraft(createEmptyInterviewDraft());
                setFeedbackDraft(createEmptyInterviewerFeedbackDraft());
              }}
              fullWidth
              SelectProps={{ native: true }}
            >
              <option value="">{t("hrDashboard.selectCandidateAction")}</option>
              {candidateItems.map((candidate) => (
                <option key={candidate.candidate_id} value={candidate.candidate_id}>
                  {candidate.first_name} {candidate.last_name} ({candidate.email})
                </option>
              ))}
            </TextField>
          </Stack>

          {selectedVacancy ? (
            <Typography variant="body2" color="text.secondary">
              {t("hrDashboard.selectedVacancySummary", {
                vacancyTitle: selectedVacancy.title,
                vacancyId: selectedVacancy.vacancy_id,
              })}
            </Typography>
          ) : null}

          {selectedCandidate ? (
            <Typography variant="body2" color="text.secondary">
              {t("hrDashboard.selectedCandidateSummary", {
                candidateName: `${selectedCandidate.first_name} ${selectedCandidate.last_name}`,
                candidateId: selectedCandidate.candidate_id,
              })}
            </Typography>
          ) : null}
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
              <Typography variant="h6">{t("hrDashboard.interviews.title")}</Typography>
              <Typography variant="body2" color="text.secondary">
                {t("hrDashboard.interviews.subtitle")}
              </Typography>
            </Stack>
            {!activeInterview ? (
              <Button
                variant="contained"
                onClick={handleCreateInterview}
                disabled={!selectedContextReady || createInterviewMutation.isPending}
              >
                {createInterviewMutation.isPending
                  ? t("hrDashboard.interviews.createPending")
                  : t("hrDashboard.interviews.createAction")}
              </Button>
            ) : (
              <Button
                variant="contained"
                onClick={handleRescheduleInterview}
                disabled={rescheduleInterviewMutation.isPending}
              >
                {rescheduleInterviewMutation.isPending
                  ? t("hrDashboard.interviews.reschedulePending")
                  : t("hrDashboard.interviews.rescheduleAction")}
              </Button>
            )}
          </Stack>

          {interviewFeedback ? (
            <Alert severity={interviewFeedback.type}>{interviewFeedback.message}</Alert>
          ) : null}

          {!selectedContextReady ? (
            <Alert severity="info">{t("hrDashboard.interviews.inactive")}</Alert>
          ) : null}

          {selectedContextReady ? (
            <Stack spacing={2}>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField
                  label={t("hrDashboard.interviews.fields.start")}
                  type="datetime-local"
                  value={interviewDraft.scheduledStartLocal}
                  onChange={(event) =>
                    setInterviewDraft((prev) => ({
                      ...prev,
                      scheduledStartLocal: event.target.value,
                    }))
                  }
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                />
                <TextField
                  label={t("hrDashboard.interviews.fields.end")}
                  type="datetime-local"
                  value={interviewDraft.scheduledEndLocal}
                  onChange={(event) =>
                    setInterviewDraft((prev) => ({
                      ...prev,
                      scheduledEndLocal: event.target.value,
                    }))
                  }
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                />
              </Stack>

              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField
                  label={t("hrDashboard.interviews.fields.timezone")}
                  value={interviewDraft.timezone}
                  onChange={(event) =>
                    setInterviewDraft((prev) => ({
                      ...prev,
                      timezone: event.target.value,
                    }))
                  }
                  fullWidth
                />
                <TextField
                  select
                  label={t("hrDashboard.interviews.fields.locationKind")}
                  value={interviewDraft.locationKind}
                  onChange={(event) =>
                    setInterviewDraft((prev) => ({
                      ...prev,
                      locationKind: event.target.value as InterviewDraft["locationKind"],
                    }))
                  }
                  fullWidth
                  SelectProps={{ native: true }}
                >
                  <option value="google_meet">
                    {t("hrDashboard.interviews.locationKind.google_meet")}
                  </option>
                  <option value="onsite">
                    {t("hrDashboard.interviews.locationKind.onsite")}
                  </option>
                  <option value="phone">
                    {t("hrDashboard.interviews.locationKind.phone")}
                  </option>
                </TextField>
              </Stack>

              <TextField
                label={t("hrDashboard.interviews.fields.locationDetails")}
                value={interviewDraft.locationDetails}
                onChange={(event) =>
                  setInterviewDraft((prev) => ({
                    ...prev,
                    locationDetails: event.target.value,
                  }))
                }
                multiline
                minRows={2}
              />
              <TextField
                label={t("hrDashboard.interviews.fields.interviewerStaffIds")}
                value={interviewDraft.interviewerStaffIdsInput}
                onChange={(event) =>
                  setInterviewDraft((prev) => ({
                    ...prev,
                    interviewerStaffIdsInput: event.target.value,
                  }))
                }
                helperText={t("hrDashboard.interviews.fields.interviewerStaffIdsHelp")}
              />
              <TextField
                label={t("hrDashboard.interviews.fields.cancelReasonCode")}
                value={interviewDraft.cancelReasonCode}
                onChange={(event) =>
                  setInterviewDraft((prev) => ({
                    ...prev,
                    cancelReasonCode: event.target.value,
                  }))
                }
                helperText={t("hrDashboard.interviews.fields.cancelReasonCodeHelp")}
              />

              {interviewsQuery.isLoading && !latestInterview ? (
                <Typography variant="body2">{t("hrDashboard.interviews.loading")}</Typography>
              ) : null}
              {interviewsQuery.isError ? (
                <Alert severity="error">
                  {resolveInterviewApiError(interviewsQuery.error, t)}
                </Alert>
              ) : null}
              {!interviewsQuery.isError && !interviewsQuery.isLoading && !latestInterview ? (
                <Alert severity="info">{t("hrDashboard.interviews.empty")}</Alert>
              ) : null}

              {latestInterview ? (
                <Stack spacing={2}>
                  <Stack
                    direction={{ xs: "column", md: "row" }}
                    spacing={1}
                    alignItems={{ xs: "flex-start", md: "center" }}
                  >
                    <Typography variant="body2" color="text.secondary">
                      {t("hrDashboard.interviews.statusLabel")}
                    </Typography>
                    <Chip
                      size="small"
                      label={t(`hrDashboard.interviews.status.${latestInterview.status}`)}
                      color={resolveInterviewStatusChipColor(latestInterview.status)}
                    />
                    <Chip
                      size="small"
                      label={t(
                        `hrDashboard.interviews.syncStatus.${latestInterview.calendar_sync_status}`,
                      )}
                      color={resolveInterviewSyncChipColor(latestInterview.calendar_sync_status)}
                    />
                    <Typography variant="body2" color="text.secondary">
                      {t("hrDashboard.interviews.scheduleVersion", {
                        value: latestInterview.schedule_version,
                      })}
                    </Typography>
                  </Stack>

                  <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                    <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                      <Typography variant="subtitle2">
                        {t("hrDashboard.interviews.fields.start")}
                      </Typography>
                      <Typography variant="body2">
                        {formatInterviewDateTime(
                          latestInterview.scheduled_start_at,
                          latestInterview.timezone,
                        )}
                      </Typography>
                    </Paper>
                    <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                      <Typography variant="subtitle2">
                        {t("hrDashboard.interviews.fields.end")}
                      </Typography>
                      <Typography variant="body2">
                        {formatInterviewDateTime(
                          latestInterview.scheduled_end_at,
                          latestInterview.timezone,
                        )}
                      </Typography>
                    </Paper>
                    <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                      <Typography variant="subtitle2">
                        {t("hrDashboard.interviews.fields.timezone")}
                      </Typography>
                      <Typography variant="body2">{latestInterview.timezone}</Typography>
                    </Paper>
                  </Stack>

                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Stack spacing={1}>
                      <Typography variant="subtitle2">
                        {t("hrDashboard.interviews.fields.locationDetails")}
                      </Typography>
                      <Typography variant="body2">
                        {latestInterview.location_details
                          || t("hrDashboard.interviews.noLocationDetails")}
                      </Typography>
                      {latestInterview.candidate_invite_url ? (
                        <TextField
                          label={t("hrDashboard.interviews.fields.inviteUrl")}
                          value={latestInterview.candidate_invite_url}
                          InputProps={{ readOnly: true }}
                          fullWidth
                        />
                      ) : null}
                      {latestInterview.candidate_token_expires_at ? (
                        <Typography variant="body2" color="text.secondary">
                          {t("hrDashboard.interviews.tokenExpiresAt", {
                            value: formatInterviewDateTime(
                              latestInterview.candidate_token_expires_at,
                              latestInterview.timezone,
                            ),
                          })}
                        </Typography>
                      ) : null}
                    </Stack>
                  </Paper>
                </Stack>
              ) : null}

              <Paper variant="outlined" sx={{ p: 2 }}>
                <Stack spacing={2}>
                  <Stack spacing={0.5}>
                    <Typography variant="subtitle1">
                      {t("hrDashboard.interviews.feedback.title")}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {t("hrDashboard.interviews.feedback.subtitle")}
                    </Typography>
                  </Stack>

                  {feedbackSummaryQuery.isLoading ? (
                    <Typography variant="body2">
                      {t("hrDashboard.interviews.feedback.loading")}
                    </Typography>
                  ) : null}

                  {feedbackSummaryQuery.isError ? (
                    <Alert severity="error">
                      {resolveInterviewApiError(feedbackSummaryQuery.error, t)}
                    </Alert>
                  ) : null}

                  {currentUserFeedbackSummary ? (
                    <Stack spacing={2}>
                      <Alert
                        severity={currentUserFeedbackSummary.gate_status === "passed" ? "success" : "warning"}
                      >
                        {buildFeedbackGateMessage(currentUserFeedbackSummary, t)}
                      </Alert>

                      <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                        <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                          <Typography variant="overline">
                            {t("hrDashboard.interviews.feedback.requiredCount")}
                          </Typography>
                          <Typography variant="h5">
                            {currentUserFeedbackSummary.required_interviewer_count}
                          </Typography>
                        </Paper>
                        <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                          <Typography variant="overline">
                            {t("hrDashboard.interviews.feedback.submittedCount")}
                          </Typography>
                          <Typography variant="h5">
                            {currentUserFeedbackSummary.submitted_count}
                          </Typography>
                        </Paper>
                        <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                          <Typography variant="overline">
                            {t("hrDashboard.interviews.feedback.missingCount")}
                          </Typography>
                          <Typography variant="h5">
                            {currentUserFeedbackSummary.missing_interviewer_ids.length}
                          </Typography>
                        </Paper>
                      </Stack>

                      <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                        <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                          <Typography variant="subtitle2">
                            {t("hrDashboard.interviews.feedback.missingTitle")}
                          </Typography>
                          {renderStringList(
                            currentUserFeedbackSummary.missing_interviewer_ids,
                            t("hrDashboard.interviews.feedback.noMissing"),
                          )}
                        </Paper>
                        <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                          <Typography variant="subtitle2">
                            {t("hrDashboard.interviews.feedback.submittedTitle")}
                          </Typography>
                          {currentUserFeedbackSummary.items.length === 0 ? (
                            <Typography variant="body2" color="text.secondary">
                              {t("hrDashboard.interviews.feedback.empty")}
                            </Typography>
                          ) : (
                            <Stack spacing={1.5} sx={{ mt: 1 }}>
                              {currentUserFeedbackSummary.items.map((item) => (
                                <Paper key={item.feedback_id} variant="outlined" sx={{ p: 2 }}>
                                  <Stack spacing={0.75}>
                                    <Stack
                                      direction={{ xs: "column", md: "row" }}
                                      spacing={1}
                                      alignItems={{ xs: "flex-start", md: "center" }}
                                    >
                                      <Typography variant="body2" fontWeight={600}>
                                        {item.interviewer_staff_id}
                                      </Typography>
                                      <Chip
                                        size="small"
                                        label={t(
                                          `hrDashboard.interviews.feedback.recommendation.${item.recommendation}`,
                                        )}
                                      />
                                      <Typography variant="body2" color="text.secondary">
                                        {t("hrDashboard.interviews.feedback.updatedAt", {
                                          value: formatDateTime(item.updated_at),
                                        })}
                                      </Typography>
                                    </Stack>
                                    <Typography variant="body2">
                                      {t("hrDashboard.interviews.feedback.notes.strengths")}
                                      {`: ${item.strengths_note}`}
                                    </Typography>
                                    <Typography variant="body2">
                                      {t("hrDashboard.interviews.feedback.notes.concerns")}
                                      {`: ${item.concerns_note}`}
                                    </Typography>
                                    <Typography variant="body2">
                                      {t("hrDashboard.interviews.feedback.notes.evidence")}
                                      {`: ${item.evidence_note}`}
                                    </Typography>
                                  </Stack>
                                </Paper>
                              ))}
                            </Stack>
                          )}
                        </Paper>
                      </Stack>

                      <Paper variant="outlined" sx={{ p: 2 }}>
                        <Stack spacing={2}>
                          <Stack spacing={0.5}>
                            <Typography variant="subtitle2">
                              {t("hrDashboard.interviews.feedback.formTitle")}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              {t("hrDashboard.interviews.feedback.formSubtitle")}
                            </Typography>
                          </Stack>

                          {feedbackPanelState ? (
                            <Alert severity={feedbackPanelState.type}>
                              {feedbackPanelState.message}
                            </Alert>
                          ) : null}

                          {meQuery.isLoading ? (
                            <Typography variant="body2">
                              {t("hrDashboard.interviews.feedback.loadingCurrentUser")}
                            </Typography>
                          ) : null}

                          {meQuery.isError ? (
                            <Alert severity="error">
                              {resolveInterviewApiError(meQuery.error, t)}
                            </Alert>
                          ) : null}

                          {!currentUserCanWriteFeedback && !meQuery.isLoading ? (
                            <Alert severity="info">
                              {t("hrDashboard.interviews.feedback.notAssigned")}
                            </Alert>
                          ) : null}

                          {currentUserCanWriteFeedback && feedbackEditorBlockedReason ? (
                            <Alert severity="warning">{feedbackEditorBlockedReason}</Alert>
                          ) : null}

                          {currentUserCanWriteFeedback ? (
                            <Stack spacing={2}>
                              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                                <TextField
                                  select
                                  label={t(
                                    "hrDashboard.interviews.feedback.fields.requirementsMatchScore",
                                  )}
                                  value={feedbackDraft.requirementsMatchScore}
                                  onChange={(event) =>
                                    setFeedbackDraft((prev) => ({
                                      ...prev,
                                      requirementsMatchScore: Number(event.target.value),
                                    }))
                                  }
                                  disabled={Boolean(feedbackEditorBlockedReason)}
                                  fullWidth
                                  SelectProps={{ native: true }}
                                >
                                  {FEEDBACK_SCORE_OPTIONS.map((value) => (
                                    <option key={value} value={value}>
                                      {value}
                                    </option>
                                  ))}
                                </TextField>
                                <TextField
                                  select
                                  label={t(
                                    "hrDashboard.interviews.feedback.fields.communicationScore",
                                  )}
                                  value={feedbackDraft.communicationScore}
                                  onChange={(event) =>
                                    setFeedbackDraft((prev) => ({
                                      ...prev,
                                      communicationScore: Number(event.target.value),
                                    }))
                                  }
                                  disabled={Boolean(feedbackEditorBlockedReason)}
                                  fullWidth
                                  SelectProps={{ native: true }}
                                >
                                  {FEEDBACK_SCORE_OPTIONS.map((value) => (
                                    <option key={value} value={value}>
                                      {value}
                                    </option>
                                  ))}
                                </TextField>
                              </Stack>

                              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                                <TextField
                                  select
                                  label={t(
                                    "hrDashboard.interviews.feedback.fields.problemSolvingScore",
                                  )}
                                  value={feedbackDraft.problemSolvingScore}
                                  onChange={(event) =>
                                    setFeedbackDraft((prev) => ({
                                      ...prev,
                                      problemSolvingScore: Number(event.target.value),
                                    }))
                                  }
                                  disabled={Boolean(feedbackEditorBlockedReason)}
                                  fullWidth
                                  SelectProps={{ native: true }}
                                >
                                  {FEEDBACK_SCORE_OPTIONS.map((value) => (
                                    <option key={value} value={value}>
                                      {value}
                                    </option>
                                  ))}
                                </TextField>
                                <TextField
                                  select
                                  label={t(
                                    "hrDashboard.interviews.feedback.fields.collaborationScore",
                                  )}
                                  value={feedbackDraft.collaborationScore}
                                  onChange={(event) =>
                                    setFeedbackDraft((prev) => ({
                                      ...prev,
                                      collaborationScore: Number(event.target.value),
                                    }))
                                  }
                                  disabled={Boolean(feedbackEditorBlockedReason)}
                                  fullWidth
                                  SelectProps={{ native: true }}
                                >
                                  {FEEDBACK_SCORE_OPTIONS.map((value) => (
                                    <option key={value} value={value}>
                                      {value}
                                    </option>
                                  ))}
                                </TextField>
                              </Stack>

                              <TextField
                                select
                                label={t("hrDashboard.interviews.feedback.fields.recommendation")}
                                value={feedbackDraft.recommendation}
                                onChange={(event) =>
                                  setFeedbackDraft((prev) => ({
                                    ...prev,
                                    recommendation: event.target.value as InterviewFeedbackRecommendation,
                                  }))
                                }
                                disabled={Boolean(feedbackEditorBlockedReason)}
                                SelectProps={{ native: true }}
                                fullWidth
                              >
                                {FEEDBACK_RECOMMENDATION_OPTIONS.map((recommendation) => (
                                  <option key={recommendation} value={recommendation}>
                                    {t(`hrDashboard.interviews.feedback.recommendation.${recommendation}`)}
                                  </option>
                                ))}
                              </TextField>

                              <TextField
                                label={t("hrDashboard.interviews.feedback.notes.strengths")}
                                value={feedbackDraft.strengthsNote}
                                onChange={(event) =>
                                  setFeedbackDraft((prev) => ({
                                    ...prev,
                                    strengthsNote: event.target.value,
                                  }))
                                }
                                disabled={Boolean(feedbackEditorBlockedReason)}
                                multiline
                                minRows={2}
                                fullWidth
                              />
                              <TextField
                                label={t("hrDashboard.interviews.feedback.notes.concerns")}
                                value={feedbackDraft.concernsNote}
                                onChange={(event) =>
                                  setFeedbackDraft((prev) => ({
                                    ...prev,
                                    concernsNote: event.target.value,
                                  }))
                                }
                                disabled={Boolean(feedbackEditorBlockedReason)}
                                multiline
                                minRows={2}
                                fullWidth
                              />
                              <TextField
                                label={t("hrDashboard.interviews.feedback.notes.evidence")}
                                value={feedbackDraft.evidenceNote}
                                onChange={(event) =>
                                  setFeedbackDraft((prev) => ({
                                    ...prev,
                                    evidenceNote: event.target.value,
                                  }))
                                }
                                disabled={Boolean(feedbackEditorBlockedReason)}
                                multiline
                                minRows={2}
                                fullWidth
                              />

                              <Button
                                variant="contained"
                                onClick={handleSubmitInterviewFeedback}
                                disabled={
                                  putInterviewFeedbackMutation.isPending
                                  || Boolean(feedbackEditorBlockedReason)
                                }
                              >
                                {putInterviewFeedbackMutation.isPending
                                  ? t("hrDashboard.interviews.feedback.submitPending")
                                  : t("hrDashboard.interviews.feedback.submitAction")}
                              </Button>
                            </Stack>
                          ) : null}
                        </Stack>
                      </Paper>
                    </Stack>
                  ) : null}
                </Stack>
              </Paper>

              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <Button
                  variant="outlined"
                  color="error"
                  onClick={handleCancelInterview}
                  disabled={!activeInterview || cancelInterviewMutation.isPending}
                >
                  {cancelInterviewMutation.isPending
                    ? t("hrDashboard.interviews.cancelPending")
                    : t("hrDashboard.interviews.cancelAction")}
                </Button>
                <Button
                  variant="outlined"
                  onClick={handleResendInterviewInvite}
                  disabled={!activeInterview || resendInterviewInviteMutation.isPending}
                >
                  {resendInterviewInviteMutation.isPending
                    ? t("hrDashboard.interviews.resendPending")
                    : t("hrDashboard.interviews.resendAction")}
                </Button>
              </Stack>
            </Stack>
          ) : null}
        </Stack>
      </Paper>
    </Stack>
  );
}

function selectInterviewState(items: HRInterviewResponse[]): {
  active: HRInterviewResponse | null;
  latest: HRInterviewResponse | null;
} {
  const active = items.find((item) => item.status !== "cancelled") ?? null;
  return {
    active,
    latest: active ?? items[0] ?? null,
  };
}
