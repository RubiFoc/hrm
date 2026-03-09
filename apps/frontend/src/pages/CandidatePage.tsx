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
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { z } from "zod";

import {
  ApiError,
  applyToVacancyPublic,
  cancelPublicInterviewRegistration,
  confirmPublicInterviewRegistration,
  getPublicCandidateCvAnalysis,
  getPublicCandidateCvParsingStatus,
  getPublicInterviewRegistration,
  requestPublicInterviewReschedule,
  type CandidateCvAnalysisResponse,
  type CandidateCvParsingStatusResponse,
  type PublicInterviewRegistrationResponse,
  type PublicVacancyApplicationRequest,
} from "../api";
import {
  readCandidateApplicationContext,
  writeCandidateApplicationContext,
  type CandidateApplicationContext,
} from "../app/candidate/applicationContext";
import { useSentryRouteTags } from "../app/observability/sentry";

const CANDIDATE_FORM_SCHEMA = z.object({
  first_name: z.string().trim().min(1),
  last_name: z.string().trim().min(1),
  email: z.string().trim().email(),
  phone: z.string().trim().min(3),
  location: z.string().trim().max(256).optional().or(z.literal("")),
  current_title: z.string().trim().max(256).optional().or(z.literal("")),
});
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const ACCEPT_ATTRIBUTE = ".pdf,.doc,.docx";

type CandidateForm = z.infer<typeof CANDIDATE_FORM_SCHEMA>;
type CandidateApplyMutationRequest = {
  vacancyId: string;
  payload: PublicVacancyApplicationRequest;
};
type FeedbackState = {
  type: "success" | "error";
  message: string;
};

/**
 * Public candidate workspace with both vacancy-apply and interview-registration modes.
 */
export function CandidatePage() {
  const { t } = useTranslation();
  useSentryRouteTags("/candidate");
  const [searchParams] = useSearchParams();
  const queryVacancyId = normalizeInput(searchParams.get("vacancyId"));
  const queryVacancyTitle = normalizeInput(searchParams.get("vacancyTitle"));
  const interviewToken = normalizeInput(searchParams.get("interviewToken"));
  const hasMixedRouteParams = Boolean(queryVacancyId && interviewToken);

  if (hasMixedRouteParams) {
    return (
      <Stack spacing={3}>
        <Stack spacing={1}>
          <Typography variant="h4">{t("candidateWorkspace")}</Typography>
          <Typography variant="body2" color="text.secondary">
            {t("candidateRoute.invalidLinkSubtitle")}
          </Typography>
        </Stack>
        <Alert severity="error">{t("candidateRoute.invalidLink")}</Alert>
      </Stack>
    );
  }

  if (interviewToken) {
    return <CandidateInterviewRegistrationMode interviewToken={interviewToken} />;
  }

  return (
    <CandidateApplyTrackingMode
      queryVacancyId={queryVacancyId}
      queryVacancyTitle={queryVacancyTitle}
    />
  );
}

