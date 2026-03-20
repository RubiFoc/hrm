import { useState } from "react";
import {
  Alert,
  Button,
  Chip,
  Divider,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import {
  ApiError,
  cancelPublicInterviewRegistration,
  confirmPublicInterviewRegistration,
  getPublicInterviewRegistration,
  requestPublicInterviewReschedule,
  type PublicInterviewRegistrationResponse,
} from "../../api";
import { useSentryRouteTags } from "../../app/observability/sentry";
import { PageHero } from "../../components/PageHero";
import { formatInterviewDateTime, normalizeInput } from "./candidateUtils";
import { useParams } from "react-router-dom";

type FeedbackState = {
  type: "success" | "error";
  message: string;
};

/**
 * Public candidate interview-registration page for a single invite token.
 */
export function CandidateInterviewRegistrationPage() {
  const { t } = useTranslation();
  useSentryRouteTags("/candidate/interview");
  const { interviewToken: routeInterviewToken } = useParams<{ interviewToken: string }>();
  const interviewToken = normalizeInput(routeInterviewToken);

  if (!interviewToken) {
    return (
      <Stack spacing={3}>
        <PageHero
          eyebrow={t("candidatePortal.eyebrow")}
          title={t("candidateWorkspace")}
          description={t("candidateRoute.invalidLinkSubtitle")}
          imageSrc="/images/candidate-portal.jpg"
          imageAlt={t("candidatePortal.imageAlt")}
        />
        <Alert severity="error">{t("candidateRoute.invalidLink")}</Alert>
      </Stack>
    );
  }

  return <CandidateInterviewRegistrationWorkspace interviewToken={interviewToken} />;
}

function CandidateInterviewRegistrationWorkspace({
  interviewToken,
}: {
  interviewToken: string;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const queryKey = ["candidate-interview-registration", interviewToken];
  const registrationQuery = useQuery({
    queryKey,
    queryFn: () => getPublicInterviewRegistration(interviewToken),
    retry: false,
  });

  const confirmMutation = useMutation({
    mutationFn: () => confirmPublicInterviewRegistration(interviewToken),
    onSuccess: (payload) => {
      setFeedback({ type: "success", message: t("candidateInterview.confirmSuccess") });
      queryClient.setQueryData(queryKey, payload);
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveCandidateInterviewError(error, t) });
    },
  });

  const rescheduleMutation = useMutation({
    mutationFn: () =>
      requestPublicInterviewReschedule(interviewToken, {
        note: normalizeInput(note),
      }),
    onSuccess: (payload) => {
      setFeedback({ type: "success", message: t("candidateInterview.rescheduleSuccess") });
      setNote("");
      queryClient.setQueryData(queryKey, payload);
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveCandidateInterviewError(error, t) });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () =>
      cancelPublicInterviewRegistration(interviewToken, {
        note: normalizeInput(note),
      }),
    onSuccess: (payload) => {
      setFeedback({ type: "success", message: t("candidateInterview.declineSuccess") });
      setNote("");
      queryClient.setQueryData(queryKey, payload);
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveCandidateInterviewError(error, t) });
    },
  });

  const isMutating =
    confirmMutation.isPending || rescheduleMutation.isPending || cancelMutation.isPending;
  const registration = registrationQuery.data ?? null;

  return (
    <Stack spacing={3}>
      <PageHero
        eyebrow={t("candidatePortal.eyebrow")}
        title={t("candidateWorkspace")}
        description={t("candidateInterview.subtitle")}
        imageSrc="/images/candidate-portal.jpg"
        imageAlt={t("candidatePortal.imageAlt")}
      />

      {feedback ? <Alert severity={feedback.type}>{feedback.message}</Alert> : null}
      {registrationQuery.isLoading ? (
        <Typography variant="body2">{t("candidateInterview.loading")}</Typography>
      ) : null}
      {registrationQuery.isError ? (
        <Alert severity="error">
          {resolveCandidateInterviewError(registrationQuery.error, t)}
        </Alert>
      ) : null}

      {registration ? (
        <Paper sx={{ p: 3 }}>
          <Stack spacing={2}>
            <Stack spacing={1}>
              <Typography variant="h6">{t("candidateInterview.title")}</Typography>
              <Typography variant="body1">{registration.vacancy_title}</Typography>
              <Stack direction={{ xs: "column", md: "row" }} spacing={1} alignItems="flex-start">
                <Chip
                  size="small"
                  label={t(`candidateInterview.status.${registration.status}`)}
                  color={resolveInterviewStatusChipColor(registration.status)}
                />
                <Chip
                  size="small"
                  label={t(`candidateInterview.syncStatus.${registration.calendar_sync_status}`)}
                  color={resolveInterviewSyncChipColor(registration.calendar_sync_status)}
                />
              </Stack>
            </Stack>

            <Stack spacing={1}>
              <Typography variant="body2">
                {t("candidateInterview.fields.start")}:{" "}
                {formatInterviewDateTime(registration.scheduled_start_at, registration.timezone)}
              </Typography>
              <Typography variant="body2">
                {t("candidateInterview.fields.end")}:{" "}
                {formatInterviewDateTime(registration.scheduled_end_at, registration.timezone)}
              </Typography>
              <Typography variant="body2">
                {t("candidateInterview.fields.timezone")}: {registration.timezone}
              </Typography>
              <Typography variant="body2">
                {t("candidateInterview.fields.locationKind")}:{" "}
                {t(`candidateInterview.locationKind.${registration.location_kind}`)}
              </Typography>
              <Typography variant="body2">
                {t("candidateInterview.fields.locationDetails")}:{" "}
                {registration.location_details || t("candidateInterview.noLocationDetails")}
              </Typography>
              <Typography variant="body2">
                {t("candidateInterview.fields.responseStatus")}:{" "}
                {t(`candidateInterview.responseStatus.${registration.candidate_response_status}`)}
              </Typography>
            </Stack>

            {registration.candidate_response_note ? (
              <Alert severity="info">
                {t("candidateInterview.noteLabel")}: {registration.candidate_response_note}
              </Alert>
            ) : null}
            {registration.candidate_token_expires_at ? (
              <Typography variant="body2" color="text.secondary">
                {t("candidateInterview.tokenExpiresAt", {
                  value: formatInterviewDateTime(
                    registration.candidate_token_expires_at,
                    registration.timezone,
                  ),
                })}
              </Typography>
            ) : null}

            <Divider />

            <TextField
              label={t("candidateInterview.fields.note")}
              value={note}
              onChange={(event) => setNote(event.target.value)}
              multiline
              minRows={3}
              helperText={t("candidateInterview.noteHelp")}
            />

            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <Button
                variant="contained"
                onClick={() => {
                  setFeedback(null);
                  confirmMutation.mutate();
                }}
                disabled={isMutating}
              >
                {confirmMutation.isPending
                  ? t("candidateInterview.actions.confirmPending")
                  : t("candidateInterview.actions.confirm")}
              </Button>
              <Button
                variant="outlined"
                onClick={() => {
                  setFeedback(null);
                  rescheduleMutation.mutate();
                }}
                disabled={isMutating}
              >
                {rescheduleMutation.isPending
                  ? t("candidateInterview.actions.reschedulePending")
                  : t("candidateInterview.actions.reschedule")}
              </Button>
              <Button
                variant="outlined"
                color="error"
                onClick={() => {
                  setFeedback(null);
                  cancelMutation.mutate();
                }}
                disabled={isMutating}
              >
                {cancelMutation.isPending
                  ? t("candidateInterview.actions.declinePending")
                  : t("candidateInterview.actions.decline")}
              </Button>
            </Stack>
          </Stack>
        </Paper>
      ) : null}
    </Stack>
  );
}

function resolveCandidateInterviewError(
  error: unknown,
  t: (key: string) => string,
): string {
  if (error instanceof ApiError) {
    const detail = error.detail.toLowerCase();
    if (detail.includes("interview_registration_not_found") || detail.includes("not found")) {
      return t("candidateInterview.errors.tokenNotFound");
    }
    if (detail.includes("interview_registration_token_expired") || detail.includes("expired")) {
      return t("candidateInterview.errors.tokenExpired");
    }
    if (detail.includes("does_not_allow")) {
      return t("candidateInterview.errors.invalidState");
    }
    const statusMessage = t(`candidateInterview.errors.http_${error.status}`);
    if (statusMessage !== `candidateInterview.errors.http_${error.status}`) {
      return statusMessage;
    }
  }
  return t("candidateInterview.errors.generic");
}

function resolveInterviewStatusChipColor(
  status: PublicInterviewRegistrationResponse["status"],
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
  status: PublicInterviewRegistrationResponse["calendar_sync_status"],
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
