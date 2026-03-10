import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemText,
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
  acceptOffer,
  ApiError,
  cancelInterview,
  createInterview,
  createMatchScore,
  createPipelineTransition,
  createVacancy,
  declineOffer,
  getOffer,
  getInterviewFeedbackSummary,
  getMe,
  listInterviews,
  getMatchScore,
  listCandidateProfiles,
  listPipelineTransitions,
  listVacancies,
  putMyInterviewFeedback,
  resendInterviewInvite,
  rescheduleInterview,
  sendOffer,
  upsertOffer,
  updateVacancy,
  type CandidateResponse,
  type HRInterviewListResponse,
  type InterviewFeedbackItemResponse,
  type InterviewFeedbackPanelSummaryResponse,
  type InterviewFeedbackRecommendation,
  type InterviewFeedbackUpsertRequest,
  type HRInterviewResponse,
  type InterviewStatus,
  type MatchScoreResponse,
  type MeResponse,
  type OfferResponse,
  type OfferStatus,
  type OfferUpsertRequest,
  type PipelineTransitionCreateRequest,
  type VacancyCreateRequest,
  type VacancyResponse,
  type VacancyUpdateRequest,
} from "../api";
import { readAuthSession } from "../app/auth/session";
import { useSentryRouteTags } from "../app/observability/sentry";

const PIPELINE_STAGE_OPTIONS: PipelineTransitionCreateRequest["to_stage"][] = [
  "applied",
  "screening",
  "shortlist",
  "interview",
  "offer",
  "hired",
  "rejected",
];
const MATCH_SCORE_POLL_INTERVAL_MS = 1000;

type FeedbackState = {
  type: "success" | "error";
  message: string;
};

type VacancyDraft = VacancyCreateRequest;
type MatchScoreStatus = MatchScoreResponse["status"];
type InterviewDraft = {
  scheduledStartLocal: string;
  scheduledEndLocal: string;
  timezone: string;
  locationKind: "google_meet" | "onsite" | "phone";
  locationDetails: string;
  interviewerStaffIdsInput: string;
  cancelReasonCode: string;
};
type InterviewerFeedbackDraft = {
  requirementsMatchScore: number;
  communicationScore: number;
  problemSolvingScore: number;
  collaborationScore: number;
  recommendation: InterviewFeedbackRecommendation;
  strengthsNote: string;
  concernsNote: string;
  evidenceNote: string;
};
type OfferDraft = {
  termsSummary: string;
  proposedStartDate: string;
  expiresAt: string;
  note: string;
  decisionNote: string;
};

const DEFAULT_VACANCY_DRAFT: VacancyDraft = {
  title: "",
  description: "",
  department: "",
  status: "open",
};
const INTERVIEW_POLL_INTERVAL_MS = 1000;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const FEEDBACK_SCORE_OPTIONS = [1, 2, 3, 4, 5] as const;
const FEEDBACK_RECOMMENDATION_OPTIONS: InterviewFeedbackRecommendation[] = [
  "strong_yes",
  "yes",
  "mixed",
  "no",
];
const OFFER_MUTABLE_STATUS: OfferStatus = "draft";

/**
 * Staff recruitment workspace for vacancy CRUD and pipeline control.
 */