function CandidateInterviewRegistrationMode({ interviewToken }: { interviewToken: string }) {
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
      <Stack spacing={1}>
        <Typography variant="h4">{t("candidateWorkspace")}</Typography>
        <Typography variant="body2" color="text.secondary">
          {t("candidateInterview.subtitle")}
        </Typography>
      </Stack>

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
        <Paper sx={{ p: 2 }}>
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
                  label={t(
                    `candidateInterview.syncStatus.${registration.calendar_sync_status}`,
                  )}
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
                {t(
                  `candidateInterview.responseStatus.${registration.candidate_response_status}`,
                )}
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

function CandidateApplyTrackingMode({
  queryVacancyId,
  queryVacancyTitle,
}: {
  queryVacancyId: string | null;
  queryVacancyTitle: string | null;
}) {
  const { t } = useTranslation();
  const storedContext = readCandidateApplicationContext();
  const [vacancyIdInput, setVacancyIdInput] = useState(queryVacancyId ?? "");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileFeedback, setFileFeedback] = useState<string | null>(null);
  const [applyFeedback, setApplyFeedback] = useState<string | null>(null);
  const [trackingFeedback, setTrackingFeedback] = useState<string | null>(null);
  const [isChecksumPending, setIsChecksumPending] = useState(false);
  const [trackingJobInput, setTrackingJobInput] = useState(storedContext?.parsingJobId ?? "");
  const [selectedTrackingJobId, setSelectedTrackingJobId] = useState(
    storedContext?.parsingJobId ?? "",
  );
  const [latestContext, setLatestContext] = useState<CandidateApplicationContext | null>(
    storedContext,
  );
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CandidateForm>({
    resolver: zodResolver(CANDIDATE_FORM_SCHEMA),
    defaultValues: {
      first_name: "",
      last_name: "",
      email: "",
      phone: "",
      location: "",
      current_title: "",
    },
  });

  const applyMutation = useMutation({
    mutationFn: ({ vacancyId, payload }: CandidateApplyMutationRequest) =>
      applyToVacancyPublic(vacancyId, payload),
  });

  const statusQuery = useQuery({
    queryKey: ["candidate-public-status", selectedTrackingJobId],
    queryFn: () => getPublicCandidateCvParsingStatus(selectedTrackingJobId),
    enabled: selectedTrackingJobId.length > 0,
    retry: false,
    refetchInterval: (query) => {
      const currentStatus = query.state.data?.status;
      if (currentStatus && !isTerminalStatus(currentStatus)) {
        return 5000;
      }
      return false;
    },
  });

  const analysisQuery = useQuery({
    queryKey: ["candidate-public-analysis", selectedTrackingJobId],
    queryFn: () => getPublicCandidateCvAnalysis(selectedTrackingJobId),
    enabled: selectedTrackingJobId.length > 0 && statusQuery.data?.analysis_ready === true,
    retry: false,
  });

  const resolvedVacancyId = queryVacancyId ?? vacancyIdInput.trim();
  const resolvedVacancyTitle = queryVacancyTitle ?? latestContext?.vacancyTitle ?? null;
  const isDiagnosticMode = !queryVacancyId;

  const onSubmit = async (values: CandidateForm) => {
    setApplyFeedback(null);
    setTrackingFeedback(null);

    if (!UUID_PATTERN.test(resolvedVacancyId)) {
      setApplyFeedback(t("candidateApply.errors.invalidVacancyId"));
      return;
    }

    if (!selectedFile) {
      setFileFeedback(t("candidateApply.errors.fileRequired"));
      return;
    }

    const fileError = validateCandidateFile(selectedFile, t);
    if (fileError) {
      setFileFeedback(fileError);
      return;
    }

    setFileFeedback(null);
    setIsChecksumPending(true);
    try {
      const checksumSha256 = await computeFileChecksumSha256(selectedFile);
      const response = await applyMutation.mutateAsync({
        vacancyId: resolvedVacancyId,
        payload: {
          ...values,
          location: normalizeInput(values.location),
          current_title: normalizeInput(values.current_title),
          checksum_sha256: checksumSha256,
          file: selectedFile,
        },
      });
      const nextContext: CandidateApplicationContext = {
        vacancyId: response.vacancy_id,
        vacancyTitle: resolvedVacancyTitle,
        candidateId: response.candidate_id,
        parsingJobId: response.parsing_job_id,
      };
      writeCandidateApplicationContext(nextContext);
      setLatestContext(nextContext);
      setTrackingJobInput(response.parsing_job_id);
      setSelectedTrackingJobId(response.parsing_job_id);
    } catch (error) {
      setApplyFeedback(resolveCandidateApplyError(error, t));
    } finally {
      setIsChecksumPending(false);
    }
  };

  const handleTrackingLookup = () => {
    const normalized = trackingJobInput.trim();
    setTrackingFeedback(null);
    if (!UUID_PATTERN.test(normalized)) {
      setTrackingFeedback(t("candidateTracking.errors.invalidJobId"));
      return;
    }
    setSelectedTrackingJobId(normalized);
  };

  const statusError = statusQuery.error ? resolveCandidateTrackingError(statusQuery.error, t) : null;
  const analysisError = analysisQuery.error
    ? resolveCandidateTrackingError(analysisQuery.error, t)
    : null;
  const submissionSuccessMessage = buildSubmissionSuccessMessage(
    latestContext,
    statusQuery.data,
    t,
  );

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4">{t("candidateWorkspace")}</Typography>
        <Typography variant="body2" color="text.secondary">
          {t("candidateApply.subtitle")}
        </Typography>
      </Stack>

      {isDiagnosticMode ? (
        <Alert severity="info">{t("candidateApply.diagnosticMode")}</Alert>
      ) : null}

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2} component="form" onSubmit={handleSubmit(onSubmit)}>
          <Typography variant="h6">{t("candidateApply.title")}</Typography>
          <Typography variant="body2" color="text.secondary">
            {resolvedVacancyTitle
              ? t("candidateApply.vacancySummary", { vacancyTitle: resolvedVacancyTitle })
              : t("candidateApply.vacancySummaryFallback")}
          </Typography>

          {isDiagnosticMode ? (
            <TextField
              label={t("candidateApply.fields.vacancyId")}
              value={vacancyIdInput}
              onChange={(event) => setVacancyIdInput(event.target.value)}
              helperText={t("candidateApply.fields.vacancyIdHelp")}
            />
          ) : (
            <TextField
              label={t("candidateApply.fields.vacancyId")}
              value={resolvedVacancyId}
              InputProps={{ readOnly: true }}
            />
          )}

          <TextField
            label={t("candidateApply.fields.firstName")}
            {...register("first_name")}
            error={Boolean(errors.first_name)}
            helperText={errors.first_name ? t("candidateApply.errors.requiredField") : " "}
          />
          <TextField
            label={t("candidateApply.fields.lastName")}
            {...register("last_name")}
            error={Boolean(errors.last_name)}
            helperText={errors.last_name ? t("candidateApply.errors.requiredField") : " "}
          />
          <TextField
            label={t("candidateApply.fields.email")}
            {...register("email")}
            error={Boolean(errors.email)}
            helperText={errors.email ? t("candidateApply.errors.invalidEmail") : " "}
          />
          <TextField
            label={t("candidateApply.fields.phone")}
            {...register("phone")}
            error={Boolean(errors.phone)}
            helperText={errors.phone ? t("candidateApply.errors.requiredField") : " "}
          />
          <TextField
            label={t("candidateApply.fields.location")}
            {...register("location")}
            error={Boolean(errors.location)}
            helperText={errors.location ? t("candidateApply.errors.invalidLocation") : " "}
          />
          <TextField
            label={t("candidateApply.fields.currentTitle")}
            {...register("current_title")}
            error={Boolean(errors.current_title)}
            helperText={errors.current_title ? t("candidateApply.errors.invalidCurrentTitle") : " "}
          />

          <Button variant="contained" component="label">
            {selectedFile
              ? t("candidateApply.fileSelected", { filename: selectedFile.name })
              : t("candidateApply.fields.cvFile")}
            <input
              hidden
              type="file"
              accept={ACCEPT_ATTRIBUTE}
              onChange={(event) => {
                const nextFile = event.target.files?.[0] ?? null;
                setSelectedFile(nextFile);
                setFileFeedback(validateCandidateFile(nextFile, t));
              }}
            />
          </Button>

          {fileFeedback ? <Alert severity="error">{fileFeedback}</Alert> : null}
          {applyFeedback ? <Alert severity="error">{applyFeedback}</Alert> : null}
          {submissionSuccessMessage ? (
            <Alert severity="success">{submissionSuccessMessage}</Alert>
          ) : null}

          <Button
            type="submit"
            variant="contained"
            disabled={applyMutation.isPending || isChecksumPending}
          >
            {applyMutation.isPending || isChecksumPending
              ? t("candidateApply.submitPending")
              : t("candidateApply.submit")}
          </Button>
        </Stack>
      </Paper>

      <Divider />

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Typography variant="h6">{t("candidateTracking.title")}</Typography>
          <Typography variant="body2" color="text.secondary">
            {t("candidateTracking.subtitle")}
          </Typography>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField
              fullWidth
              size="small"
              label={t("candidateTracking.jobIdLabel")}
              placeholder={t("candidateTracking.jobIdPlaceholder")}
              value={trackingJobInput}
              onChange={(event) => setTrackingJobInput(event.target.value)}
            />
            <Button variant="contained" onClick={handleTrackingLookup}>
              {t("candidateTracking.load")}
            </Button>
          </Stack>

          {!selectedTrackingJobId ? (
            <Typography variant="body2">{t("candidateTracking.enterJobId")}</Typography>
          ) : null}

          {trackingFeedback ? <Alert severity="error">{trackingFeedback}</Alert> : null}
          {statusQuery.isLoading ? (
            <Typography variant="body2">{t("candidateCvAnalysis.loadingStatus")}</Typography>
          ) : null}
          {statusError ? <Alert severity="error">{statusError}</Alert> : null}
          {statusQuery.data ? <StatusCard status={statusQuery.data} /> : null}
          {statusQuery.data?.status === "failed" && statusQuery.data.last_error ? (
            <Alert severity="error">
              {t("candidateCvAnalysis.failedReason", {
                reason: statusQuery.data.last_error,
              })}
            </Alert>
          ) : null}
          {statusQuery.data && !statusQuery.data.analysis_ready ? (
            <Alert severity="info">{t("candidateCvAnalysis.notReady")}</Alert>
          ) : null}

          {analysisQuery.isLoading ? (
            <Typography variant="body2">{t("candidateCvAnalysis.loadingAnalysis")}</Typography>
          ) : null}
          {analysisError ? <Alert severity="error">{analysisError}</Alert> : null}
          {analysisQuery.data ? <AnalysisCard analysis={analysisQuery.data} /> : null}
        </Stack>
      </Paper>
    </Stack>
  );
}

