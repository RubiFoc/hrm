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
  acceptOffer,
  declineOffer,
  getInterviewFeedbackSummary,
  getOffer,
  listCandidateProfiles,
  listInterviews,
  listPipelineTransitions,
  listVacancies,
  sendOffer,
  upsertOffer,
} from "../../api";
import { readAuthSession } from "../../app/auth/session";
import { PageHero } from "../../components/PageHero";
import { HrWorkspaceNav } from "./HrWorkspaceNav";
import {
  type FeedbackState,
  createEmptyOfferDraft,
  buildFeedbackGateMessage,
  buildOfferDraftFromResponse,
  buildOfferGateAlertMessage,
  buildOfferPrerequisiteMessage,
  buildOfferStatusHint,
  buildOfferUpsertPayload,
  formatDateTime,
  isOfferStageNotActiveError,
  resolveOfferHintSeverity,
  resolveOfferStatusChipColor,
  resolveRecruitmentApiError,
  selectInterviewState,
} from "./hrWorkspaceShared";

/**
 * Focused offer lifecycle page for the HR workspace.
 */
export function HrOffersPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const session = readAuthSession();
  const accessToken = session.accessToken;
  const [selectedVacancyId, setSelectedVacancyId] = useState("");
  const [selectedCandidateId, setSelectedCandidateId] = useState("");
  const [offerDraft, setOfferDraft] = useState(createEmptyOfferDraft);
  const [offerPanelState, setOfferPanelState] = useState<FeedbackState | null>(null);

  const vacanciesQuery = useQuery({
    queryKey: ["hr-vacancies", accessToken],
    queryFn: () => listVacancies(),
    enabled: Boolean(accessToken),
  });

  const candidatesQuery = useQuery({
    queryKey: ["hr-offer-candidates", accessToken, selectedVacancyId],
    queryFn: () =>
      listCandidateProfiles({
        limit: 20,
        offset: 0,
        vacancyId: selectedVacancyId || undefined,
      }),
    enabled: Boolean(accessToken),
  });

  const transitionsQuery = useQuery({
    queryKey: ["hr-pipeline-history", accessToken, selectedVacancyId, selectedCandidateId],
    queryFn: () => listPipelineTransitions(selectedVacancyId, selectedCandidateId),
    enabled: Boolean(accessToken && selectedVacancyId && selectedCandidateId),
  });

  const interviewQuery = useQuery({
    queryKey: ["hr-interviews", accessToken, selectedVacancyId, selectedCandidateId],
    queryFn: () =>
      listInterviews(accessToken!, selectedVacancyId, {
        candidateId: selectedCandidateId,
      }),
    enabled: Boolean(accessToken && selectedVacancyId && selectedCandidateId),
  });

  const interviewItems = interviewQuery.data?.items ?? [];
  const interviewState = selectInterviewState(interviewItems);
  const latestInterview = interviewState.latest;
  const feedbackSummaryQueryKey = [
    "hr-interview-feedback",
    accessToken,
    selectedVacancyId,
    latestInterview?.interview_id ?? "",
  ];

  const feedbackSummaryQuery = useQuery({
    queryKey: feedbackSummaryQueryKey,
    queryFn: () =>
      getInterviewFeedbackSummary(accessToken!, selectedVacancyId, latestInterview!.interview_id),
    enabled: Boolean(accessToken && selectedVacancyId && latestInterview),
  });

  const offerQuery = useQuery({
    queryKey: ["hr-offer", accessToken, selectedVacancyId, selectedCandidateId],
    queryFn: () => getOffer(accessToken!, selectedVacancyId, selectedCandidateId),
    enabled: Boolean(accessToken && selectedVacancyId && selectedCandidateId),
    retry: false,
  });

  const vacancyItems = useMemo(() => vacanciesQuery.data?.items ?? [], [vacanciesQuery.data?.items]);
  const candidateItems = useMemo(() => candidatesQuery.data?.items ?? [], [candidatesQuery.data?.items]);
  const selectedVacancy =
    vacancyItems.find((item) => item.vacancy_id === selectedVacancyId) ?? null;
  const selectedCandidate =
    candidateItems.find((item) => item.candidate_id === selectedCandidateId) ?? null;
  const currentPipelineStage = transitionsQuery.data
    ? (transitionsQuery.data.items[transitionsQuery.data.items.length - 1]?.to_stage ?? null)
    : null;
  const feedbackSummary = feedbackSummaryQuery.data ?? null;
  const offer = offerQuery.data ?? null;
  const offerStatus = offer?.status ?? "draft";
  const offerReadOnly = currentPipelineStage !== "offer" || offerStatus !== "draft";
  const offerPrerequisiteMessage = buildOfferPrerequisiteMessage({
    currentPipelineStage,
    feedbackSummary,
    offerQueryError: offerQuery.error,
    t,
  });
  const offerPrerequisiteSeverity =
    currentPipelineStage === "interview" && feedbackSummary?.gate_status === "blocked"
      ? "warning"
      : "info";
  const offerStatusHint = buildOfferStatusHint(offerStatus, t);

  const upsertOfferMutation = useMutation({
    mutationFn: (payload: ReturnType<typeof buildOfferUpsertPayload>) =>
      upsertOffer(accessToken!, selectedVacancyId, selectedCandidateId, payload),
    onSuccess: async () => {
      setOfferPanelState({ type: "success", message: t("hrDashboard.offers.saveSuccess") });
      await queryClient.invalidateQueries({
        queryKey: ["hr-offer", accessToken, selectedVacancyId, selectedCandidateId],
      });
    },
    onError: (error: unknown) => {
      setOfferPanelState({ type: "error", message: resolveRecruitmentApiError(error, t) });
    },
  });

  const sendOfferMutation = useMutation({
    mutationFn: () => sendOffer(accessToken!, selectedVacancyId, selectedCandidateId),
    onSuccess: async () => {
      setOfferPanelState({ type: "success", message: t("hrDashboard.offers.sendSuccess") });
      await queryClient.invalidateQueries({
        queryKey: ["hr-offer", accessToken, selectedVacancyId, selectedCandidateId],
      });
    },
    onError: (error: unknown) => {
      setOfferPanelState({ type: "error", message: resolveRecruitmentApiError(error, t) });
    },
  });

  const acceptOfferMutation = useMutation({
    mutationFn: (note: string | null) =>
      acceptOffer(
        accessToken!,
        selectedVacancyId,
        selectedCandidateId,
        note ? { note } : undefined,
      ),
    onSuccess: async () => {
      setOfferPanelState({ type: "success", message: t("hrDashboard.offers.acceptSuccess") });
      await queryClient.invalidateQueries({
        queryKey: ["hr-offer", accessToken, selectedVacancyId, selectedCandidateId],
      });
      await queryClient.invalidateQueries({ queryKey: ["hr-pipeline-history"] });
    },
    onError: (error: unknown) => {
      setOfferPanelState({ type: "error", message: resolveRecruitmentApiError(error, t) });
    },
  });

  const declineOfferMutation = useMutation({
    mutationFn: (note: string | null) =>
      declineOffer(
        accessToken!,
        selectedVacancyId,
        selectedCandidateId,
        note ? { note } : undefined,
      ),
    onSuccess: async () => {
      setOfferPanelState({ type: "success", message: t("hrDashboard.offers.declineSuccess") });
      await queryClient.invalidateQueries({
        queryKey: ["hr-offer", accessToken, selectedVacancyId, selectedCandidateId],
      });
      await queryClient.invalidateQueries({ queryKey: ["hr-pipeline-history"] });
    },
    onError: (error: unknown) => {
      setOfferPanelState({ type: "error", message: resolveRecruitmentApiError(error, t) });
    },
  });

  useEffect(() => {
    setOfferDraft(buildOfferDraftFromResponse(offer));
  }, [offer]);

  const handleSaveOfferDraft = () => {
    if (!selectedVacancyId || !selectedCandidateId) {
      setOfferPanelState({
        type: "error",
        message: t("hrDashboard.offers.errors.selectContext"),
      });
      return;
    }
    try {
      setOfferPanelState(null);
      upsertOfferMutation.mutate(buildOfferUpsertPayload(offerDraft, t));
    } catch (error) {
      setOfferPanelState({ type: "error", message: resolveRecruitmentApiError(error, t) });
    }
  };

  const handleSendOffer = () => {
    if (!selectedVacancyId || !selectedCandidateId) {
      setOfferPanelState({
        type: "error",
        message: t("hrDashboard.offers.errors.selectContext"),
      });
      return;
    }
    setOfferPanelState(null);
    sendOfferMutation.mutate();
  };

  const handleAcceptOffer = () => {
    if (!selectedVacancyId || !selectedCandidateId) {
      setOfferPanelState({
        type: "error",
        message: t("hrDashboard.offers.errors.selectContext"),
      });
      return;
    }
    setOfferPanelState(null);
    acceptOfferMutation.mutate(offerDraft.decisionNote.trim() || null);
  };

  const handleDeclineOffer = () => {
    if (!selectedVacancyId || !selectedCandidateId) {
      setOfferPanelState({
        type: "error",
        message: t("hrDashboard.offers.errors.selectContext"),
      });
      return;
    }
    setOfferPanelState(null);
    declineOfferMutation.mutate(offerDraft.decisionNote.trim() || null);
  };

  if (!accessToken) {
    return <Alert severity="info">{t("hrDashboard.authRequired")}</Alert>;
  }

  return (
    <Stack spacing={3}>
      <PageHero
        eyebrow={t("hrDashboard.title")}
        title={t("hrWorkspacePages.offers.title")}
        description={t("hrWorkspacePages.offers.subtitle")}
        imageSrc="/images/candidate-portal.jpg"
        imageAlt={t("hrDashboard.offers.title")}
        chips={[
          t("hrDashboard.offers.title"),
          t("hrDashboard.offers.hints.sent"),
          t("hrWorkspaceNav.workbench"),
        ]}
      />

      <HrWorkspaceNav />

      {offerPanelState ? <Alert severity={offerPanelState.type}>{offerPanelState.message}</Alert> : null}

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField
              select
              label={t("hrWorkspacePages.offers.vacancyLabel")}
              value={selectedVacancyId}
              onChange={(event) => {
                setSelectedVacancyId(event.target.value);
                setSelectedCandidateId("");
                setOfferPanelState(null);
                setOfferDraft(createEmptyOfferDraft());
              }}
              fullWidth
              SelectProps={{ native: true }}
            >
              <option value="">{t("hrWorkspacePages.offers.vacancyPlaceholder")}</option>
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
                setOfferPanelState(null);
                setOfferDraft(createEmptyOfferDraft());
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
          <Stack spacing={0.5}>
            <Typography variant="h6">{t("hrDashboard.offers.title")}</Typography>
            <Typography variant="body2" color="text.secondary">
              {t("hrDashboard.offers.subtitle")}
            </Typography>
          </Stack>

          {offerPrerequisiteMessage ? (
            <Alert severity={offerPrerequisiteSeverity}>{offerPrerequisiteMessage}</Alert>
          ) : null}

          {offerQuery.isLoading && !offer ? (
            <Typography variant="body2">{t("hrDashboard.offers.loading")}</Typography>
          ) : null}

          {offerQuery.isError && !isOfferStageNotActiveError(offerQuery.error) ? (
            <Alert severity="error">{resolveRecruitmentApiError(offerQuery.error, t)}</Alert>
          ) : null}

          {offer ? (
            <Stack spacing={2}>
              <Stack direction={{ xs: "column", md: "row" }} spacing={1} alignItems={{ xs: "flex-start", md: "center" }}>
                <Typography variant="body2" color="text.secondary">
                  {t("hrDashboard.offers.stageLabel", {
                    stage: currentPipelineStage
                      ? t(`hrDashboard.stages.${currentPipelineStage}`)
                      : t("hrDashboard.timeline.start"),
                  })}
                </Typography>
                <Chip
                  size="small"
                  color={resolveOfferStatusChipColor(offer.status)}
                  label={t(`hrDashboard.offers.status.${offer.status}`)}
                />
                {offer.sent_at ? (
                  <Typography variant="body2" color="text.secondary">
                    {t("hrDashboard.offers.sentAt", { value: formatDateTime(offer.sent_at) })}
                  </Typography>
                ) : null}
                {offer.decision_at ? (
                  <Typography variant="body2" color="text.secondary">
                    {t("hrDashboard.offers.decisionAt", { value: formatDateTime(offer.decision_at) })}
                  </Typography>
                ) : null}
              </Stack>

              <Alert severity={resolveOfferHintSeverity(offer.status)}>
                {offerStatusHint}
              </Alert>

              {currentPipelineStage === "interview" && feedbackSummary ? (
                <Alert severity={feedbackSummary.gate_status === "passed" ? "success" : "warning"}>
                  {buildOfferGateAlertMessage(feedbackSummary, t)}
                </Alert>
              ) : null}

              {feedbackSummary ? (
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Stack spacing={1}>
                    <Typography variant="subtitle2">{t("hrDashboard.interviews.feedback.title")}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {buildFeedbackGateMessage(feedbackSummary, t)}
                    </Typography>
                  </Stack>
                </Paper>
              ) : null}

              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField
                  label={t("hrDashboard.offers.fields.proposedStartDate")}
                  type="date"
                  value={offerDraft.proposedStartDate}
                  onChange={(event) =>
                    setOfferDraft((prev) => ({
                      ...prev,
                      proposedStartDate: event.target.value,
                    }))
                  }
                  InputLabelProps={{ shrink: true }}
                  disabled={offerReadOnly}
                  fullWidth
                />
                <TextField
                  label={t("hrDashboard.offers.fields.expiresAt")}
                  type="date"
                  value={offerDraft.expiresAt}
                  onChange={(event) =>
                    setOfferDraft((prev) => ({
                      ...prev,
                      expiresAt: event.target.value,
                    }))
                  }
                  InputLabelProps={{ shrink: true }}
                  disabled={offerReadOnly}
                  fullWidth
                />
              </Stack>

              <TextField
                label={t("hrDashboard.offers.fields.termsSummary")}
                value={offerDraft.termsSummary}
                onChange={(event) =>
                  setOfferDraft((prev) => ({
                    ...prev,
                    termsSummary: event.target.value,
                  }))
                }
                disabled={offerReadOnly}
                multiline
                minRows={3}
                fullWidth
              />
              <TextField
                label={t("hrDashboard.offers.fields.note")}
                value={offerDraft.note}
                onChange={(event) =>
                  setOfferDraft((prev) => ({
                    ...prev,
                    note: event.target.value,
                  }))
                }
                disabled={offerReadOnly}
                multiline
                minRows={2}
                fullWidth
              />

              <TextField
                label={t("hrDashboard.offers.fields.decisionNote")}
                value={offerDraft.decisionNote}
                onChange={(event) =>
                  setOfferDraft((prev) => ({
                    ...prev,
                    decisionNote: event.target.value,
                  }))
                }
                disabled={offer.status !== "sent"}
                multiline
                minRows={2}
                fullWidth
              />

              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <Button
                  variant="contained"
                  onClick={handleSaveOfferDraft}
                  disabled={offerReadOnly || upsertOfferMutation.isPending}
                >
                  {upsertOfferMutation.isPending
                    ? t("hrDashboard.offers.savePending")
                    : t("hrDashboard.offers.saveAction")}
                </Button>
                <Button
                  variant="outlined"
                  onClick={handleSendOffer}
                  disabled={offer.status !== "draft" || sendOfferMutation.isPending}
                >
                  {sendOfferMutation.isPending
                    ? t("hrDashboard.offers.sendPending")
                    : t("hrDashboard.offers.sendAction")}
                </Button>
                <Button
                  variant="outlined"
                  color="success"
                  onClick={handleAcceptOffer}
                  disabled={offer.status !== "sent" || acceptOfferMutation.isPending}
                >
                  {acceptOfferMutation.isPending
                    ? t("hrDashboard.offers.acceptPending")
                    : t("hrDashboard.offers.acceptAction")}
                </Button>
                <Button
                  variant="outlined"
                  color="error"
                  onClick={handleDeclineOffer}
                  disabled={offer.status !== "sent" || declineOfferMutation.isPending}
                >
                  {declineOfferMutation.isPending
                    ? t("hrDashboard.offers.declinePending")
                    : t("hrDashboard.offers.declineAction")}
                </Button>
              </Stack>
            </Stack>
          ) : null}
        </Stack>
      </Paper>
    </Stack>
  );
}