export function HrDashboardPage() {
  const { t } = useTranslation();
  useSentryRouteTags("/");
  const queryClient = useQueryClient();
  const session = readAuthSession();
  const accessToken = session.accessToken;
  const [selectedVacancyId, setSelectedVacancyId] = useState("");
  const [selectedCandidateId, setSelectedCandidateId] = useState("");
  const [createDraft, setCreateDraft] = useState<VacancyDraft>(DEFAULT_VACANCY_DRAFT);
  const [editDraft, setEditDraft] = useState<VacancyDraft>(DEFAULT_VACANCY_DRAFT);
  const [transitionStage, setTransitionStage] =
    useState<PipelineTransitionCreateRequest["to_stage"]>("applied");
  const [transitionReason, setTransitionReason] = useState("");
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const [scoreFeedback, setScoreFeedback] = useState<FeedbackState | null>(null);
  const [interviewFeedback, setInterviewFeedback] = useState<FeedbackState | null>(null);
  const [feedbackPanelState, setFeedbackPanelState] = useState<FeedbackState | null>(null);
  const [offerPanelState, setOfferPanelState] = useState<FeedbackState | null>(null);
  const [interviewDraft, setInterviewDraft] = useState<InterviewDraft>(createEmptyInterviewDraft);
  const [feedbackDraft, setFeedbackDraft] =
    useState<InterviewerFeedbackDraft>(createEmptyInterviewerFeedbackDraft);
  const [offerDraft, setOfferDraft] = useState<OfferDraft>(createEmptyOfferDraft);
  const matchScoreQueryKey = [
    "hr-match-score",
    accessToken,
    selectedVacancyId,
    selectedCandidateId,
  ];
  const interviewsQueryKey = [
    "hr-interviews",
    accessToken,
    selectedVacancyId,
    selectedCandidateId,
  ];
  const meQueryKey = ["auth-me", accessToken];

  const vacanciesQuery = useQuery({
    queryKey: ["hr-vacancies", accessToken],
    queryFn: () => listVacancies(accessToken!),
    enabled: Boolean(accessToken),
  });

  const candidatesQuery = useQuery({
    queryKey: ["hr-candidates", accessToken],
    queryFn: () => listCandidateProfiles(accessToken!),
    enabled: Boolean(accessToken),
  });

  const transitionsQuery = useQuery({
    queryKey: ["hr-pipeline-history", accessToken, selectedVacancyId, selectedCandidateId],
    queryFn: () => listPipelineTransitions(accessToken!, selectedVacancyId, selectedCandidateId),
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

  const interviewsQuery = useQuery({
    queryKey: interviewsQueryKey,
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
  const feedbackSummaryQueryKey = [
    "hr-interview-feedback",
    accessToken,
    selectedVacancyId,
    latestInterview?.interview_id ?? "",
  ];
  const offerQueryKey = ["hr-offer", accessToken, selectedVacancyId, selectedCandidateId];

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

  const offerQuery = useQuery({
    queryKey: offerQueryKey,
    queryFn: () => getOffer(accessToken!, selectedVacancyId, selectedCandidateId),
    enabled: Boolean(accessToken && selectedVacancyId && selectedCandidateId),
    retry: false,
  });

  const createVacancyMutation = useMutation({
    mutationFn: (payload: VacancyCreateRequest) => createVacancy(accessToken!, payload),
    onSuccess: (vacancy) => {
      setFeedback({ type: "success", message: t("hrDashboard.createSuccess") });
      setCreateDraft(DEFAULT_VACANCY_DRAFT);
      setSelectedVacancyId(vacancy.vacancy_id);
      setEditDraft(toVacancyDraft(vacancy));
      void queryClient.invalidateQueries({ queryKey: ["hr-vacancies"] });
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveRecruitmentApiError(error, t) });
    },
  });

  const updateVacancyMutation = useMutation({
    mutationFn: (payload: VacancyUpdateRequest) =>
      updateVacancy(accessToken!, selectedVacancyId, payload),
    onSuccess: (vacancy) => {
      setFeedback({ type: "success", message: t("hrDashboard.updateSuccess") });
      setEditDraft(toVacancyDraft(vacancy));
      void queryClient.invalidateQueries({ queryKey: ["hr-vacancies"] });
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveRecruitmentApiError(error, t) });
    },
  });

  const transitionMutation = useMutation({
    mutationFn: (payload: PipelineTransitionCreateRequest) =>
      createPipelineTransition(accessToken!, payload),
    onSuccess: () => {
      setFeedback({ type: "success", message: t("hrDashboard.transitionSuccess") });
      setTransitionReason("");
      void queryClient.invalidateQueries({ queryKey: ["hr-pipeline-history"] });
      void queryClient.invalidateQueries({ queryKey: offerQueryKey });
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

  const createInterviewMutation = useMutation({
    mutationFn: () =>
      createInterview(
        accessToken!,
        selectedVacancyId,
        buildInterviewCreatePayload(interviewDraft, selectedCandidateId, t),
      ),
    onSuccess: (payload) => {
      setInterviewFeedback({ type: "success", message: t("hrDashboard.interviews.createSuccess") });
      queryClient.setQueryData(interviewsQueryKey, { items: [payload] });
      void queryClient.invalidateQueries({ queryKey: interviewsQueryKey });
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
      queryClient.setQueryData(interviewsQueryKey, { items: [payload] });
      void queryClient.invalidateQueries({ queryKey: interviewsQueryKey });
    },
    onError: (error: unknown) => {
      setInterviewFeedback({ type: "error", message: resolveInterviewApiError(error, t) });
    },
  });

  const cancelInterviewMutation = useMutation({
    mutationFn: (interviewId: string) =>
      cancelInterview(accessToken!, selectedVacancyId, interviewId, {
        cancel_reason_code: normalizeInput(interviewDraft.cancelReasonCode)
          ?? "cancelled_by_staff",
      }),
    onSuccess: (payload) => {
      setInterviewFeedback({ type: "success", message: t("hrDashboard.interviews.cancelSuccess") });
      queryClient.setQueryData(interviewsQueryKey, { items: [payload] });
      void queryClient.invalidateQueries({ queryKey: interviewsQueryKey });
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
      queryClient.setQueryData(interviewsQueryKey, { items: [payload] });
      void queryClient.invalidateQueries({ queryKey: interviewsQueryKey });
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

  const upsertOfferMutation = useMutation({
    mutationFn: (payload: OfferUpsertRequest) =>
      upsertOffer(accessToken!, selectedVacancyId, selectedCandidateId, payload),
    onSuccess: async () => {
      setOfferPanelState({ type: "success", message: t("hrDashboard.offers.saveSuccess") });
      await queryClient.invalidateQueries({ queryKey: offerQueryKey });
    },
    onError: (error: unknown) => {
      setOfferPanelState({ type: "error", message: resolveRecruitmentApiError(error, t) });
    },
  });

  const sendOfferMutation = useMutation({
    mutationFn: () => sendOffer(accessToken!, selectedVacancyId, selectedCandidateId),
    onSuccess: async () => {
      setOfferPanelState({ type: "success", message: t("hrDashboard.offers.sendSuccess") });
      await queryClient.invalidateQueries({ queryKey: offerQueryKey });
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
      await queryClient.invalidateQueries({ queryKey: offerQueryKey });
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
      await queryClient.invalidateQueries({ queryKey: offerQueryKey });
      await queryClient.invalidateQueries({ queryKey: ["hr-pipeline-history"] });
    },
    onError: (error: unknown) => {
      setOfferPanelState({ type: "error", message: resolveRecruitmentApiError(error, t) });
    },
  });

  const vacancyItems = vacanciesQuery.data?.items ?? [];
  const candidateItems = candidatesQuery.data?.items ?? [];
  const selectedVacancy =
    vacancyItems.find((item) => item.vacancy_id === selectedVacancyId) ?? null;
  const selectedCandidate =
    candidateItems.find((item) => item.candidate_id === selectedCandidateId) ?? null;
  const matchScore = matchScoreQuery.data ?? null;
  const matchedRequirements = matchScore?.matched_requirements ?? [];
  const missingRequirements = matchScore?.missing_requirements ?? [];
  const matchScoreEvidence = matchScore?.evidence ?? [];
  const feedbackSummary = feedbackSummaryQuery.data ?? null;
  const offer = offerQuery.data ?? null;
  const currentUser = meQuery.data ?? null;
  const currentPipelineStage = transitionsQuery.data
    ? (transitionsQuery.data.items[transitionsQuery.data.items.length - 1]?.to_stage ?? null)
    : null;
  const currentUserCanWriteFeedback = isCurrentUserAssignedInterviewer(
    latestInterview,
    currentUser,
  );
  const currentUserFeedbackItem = findFeedbackItemForInterviewer(
    feedbackSummary,
    currentUser?.subject_id ?? null,
  );
  const hasSelectionContext = Boolean(selectedVacancyId && selectedCandidateId);
  const feedbackWindowOpen = hasInterviewFeedbackWindowOpened(latestInterview);
  const feedbackEditorBlockedReason = resolveFeedbackEditorBlockedReason({
    latestInterview,
    currentPipelineStage,
    currentUserCanWriteFeedback,
    feedbackWindowOpen,
    t,
  });
  const offerStatus = offer?.status ?? "draft";
  const offerReadOnly =
    currentPipelineStage !== "offer" || offerStatus !== OFFER_MUTABLE_STATUS;
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

  useEffect(() => {
    setOfferDraft(buildOfferDraftFromResponse(offer));
  }, [offer]);

  const handleSelectVacancy = (vacancy: VacancyResponse) => {
    setSelectedVacancyId(vacancy.vacancy_id);
    setEditDraft(toVacancyDraft(vacancy));
    setFeedback(null);
    setScoreFeedback(null);
    setInterviewFeedback(null);
    setFeedbackPanelState(null);
    setOfferPanelState(null);
  };

  const handleCreateVacancy = () => {
    setFeedback(null);
    createVacancyMutation.mutate(createDraft);
  };

  const handleUpdateVacancy = () => {
    if (!selectedVacancy) {
      setFeedback({ type: "error", message: t("hrDashboard.errors.selectVacancy") });
      return;
    }

    const payload = buildVacancyPatchPayload(selectedVacancy, editDraft);
    if (Object.keys(payload).length === 0) {
      setFeedback({ type: "error", message: t("hrDashboard.errors.noVacancyChanges") });
      return;
    }
    setFeedback(null);
    updateVacancyMutation.mutate(payload);
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

  const handleSelectCandidate = (candidateId: string) => {
    setSelectedCandidateId(candidateId);
    setScoreFeedback(null);
    setInterviewFeedback(null);
    setFeedbackPanelState(null);
    setOfferPanelState(null);
  };

  const handleRunScore = () => {
    if (!selectedVacancyId || !selectedCandidateId) {
      setScoreFeedback({
        type: "error",
        message: t("hrDashboard.errors.selectShortlistContext"),
      });
      return;
    }
    setScoreFeedback(null);
    runScoreMutation.mutate();
  };

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
      setOfferPanelState({
        type: "error",
        message: resolveRecruitmentApiError(error, t),
      });
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
    acceptOfferMutation.mutate(normalizeInput(offerDraft.decisionNote));
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
    declineOfferMutation.mutate(normalizeInput(offerDraft.decisionNote));
  };

  if (!accessToken) {
    return <Alert severity="info">{t("hrDashboard.authRequired")}</Alert>;
  }

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4">{t("hrDashboard.title")}</Typography>
        <Typography variant="body2" color="text.secondary">
          {t("hrDashboard.subtitle")}
        </Typography>
      </Stack>

      {feedback ? <Alert severity={feedback.type}>{feedback.message}</Alert> : null}

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Typography variant="h6">{t("hrDashboard.createSectionTitle")}</Typography>
          <TextField
            label={t("hrDashboard.fields.title")}
            value={createDraft.title}
            onChange={(event) => setCreateDraft((prev) => ({ ...prev, title: event.target.value }))}
          />
          <TextField
            label={t("hrDashboard.fields.department")}
            value={createDraft.department}
            onChange={(event) =>
              setCreateDraft((prev) => ({ ...prev, department: event.target.value }))
            }
          />
          <TextField
            label={t("hrDashboard.fields.status")}
            value={createDraft.status}
            onChange={(event) => setCreateDraft((prev) => ({ ...prev, status: event.target.value }))}
          />
          <TextField
            label={t("hrDashboard.fields.description")}
            value={createDraft.description}
            multiline
            minRows={3}
            onChange={(event) =>
              setCreateDraft((prev) => ({ ...prev, description: event.target.value }))
            }
          />
          <Button
            variant="contained"
            onClick={handleCreateVacancy}
            disabled={createVacancyMutation.isPending}
          >
            {createVacancyMutation.isPending
              ? t("hrDashboard.createPending")
              : t("hrDashboard.createAction")}
          </Button>
        </Stack>
      </Paper>

      <Paper>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t("hrDashboard.table.title")}</TableCell>
              <TableCell>{t("hrDashboard.table.department")}</TableCell>
              <TableCell>{t("hrDashboard.table.status")}</TableCell>
              <TableCell>{t("hrDashboard.table.updatedAt")}</TableCell>
              <TableCell>{t("hrDashboard.table.actions")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {vacanciesQuery.isLoading ? (
              <TableRow>
                <TableCell colSpan={5}>{t("hrDashboard.loadingVacancies")}</TableCell>
              </TableRow>
            ) : null}
            {!vacanciesQuery.isLoading && vacancyItems.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5}>{t("hrDashboard.emptyVacancies")}</TableCell>
              </TableRow>
            ) : null}
            {vacancyItems.map((vacancy) => (
              <TableRow
                key={vacancy.vacancy_id}
                selected={vacancy.vacancy_id === selectedVacancyId}
              >
                <TableCell>{vacancy.title}</TableCell>
                <TableCell>{vacancy.department}</TableCell>
                <TableCell>{vacancy.status}</TableCell>
                <TableCell>{formatDateTime(vacancy.updated_at)}</TableCell>
                <TableCell>
                  <Button size="small" onClick={() => handleSelectVacancy(vacancy)}>
                    {t("hrDashboard.selectVacancyAction")}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Typography variant="h6">{t("hrDashboard.editSectionTitle")}</Typography>
          {selectedVacancy ? (
            <Typography variant="body2" color="text.secondary">
              {t("hrDashboard.selectedVacancySummary", {
                vacancyTitle: selectedVacancy.title,
                vacancyId: selectedVacancy.vacancy_id,
              })}
            </Typography>
          ) : (
            <Alert severity="info">{t("hrDashboard.selectVacancyPrompt")}</Alert>
          )}
          <TextField
            label={t("hrDashboard.fields.title")}
            value={editDraft.title}
            onChange={(event) => setEditDraft((prev) => ({ ...prev, title: event.target.value }))}
          />
          <TextField
            label={t("hrDashboard.fields.department")}
            value={editDraft.department}
            onChange={(event) =>
              setEditDraft((prev) => ({ ...prev, department: event.target.value }))
            }
          />
          <TextField
            label={t("hrDashboard.fields.status")}
            value={editDraft.status}
            onChange={(event) => setEditDraft((prev) => ({ ...prev, status: event.target.value }))}
          />
          <TextField
            label={t("hrDashboard.fields.description")}
            value={editDraft.description}
            multiline
            minRows={3}
            onChange={(event) =>
              setEditDraft((prev) => ({ ...prev, description: event.target.value }))
            }
          />
          <Button
            variant="outlined"
            onClick={handleUpdateVacancy}
            disabled={updateVacancyMutation.isPending}
          >
            {updateVacancyMutation.isPending
              ? t("hrDashboard.updatePending")
              : t("hrDashboard.updateAction")}
          </Button>
        </Stack>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Typography variant="h6">{t("hrDashboard.pipelineTitle")}</Typography>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField
              select
              label={t("hrDashboard.fields.candidate")}
              value={selectedCandidateId}
              onChange={(event) => handleSelectCandidate(event.target.value)}
              fullWidth
              SelectProps={{ native: true }}
            >
              <option value="">{t("hrDashboard.selectCandidateAction")}</option>
              {candidateItems.map((candidate) => (
                <option key={candidate.candidate_id} value={candidate.candidate_id}>
                  {formatCandidateLabel(candidate)}
                </option>
              ))}
            </TextField>
            <TextField
              select
              label={t("hrDashboard.fields.transitionStage")}
              value={transitionStage}
              onChange={(event) =>
                setTransitionStage(event.target.value as PipelineTransitionCreateRequest["to_stage"])
              }
              fullWidth
              SelectProps={{ native: true }}
            >
              {PIPELINE_STAGE_OPTIONS.map((stage) => (
                <option key={stage} value={stage}>
                  {t(`hrDashboard.stages.${stage}`)}
                </option>
              ))}
            </TextField>
          </Stack>
          <TextField
            label={t("hrDashboard.fields.transitionReason")}
            value={transitionReason}
            onChange={(event) => setTransitionReason(event.target.value)}
            multiline
            minRows={2}
          />
          <Button
            variant="contained"
            onClick={handleCreateTransition}
            disabled={transitionMutation.isPending}
          >
            {transitionMutation.isPending
              ? t("hrDashboard.transitionPending")
              : t("hrDashboard.transitionAction")}
          </Button>

          {selectedCandidate ? (
            <Typography variant="body2" color="text.secondary">
              {t("hrDashboard.selectedCandidateSummary", {
                candidateName: formatCandidateLabel(selectedCandidate),
                candidateId: selectedCandidate.candidate_id,
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

                  {matchScore.status === "failed" ? (
                    <Alert severity="warning">{t("hrDashboard.shortlist.failedHint")}</Alert>
                  ) : null}

                  <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                    <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                      <Stack spacing={1}>
                        <Typography variant="overline">
                          {t("hrDashboard.shortlist.scoreLabel")}
                        </Typography>
                        <Typography variant="h4">
                          {formatScore(matchScore.score, t)}
                        </Typography>
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
                      {renderStringList(
                        matchedRequirements,
                        t("hrDashboard.shortlist.noItems"),
                      )}
                    </Paper>
                    <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                      <Typography variant="subtitle1">
                        {t("hrDashboard.shortlist.missingTitle")}
                      </Typography>
                      {renderStringList(
                        missingRequirements,
                        t("hrDashboard.shortlist.noItems"),
                      )}
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
                disabled={
                  !selectedVacancyId || !selectedCandidateId || createInterviewMutation.isPending
                }
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

          {!hasSelectionContext ? (
            <Alert severity="info">{t("hrDashboard.interviews.inactive")}</Alert>
          ) : null}

          {hasSelectionContext ? (
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

                  {transitionStage === "offer" && feedbackSummary ? (
                    <Alert
                      severity={feedbackSummary.gate_status === "passed" ? "success" : "warning"}
                    >
                      {buildOfferGateAlertMessage(feedbackSummary, t)}
                    </Alert>
                  ) : null}

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

                  {feedbackSummary ? (
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

                        <Alert
                          severity={feedbackSummary.gate_status === "passed" ? "success" : "warning"}
                        >
                          {buildFeedbackGateMessage(feedbackSummary, t)}
                        </Alert>

                        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                          <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                            <Typography variant="overline">
                              {t("hrDashboard.interviews.feedback.requiredCount")}
                            </Typography>
                            <Typography variant="h5">
                              {feedbackSummary.required_interviewer_count}
                            </Typography>
                          </Paper>
                          <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                            <Typography variant="overline">
                              {t("hrDashboard.interviews.feedback.submittedCount")}
                            </Typography>
                            <Typography variant="h5">{feedbackSummary.submitted_count}</Typography>
                          </Paper>
                          <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                            <Typography variant="overline">
                              {t("hrDashboard.interviews.feedback.missingCount")}
                            </Typography>
                            <Typography variant="h5">
                              {feedbackSummary.missing_interviewer_ids.length}
                            </Typography>
                          </Paper>
                        </Stack>

                        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                          <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                            <Typography variant="subtitle2">
                              {t("hrDashboard.interviews.feedback.missingTitle")}
                            </Typography>
                            {renderStringList(
                              feedbackSummary.missing_interviewer_ids,
                              t("hrDashboard.interviews.feedback.noMissing"),
                            )}
                          </Paper>
                          <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                            <Typography variant="subtitle2">
                              {t("hrDashboard.interviews.feedback.distributionTitle")}
                            </Typography>
                            <List dense disablePadding>
                              {FEEDBACK_RECOMMENDATION_OPTIONS.map((recommendation) => (
                                <ListItem key={recommendation} disableGutters>
                                  <ListItemText
                                    primary={t(
                                      `hrDashboard.interviews.feedback.recommendation.${recommendation}`,
                                    )}
                                    secondary={String(
                                      feedbackSummary.recommendation_distribution[recommendation],
                                    )}
                                  />
                                </ListItem>
                              ))}
                            </List>
                          </Paper>
                          <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
                            <Typography variant="subtitle2">
                              {t("hrDashboard.interviews.feedback.averagesTitle")}
                            </Typography>
                            <List dense disablePadding>
                              <ListItem disableGutters>
                                <ListItemText
                                  primary={t(
                                    "hrDashboard.interviews.feedback.fields.requirementsMatchScore",
                                  )}
                                  secondary={formatAverageScore(
                                    feedbackSummary.average_scores.requirements_match_score,
                                    t,
                                  )}
                                />
                              </ListItem>
                              <ListItem disableGutters>
                                <ListItemText
                                  primary={t(
                                    "hrDashboard.interviews.feedback.fields.communicationScore",
                                  )}
                                  secondary={formatAverageScore(
                                    feedbackSummary.average_scores.communication_score,
                                    t,
                                  )}
                                />
                              </ListItem>
                              <ListItem disableGutters>
                                <ListItemText
                                  primary={t(
                                    "hrDashboard.interviews.feedback.fields.problemSolvingScore",
                                  )}
                                  secondary={formatAverageScore(
                                    feedbackSummary.average_scores.problem_solving_score,
                                    t,
                                  )}
                                />
                              </ListItem>
                              <ListItem disableGutters>
                                <ListItemText
                                  primary={t(
                                    "hrDashboard.interviews.feedback.fields.collaborationScore",
                                  )}
                                  secondary={formatAverageScore(
                                    feedbackSummary.average_scores.collaboration_score,
                                    t,
                                  )}
                                />
                              </ListItem>
                            </List>
                          </Paper>
                        </Stack>

                        <Paper variant="outlined" sx={{ p: 2 }}>
                          <Typography variant="subtitle2">
                            {t("hrDashboard.interviews.feedback.submittedTitle")}
                          </Typography>
                          {feedbackSummary.items.length === 0 ? (
                            <Typography variant="body2" color="text.secondary">
                              {t("hrDashboard.interviews.feedback.empty")}
                            </Typography>
                          ) : (
                            <Stack spacing={1.5} sx={{ mt: 1 }}>
                              {feedbackSummary.items.map((item) => (
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
                                {resolveRecruitmentApiError(meQuery.error, t)}
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
                                  label={t(
                                    "hrDashboard.interviews.feedback.fields.recommendation",
                                  )}
                                  value={feedbackDraft.recommendation}
                                  onChange={(event) =>
                                    setFeedbackDraft((prev) => ({
                                      ...prev,
                                      recommendation:
                                        event.target.value as InterviewFeedbackRecommendation,
                                    }))
                                  }
                                  disabled={Boolean(feedbackEditorBlockedReason)}
                                  SelectProps={{ native: true }}
                                  fullWidth
                                >
                                  {FEEDBACK_RECOMMENDATION_OPTIONS.map((recommendation) => (
                                    <option key={recommendation} value={recommendation}>
                                      {t(
                                        `hrDashboard.interviews.feedback.recommendation.${recommendation}`,
                                      )}
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
                    </Paper>
                  ) : null}

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

              <Paper variant="outlined" sx={{ p: 2 }}>
                <Stack spacing={2}>
                  <Stack spacing={0.5}>
                    <Typography variant="subtitle1">
                      {t("hrDashboard.offers.title")}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {t("hrDashboard.offers.subtitle")}
                    </Typography>
                  </Stack>

                  {offerPanelState ? (
                    <Alert severity={offerPanelState.type}>{offerPanelState.message}</Alert>
                  ) : null}

                  {offerPrerequisiteMessage ? (
                    <Alert severity={offerPrerequisiteSeverity}>
                      {offerPrerequisiteMessage}
                    </Alert>
                  ) : null}

                  {offerQuery.isLoading && !offer ? (
                    <Typography variant="body2">
                      {t("hrDashboard.offers.loading")}
                    </Typography>
                  ) : null}

                  {offerQuery.isError && !isOfferStageNotActiveError(offerQuery.error) ? (
                    <Alert severity="error">
                      {resolveRecruitmentApiError(offerQuery.error, t)}
                    </Alert>
                  ) : null}

                  {offer ? (
                    <Stack spacing={2}>
                      <Stack
                        direction={{ xs: "column", md: "row" }}
                        spacing={1}
                        alignItems={{ xs: "flex-start", md: "center" }}
                      >
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
                            {t("hrDashboard.offers.sentAt", {
                              value: formatDateTime(offer.sent_at),
                            })}
                          </Typography>
                        ) : null}
                        {offer.decision_at ? (
                          <Typography variant="body2" color="text.secondary">
                            {t("hrDashboard.offers.decisionAt", {
                              value: formatDateTime(offer.decision_at),
                            })}
                          </Typography>
                        ) : null}
                      </Stack>

                      <Alert severity={resolveOfferHintSeverity(offer.status)}>
                        {offerStatusHint}
                      </Alert>

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
          ) : null}
        </Stack>
      </Paper>
    </Stack>
  );
}

function toVacancyDraft(vacancy: VacancyResponse): VacancyDraft {
  return {
    title: vacancy.title,
    description: vacancy.description,
    department: vacancy.department,
    status: vacancy.status,
  };
}

function buildVacancyPatchPayload(
  current: VacancyResponse,
  draft: VacancyDraft,
): VacancyUpdateRequest {
  const payload: VacancyUpdateRequest = {};
  if (draft.title !== current.title) {
    payload.title = draft.title;
  }
  if (draft.description !== current.description) {
    payload.description = draft.description;
  }
  if (draft.department !== current.department) {
    payload.department = draft.department;
  }
  if (draft.status !== current.status) {
    payload.status = draft.status;
  }
  return payload;
}

function formatCandidateLabel(candidate: CandidateResponse): string {
  return `${candidate.first_name} ${candidate.last_name} (${candidate.email})`;
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString();
}

function formatScore(
  value: number | null | undefined,
  t: (key: string) => string,
): string {
  if (value === null || value === undefined) {
    return t("hrDashboard.shortlist.notAvailable");
  }
  return value.toFixed(0);
}

function formatConfidence(
  value: number | null | undefined,
  t: (key: string) => string,
): string {
  if (value === null || value === undefined) {
    return t("hrDashboard.shortlist.notAvailable");
  }
  return `${Math.round(value * 100)}%`;
}

function formatAverageScore(
  value: number | null | undefined,
  t: (key: string) => string,
): string {
  if (value === null || value === undefined) {
    return t("hrDashboard.shortlist.notAvailable");
  }
  return value.toFixed(2);
}

function buildOfferGateAlertMessage(
  summary: InterviewFeedbackPanelSummaryResponse,
  t: (key: string, options?: Record<string, unknown>) => string,
): string {
  if (summary.gate_status === "passed") {
    return t("hrDashboard.interviews.feedback.offerReady");
  }
  return t("hrDashboard.interviews.feedback.offerBlocked", {
    reasons: resolveFeedbackGateReasonLabels(summary.gate_reason_codes, t).join(", "),
  });
}

function buildFeedbackGateMessage(
  summary: InterviewFeedbackPanelSummaryResponse,
  t: (key: string, options?: Record<string, unknown>) => string,
): string {
  if (summary.gate_status === "passed") {
    return t("hrDashboard.interviews.feedback.gatePassed");
  }
  return t("hrDashboard.interviews.feedback.gateBlocked", {
    reasons: resolveFeedbackGateReasonLabels(summary.gate_reason_codes, t).join(", "),
  });
}

function resolveFeedbackGateReasonLabels(
  reasonCodes: string[],
  t: (key: string) => string,
): string[] {
  return reasonCodes.map((reasonCode) => {
    const translated = t(`hrDashboard.interviews.feedback.gateReasons.${reasonCode}`);
    if (translated !== `hrDashboard.interviews.feedback.gateReasons.${reasonCode}`) {
      return translated;
    }
    return reasonCode;
  });
}

function resolveMatchScoreChipColor(
  status: MatchScoreStatus,
): "default" | "error" | "info" | "success" | "warning" {
  switch (status) {
    case "queued":
      return "info";
    case "running":
      return "warning";
    case "succeeded":
      return "success";
    case "failed":
      return "error";
    default:
      return "default";
  }
}

function renderStringList(items: string[], emptyState: string) {
  if (items.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        {emptyState}
      </Typography>
    );
  }

  return (
    <List dense disablePadding>
      {items.map((item) => (
        <ListItem key={item} disableGutters>
          <ListItemText primary={item} />
        </ListItem>
      ))}
    </List>
  );
}

function normalizeInput(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function createEmptyInterviewDraft(): InterviewDraft {
  return {
    scheduledStartLocal: "",
    scheduledEndLocal: "",
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
    locationKind: "google_meet",
    locationDetails: "",
    interviewerStaffIdsInput: "",
    cancelReasonCode: "cancelled_by_staff",
  };
}

function createEmptyOfferDraft(): OfferDraft {
  return {
    termsSummary: "",
    proposedStartDate: "",
    expiresAt: "",
    note: "",
    decisionNote: "",
  };
}

function createEmptyInterviewerFeedbackDraft(): InterviewerFeedbackDraft {
  return {
    requirementsMatchScore: 3,
    communicationScore: 3,
    problemSolvingScore: 3,
    collaborationScore: 3,
    recommendation: "mixed",
    strengthsNote: "",
    concernsNote: "",
    evidenceNote: "",
  };
}

function buildInterviewDraftFromResponse(interview: HRInterviewResponse): InterviewDraft {
  return {
    scheduledStartLocal: toDateTimeLocalValue(interview.scheduled_start_at),
    scheduledEndLocal: toDateTimeLocalValue(interview.scheduled_end_at),
    timezone: interview.timezone,
    locationKind: interview.location_kind,
    locationDetails: interview.location_details ?? "",
    interviewerStaffIdsInput: interview.interviewer_staff_ids.join(", "),
    cancelReasonCode: interview.cancel_reason_code ?? "cancelled_by_staff",
  };
}

function buildFeedbackDraftFromItem(
  item: InterviewFeedbackItemResponse | null,
): InterviewerFeedbackDraft {
  if (!item) {
    return createEmptyInterviewerFeedbackDraft();
  }
  return {
    requirementsMatchScore: item.requirements_match_score,
    communicationScore: item.communication_score,
    problemSolvingScore: item.problem_solving_score,
    collaborationScore: item.collaboration_score,
    recommendation: item.recommendation,
    strengthsNote: item.strengths_note,
    concernsNote: item.concerns_note,
    evidenceNote: item.evidence_note,
  };
}

function buildOfferDraftFromResponse(item: OfferResponse | null): OfferDraft {
  if (!item) {
    return createEmptyOfferDraft();
  }
  return {
    termsSummary: item.terms_summary ?? "",
    proposedStartDate: item.proposed_start_date ?? "",
    expiresAt: item.expires_at ?? "",
    note: item.note ?? "",
    decisionNote: item.decision_note ?? "",
  };
}

function buildInterviewFeedbackPayload(
  draft: InterviewerFeedbackDraft,
  t: (key: string) => string,
): InterviewFeedbackUpsertRequest {
  const strengthsNote = draft.strengthsNote.trim();
  const concernsNote = draft.concernsNote.trim();
  const evidenceNote = draft.evidenceNote.trim();
  if (!strengthsNote || !concernsNote || !evidenceNote) {
    throw new Error(t("hrDashboard.interviews.feedback.errors.notesRequired"));
  }
  return {
    requirements_match_score: draft.requirementsMatchScore,
    communication_score: draft.communicationScore,
    problem_solving_score: draft.problemSolvingScore,
    collaboration_score: draft.collaborationScore,
    recommendation: draft.recommendation,
    strengths_note: strengthsNote,
    concerns_note: concernsNote,
    evidence_note: evidenceNote,
  };
}

function buildOfferUpsertPayload(
  draft: OfferDraft,
  t: (key: string) => string,
): OfferUpsertRequest {
  const termsSummary = normalizeInput(draft.termsSummary);
  if (!termsSummary) {
    throw new Error(t("hrDashboard.offers.errors.termsRequired"));
  }
  return {
    terms_summary: termsSummary,
    proposed_start_date: normalizeInput(draft.proposedStartDate),
    expires_at: normalizeInput(draft.expiresAt),
    note: normalizeInput(draft.note),
  };
}

function buildInterviewCreatePayload(
  draft: InterviewDraft,
  candidateId: string,
  t: (key: string) => string,
) {
  const basePayload = buildInterviewSchedulePayload(draft, t);
  return {
    ...basePayload,
    candidate_id: candidateId,
  };
}

function buildInterviewReschedulePayload(
  draft: InterviewDraft,
  t: (key: string) => string,
) {
  return buildInterviewSchedulePayload(draft, t);
}

function buildInterviewSchedulePayload(
  draft: InterviewDraft,
  t: (key: string) => string,
) {
  const interviewerStaffIds = parseInterviewerStaffIds(draft.interviewerStaffIdsInput);
  if (!draft.scheduledStartLocal || !draft.scheduledEndLocal) {
    throw new Error(t("hrDashboard.interviews.errors.missingScheduleWindow"));
  }
  if (interviewerStaffIds.length === 0) {
    throw new Error(t("hrDashboard.interviews.errors.invalidInterviewerIds"));
  }
  return {
    scheduled_start_local: draft.scheduledStartLocal,
    scheduled_end_local: draft.scheduledEndLocal,
    timezone: draft.timezone.trim(),
    location_kind: draft.locationKind,
    location_details: normalizeInput(draft.locationDetails),
    interviewer_staff_ids: interviewerStaffIds,
  };
}

function parseInterviewerStaffIds(value: string): string[] {
  const items = value
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
  if (items.some((item) => !UUID_PATTERN.test(item))) {
    return [];
  }
  return Array.from(new Set(items));
}

function toDateTimeLocalValue(value: string): string {
  const item = new Date(value);
  if (Number.isNaN(item.getTime())) {
    return "";
  }
  const year = item.getFullYear();
  const month = String(item.getMonth() + 1).padStart(2, "0");
  const day = String(item.getDate()).padStart(2, "0");
  const hours = String(item.getHours()).padStart(2, "0");
  const minutes = String(item.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function formatInterviewDateTime(value: string, timezone: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: timezone,
    }).format(new Date(value));
  } catch {
    return new Date(value).toLocaleString();
  }
}

function selectInterviewState(items: HRInterviewResponse[]): {
  active: HRInterviewResponse | null;
  latest: HRInterviewResponse | null;
} {
  const active =
    items.find((item) => item.status !== "cancelled") ?? null;
  return {
    active,
    latest: active ?? items[0] ?? null,
  };
}

function findFeedbackItemForInterviewer(
  summary: InterviewFeedbackPanelSummaryResponse | null,
  interviewerId: string | null,
): InterviewFeedbackItemResponse | null {
  if (!summary || !interviewerId) {
    return null;
  }
  return (
    summary.items.find((item) => item.interviewer_staff_id === interviewerId)
    ?? null
  );
}

function isCurrentUserAssignedInterviewer(
  interview: HRInterviewResponse | null,
  currentUser: MeResponse | null,
): boolean {
  if (!interview || !currentUser) {
    return false;
  }
  return interview.interviewer_staff_ids.includes(currentUser.subject_id);
}

function hasInterviewFeedbackWindowOpened(interview: HRInterviewResponse | null): boolean {
  if (!interview) {
    return false;
  }
  return new Date(interview.scheduled_end_at).getTime() <= Date.now();
}

function resolveFeedbackEditorBlockedReason({
  latestInterview,
  currentPipelineStage,
  currentUserCanWriteFeedback,
  feedbackWindowOpen,
  t,
}: {
  latestInterview: HRInterviewResponse | null;
  currentPipelineStage: PipelineTransitionCreateRequest["to_stage"] | null;
  currentUserCanWriteFeedback: boolean;
  feedbackWindowOpen: boolean;
  t: (key: string) => string;
}): string | null {
  if (!latestInterview || !currentUserCanWriteFeedback) {
    return null;
  }
  if (latestInterview.status === "cancelled") {
    return t("hrDashboard.interviews.feedback.locked");
  }
  if (!feedbackWindowOpen) {
    return t("hrDashboard.interviews.feedback.windowNotOpen");
  }
  if (currentPipelineStage && currentPipelineStage !== "interview") {
    return t("hrDashboard.interviews.feedback.locked");
  }
  return null;
}

function buildOfferPrerequisiteMessage({
  currentPipelineStage,
  feedbackSummary,
  offerQueryError,
  t,
}: {
  currentPipelineStage: PipelineTransitionCreateRequest["to_stage"] | null;
  feedbackSummary: InterviewFeedbackPanelSummaryResponse | null;
  offerQueryError: unknown;
  t: (key: string, options?: Record<string, unknown>) => string;
}): string | null {
  if (currentPipelineStage === "interview" && feedbackSummary) {
    if (feedbackSummary.gate_status === "passed") {
      return t("hrDashboard.offers.waitingForTransition");
    }
    return t("hrDashboard.offers.blockedByFairnessGate", {
      reasons: resolveFeedbackGateReasonLabels(feedbackSummary.gate_reason_codes, t).join(", "),
    });
  }
  if (currentPipelineStage !== "offer" && currentPipelineStage !== "hired" && currentPipelineStage !== "rejected") {
    return t("hrDashboard.offers.inactive");
  }
  if (isOfferStageNotActiveError(offerQueryError)) {
    return t("hrDashboard.offers.stageNotReady");
  }
  return null;
}

function buildOfferStatusHint(
  status: OfferStatus,
  t: (key: string) => string,
): string {
  switch (status) {
    case "draft":
      return t("hrDashboard.offers.hints.draft");
    case "sent":
      return t("hrDashboard.offers.hints.sent");
    case "accepted":
      return t("hrDashboard.offers.hints.accepted");
    case "declined":
      return t("hrDashboard.offers.hints.declined");
    default:
      return t("hrDashboard.offers.hints.draft");
  }
}

function isOfferStageNotActiveError(error: unknown): boolean {
  return error instanceof ApiError && error.detail.toLowerCase().includes("offer_stage_not_active");
}

function resolveRecruitmentApiError(
  error: unknown,
  t: (key: string) => string,
): string {
  if (error instanceof Error && !(error instanceof ApiError)) {
    return error.message;
  }
  if (error instanceof ApiError) {
    const detail = error.detail.toLowerCase();
    if (detail.includes("vacancy not found")) {
      return t("hrDashboard.errors.vacancyNotFound");
    }
    if (detail.includes("candidate not found")) {
      return t("hrDashboard.errors.candidateNotFound");
    }
    if (detail.includes("cv analysis is not ready")) {
      return t("hrDashboard.errors.cvAnalysisNotReady");
    }
    if (detail.includes("match score not found")) {
      return t("hrDashboard.errors.matchScoreNotFound");
    }
    if (detail.includes("interview_feedback_window_not_open")) {
      return t("hrDashboard.errors.interviewFeedbackWindowNotOpen");
    }
    if (detail.includes("interview_feedback_missing")) {
      return t("hrDashboard.errors.interviewFeedbackMissing");
    }
    if (detail.includes("interview_feedback_incomplete")) {
      return t("hrDashboard.errors.interviewFeedbackIncomplete");
    }
    if (detail.includes("interview_feedback_stale")) {
      return t("hrDashboard.errors.interviewFeedbackStale");
    }
    if (detail.includes("offer_stage_not_active")) {
      return t("hrDashboard.errors.offerStageNotActive");
    }
    if (detail.includes("offer_not_found")) {
      return t("hrDashboard.errors.offerNotFound");
    }
    if (detail.includes("offer_not_editable")) {
      return t("hrDashboard.errors.offerNotEditable");
    }
    if (detail.includes("offer_already_sent")) {
      return t("hrDashboard.errors.offerAlreadySent");
    }
    if (detail.includes("offer_already_accepted")) {
      return t("hrDashboard.errors.offerAlreadyAccepted");
    }
    if (detail.includes("offer_already_declined")) {
      return t("hrDashboard.errors.offerAlreadyDeclined");
    }
    if (detail.includes("offer_not_sent")) {
      return t("hrDashboard.errors.offerNotSent");
    }
    if (detail.includes("offer_terms_missing")) {
      return t("hrDashboard.errors.offerTermsMissing");
    }
    if (detail.includes("offer_not_accepted")) {
      return t("hrDashboard.errors.offerNotAccepted");
    }
    if (detail.includes("offer_not_declined")) {
      return t("hrDashboard.errors.offerNotDeclined");
    }
    if (detail.includes("transition from")) {
      return t("hrDashboard.errors.invalidTransition");
    }
    const statusMessage = t(`hrDashboard.errors.http_${error.status}`);
    if (statusMessage !== `hrDashboard.errors.http_${error.status}`) {
      return statusMessage;
    }
  }
  return t("hrDashboard.errors.generic");
}

function resolveInterviewApiError(
  error: unknown,
  t: (key: string) => string,
): string {
  if (error instanceof Error && !(error instanceof ApiError)) {
    return error.message;
  }
  if (error instanceof ApiError) {
    const detail = error.detail.toLowerCase();
    if (detail.includes("calendar_not_configured")) {
      return t("hrDashboard.interviews.errors.calendarNotConfigured");
    }
    if (detail.includes("interviewer_calendar_not_configured")) {
      return t("hrDashboard.interviews.errors.interviewerCalendarNotConfigured");
    }
    if (detail.includes("active_interview_already_exists")) {
      return t("hrDashboard.interviews.errors.activeInterviewAlreadyExists");
    }
    if (detail.includes("invalid_pipeline_stage")) {
      return t("hrDashboard.interviews.errors.invalidPipelineStage");
    }
    if (detail.includes("duplicate_interviewer_list")) {
      return t("hrDashboard.interviews.errors.duplicateInterviewers");
    }
    if (detail.includes("interview_terminal")) {
      return t("hrDashboard.interviews.errors.interviewTerminal");
    }
    if (detail.includes("invite_not_available")) {
      return t("hrDashboard.interviews.errors.inviteNotAvailable");
    }
    if (detail.includes("interview_feedback_forbidden")) {
      return t("hrDashboard.interviews.feedback.notAssigned");
    }
    if (detail.includes("interview_feedback_locked")) {
      return t("hrDashboard.interviews.feedback.locked");
    }
    if (detail.includes("interview_feedback_window_not_open")) {
      return t("hrDashboard.interviews.feedback.windowNotOpen");
    }
    const statusMessage = t(`hrDashboard.interviews.errors.http_${error.status}`);
    if (statusMessage !== `hrDashboard.interviews.errors.http_${error.status}`) {
      return statusMessage;
    }
  }
  return t("hrDashboard.interviews.errors.generic");
}

function resolveInterviewStatusChipColor(
  status: InterviewStatus,
): "default" | "error" | "info" | "success" | "warning" {
  switch (status) {
    case "pending_sync":
      return "info";
    case "awaiting_candidate_confirmation":
      return "warning";
    case "confirmed":
      return "success";
    case "reschedule_requested":
      return "warning";
    case "cancelled":
      return "error";
    default:
      return "default";
  }
}

function resolveInterviewSyncChipColor(
  status: HRInterviewResponse["calendar_sync_status"],
): "default" | "error" | "info" | "success" | "warning" {
  switch (status) {
    case "queued":
      return "info";
    case "running":
      return "warning";
    case "synced":
      return "success";
    case "conflict":
      return "warning";
    case "failed":
      return "error";
    default:
      return "default";
  }
}

function resolveOfferStatusChipColor(
  status: OfferStatus,
): "default" | "error" | "info" | "success" | "warning" {
  switch (status) {
    case "draft":
      return "info";
    case "sent":
      return "warning";
    case "accepted":
      return "success";
    case "declined":
      return "error";
    default:
      return "default";
  }
}

function resolveOfferHintSeverity(
  status: OfferStatus,
): "error" | "info" | "success" | "warning" {
  switch (status) {
    case "draft":
      return "warning";
    case "sent":
      return "info";
    case "accepted":
      return "success";
    case "declined":
      return "error";
    default:
      return "info";
  }
}