function StatusCard({ status }: { status: CandidateCvParsingStatusResponse }) {
  const { t } = useTranslation();
  return (
    <Stack spacing={1}>
      <Typography variant="body2">
        {t("candidateCvAnalysis.statusLabel")}: {t(`candidateCvAnalysis.status.${status.status}`)}
      </Typography>
      <Typography variant="body2">
        {t("candidateCvAnalysis.languageLabel")}:{" "}
        {t(`candidateCvAnalysis.language.${status.detected_language}`)}
      </Typography>
      <Typography variant="body2">
        {t("candidateCvAnalysis.analysisReadyLabel")}:{" "}
        {status.analysis_ready ? t("candidateCvAnalysis.yes") : t("candidateCvAnalysis.no")}
      </Typography>
      <Typography variant="body2">
        {t("candidateCvAnalysis.candidateIdLabel")}: {status.candidate_id}
      </Typography>
      <Typography variant="body2">
        {t("candidateTracking.jobIdLabel")}: {status.job_id}
      </Typography>
      <Typography variant="body2">
        {t("candidateCvAnalysis.updatedAtLabel")}: {formatDateTime(status.updated_at)}
      </Typography>
    </Stack>
  );
}

function AnalysisCard({ analysis }: { analysis: CandidateCvAnalysisResponse }) {
  const { t } = useTranslation();
  return (
    <Stack spacing={1}>
      <Typography variant="subtitle2">{t("candidateCvAnalysis.profileLabel")}</Typography>
      <Paper variant="outlined" sx={{ p: 1.5, bgcolor: "grey.50" }}>
        <Typography
          component="pre"
          sx={{
            margin: 0,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
            fontSize: 12,
          }}
        >
          {JSON.stringify(analysis.parsed_profile, null, 2)}
        </Typography>
      </Paper>
      <Typography variant="subtitle2">{t("candidateCvAnalysis.evidenceLabel")}</Typography>
      {analysis.evidence.length === 0 ? (
        <Typography variant="body2">{t("candidateCvAnalysis.noEvidence")}</Typography>
      ) : null}
      {analysis.evidence.map((item, index) => (
        <Paper key={`${item.field}-${index}`} variant="outlined" sx={{ p: 1.5 }}>
          <Typography variant="body2">
            <strong>{item.field}</strong>
          </Typography>
          <Typography variant="body2">{item.snippet}</Typography>
          <Typography variant="caption" color="text.secondary">
            {t("candidateCvAnalysis.offsetsLabel", {
              start: item.start_offset,
              end: item.end_offset,
            })}
          </Typography>
        </Paper>
      ))}
    </Stack>
  );
}

function validateCandidateFile(
  file: File | null,
  t: (key: string, options?: Record<string, string | number>) => string,
): string | null {
  if (!file) {
    return null;
  }
  const filename = file.name.toLowerCase();
  const mimeType = file.type.toLowerCase();
  const isAcceptedExtension =
    filename.endsWith(".pdf") || filename.endsWith(".doc") || filename.endsWith(".docx");
  const isAcceptedMime =
    mimeType === "application/pdf"
    || mimeType === "application/msword"
    || mimeType
      === "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  if (!isAcceptedExtension && !isAcceptedMime) {
    return t("candidateApply.errors.fileType");
  }
  return null;
}

async function computeFileChecksumSha256(file: File): Promise<string> {
  const payload = await file.arrayBuffer();
  const digest = await window.crypto.subtle.digest("SHA-256", payload);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function normalizeInput(value: string | null | undefined): string | null {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString();
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

function isTerminalStatus(status: CandidateCvParsingStatusResponse["status"]): boolean {
  return status === "succeeded" || status === "failed";
}

function buildSubmissionSuccessMessage(
  context: CandidateApplicationContext | null,
  status: CandidateCvParsingStatusResponse | undefined,
  t: (key: string, options?: Record<string, string>) => string,
): string | null {
  if (!context) {
    return null;
  }
  return t("candidateApply.success", {
    candidateId: context.candidateId,
    trackingJobId: context.parsingJobId,
    status: status?.status ?? "queued",
  });
}

function resolveCandidateApplyError(
  error: unknown,
  t: (key: string) => string,
): string {
  if (error instanceof ApiError) {
    const detail = error.detail.toLowerCase();
    if (detail.includes("vacancy not found")) {
      return t("candidateApply.errors.vacancyNotFound");
    }
    if (detail.includes("not open for applications")) {
      return t("candidateApply.errors.vacancyClosed");
    }
    if (detail.includes("duplicate submission")) {
      return t("candidateApply.errors.duplicateSubmission");
    }
    if (detail.includes("cooldown active")) {
      return t("candidateApply.errors.cooldownActive");
    }
    if (detail.includes("bot submission detected")) {
      return t("candidateApply.errors.botSubmission");
    }
    const statusMessage = t(`candidateApply.errors.http_${error.status}`);
    if (statusMessage !== `candidateApply.errors.http_${error.status}`) {
      return statusMessage;
    }
  }
  return t("candidateApply.errors.generic");
}

function resolveCandidateTrackingError(
  error: unknown,
  t: (key: string) => string,
): string {
  if (error instanceof ApiError) {
    const detail = error.detail.toLowerCase();
    if (detail.includes("analysis is not ready")) {
      return t("candidateTracking.errors.analysisNotReady");
    }
    if (detail.includes("cv parsing job is not available")) {
      return t("candidateTracking.errors.jobNotFound");
    }
    const statusMessage = t(`candidateTracking.errors.http_${error.status}`);
    if (statusMessage !== `candidateTracking.errors.http_${error.status}`) {
      return statusMessage;
    }
  }
  return t("candidateTracking.errors.generic");
}

function resolveCandidateInterviewError(
  error: unknown,
  t: (key: string) => string,
): string {
  if (error instanceof ApiError) {
    const detail = error.detail.toLowerCase();
    if (
      detail.includes("interview_registration_not_found")
      || detail.includes("not found")
    ) {
      return t("candidateInterview.errors.tokenNotFound");
    }
    if (
      detail.includes("interview_registration_token_expired")
      || detail.includes("expired")
    ) {
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
