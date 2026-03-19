import { FormEvent, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Grid2,
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
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import {
  ApiError,
  getBackendHealth,
  getCandidateCvParsingStatus,
  getMatchScore,
  listAuditEvents,
  type CandidateCvParsingStatusResponse,
  type MatchScoreResponse,
} from "../../api";
import { formatDateTime, normalizeFilterValue, type TranslationFn } from "./adminUtils";

const AUDIT_PREVIEW_LIMIT = 5;

type LookupFeedbackState = {
  type: "error" | "warning";
  message: string;
};

type ParsingQueryState = {
  candidateId: string;
  requestNonce: number;
};

type ScoringQueryState = {
  candidateId: string;
  requestNonce: number;
  vacancyId: string;
};

/**
 * Render the admin observability dashboard.
 *
 * Inputs:
 * - none; reads localization state and performs read-only lookup requests from the active browser session.
 *
 * Outputs:
 * - React element tree with backend health, audit preview, and job-status lookup panels.
 *
 * Side effects:
 * - issues read-only HTTP requests for `/health`, audit preview, CV parsing status, and match-score status.
 */
export function AdminObservabilityPage() {
  const { t } = useTranslation();
  const [parsingCandidateInput, setParsingCandidateInput] = useState("");
  const [parsingQueryState, setParsingQueryState] = useState<ParsingQueryState>({
    candidateId: "",
    requestNonce: 0,
  });
  const [parsingFeedback, setParsingFeedback] = useState<LookupFeedbackState | null>(null);
  const [scoringCandidateInput, setScoringCandidateInput] = useState("");
  const [scoringVacancyInput, setScoringVacancyInput] = useState("");
  const [scoringQueryState, setScoringQueryState] = useState<ScoringQueryState>({
    candidateId: "",
    requestNonce: 0,
    vacancyId: "",
  });
  const [scoringFeedback, setScoringFeedback] = useState<LookupFeedbackState | null>(null);

  const healthQuery = useQuery({
    queryKey: ["admin-observability-health"],
    queryFn: () => getBackendHealth(),
    retry: false,
  });

  const auditQuery = useQuery({
    queryKey: ["admin-observability-audit-preview", AUDIT_PREVIEW_LIMIT],
    queryFn: () => listAuditEvents({ limit: AUDIT_PREVIEW_LIMIT, offset: 0 }),
    retry: false,
  });

  const parsingStatusQuery = useQuery({
    queryKey: [
      "admin-observability-parsing-status",
      parsingQueryState.candidateId,
      parsingQueryState.requestNonce,
    ],
    queryFn: () => getCandidateCvParsingStatus(parsingQueryState.candidateId),
    enabled: Boolean(parsingQueryState.candidateId),
    retry: false,
  });

  const scoringStatusQuery = useQuery({
    queryKey: [
      "admin-observability-scoring-status",
      scoringQueryState.vacancyId,
      scoringQueryState.candidateId,
      scoringQueryState.requestNonce,
    ],
    queryFn: () =>
      getMatchScore(scoringQueryState.vacancyId, scoringQueryState.candidateId),
    enabled: Boolean(scoringQueryState.vacancyId && scoringQueryState.candidateId),
    retry: false,
  });

  const health = healthQuery.data ?? null;
  const healthCheckedAt = healthQuery.dataUpdatedAt > 0
    ? new Date(healthQuery.dataUpdatedAt).toISOString()
    : null;
  const auditItems = auditQuery.data?.items ?? [];

  const parsingErrorMessage = useMemo(() => {
    if (!parsingStatusQuery.error) {
      return "";
    }
    return resolveObservabilityErrorMessage(parsingStatusQuery.error, t);
  }, [parsingStatusQuery.error, t]);

  const scoringErrorMessage = useMemo(() => {
    if (!scoringStatusQuery.error) {
      return "";
    }
    return resolveObservabilityErrorMessage(scoringStatusQuery.error, t);
  }, [scoringStatusQuery.error, t]);

  const auditErrorMessage = useMemo(() => {
    if (!auditQuery.error) {
      return "";
    }
    return resolveObservabilityErrorMessage(auditQuery.error, t);
  }, [auditQuery.error, t]);

  const healthErrorMessage = useMemo(() => {
    if (!healthQuery.error) {
      return "";
    }
    return resolveObservabilityErrorMessage(healthQuery.error, t);
  }, [healthQuery.error, t]);

  const handleParsingLookupSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const candidateId = normalizeFilterValue(parsingCandidateInput);
    if (!candidateId) {
      setParsingFeedback({
        type: "warning",
        message: t("adminObservability.parsing.errors.candidateRequired"),
      });
      return;
    }

    setParsingFeedback(null);
    setParsingQueryState((prev) => ({
      candidateId,
      requestNonce: prev.requestNonce + 1,
    }));
  };

  const handleScoringLookupSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const vacancyId = normalizeFilterValue(scoringVacancyInput);
    const candidateId = normalizeFilterValue(scoringCandidateInput);
    if (!vacancyId) {
      setScoringFeedback({
        type: "warning",
        message: t("adminObservability.scoring.errors.vacancyRequired"),
      });
      return;
    }
    if (!candidateId) {
      setScoringFeedback({
        type: "warning",
        message: t("adminObservability.scoring.errors.candidateRequired"),
      });
      return;
    }

    setScoringFeedback(null);
    setScoringQueryState((prev) => ({
      candidateId,
      requestNonce: prev.requestNonce + 1,
      vacancyId,
    }));
  };

  return (
    <Stack spacing={2}>
      <Box>
        <Typography variant="h4">{t("adminObservability.title")}</Typography>
        <Typography variant="body2">{t("adminObservability.subtitle")}</Typography>
      </Box>

      <Paper sx={{ p: 2 }}>
        <Stack spacing={1.5}>
          <Typography variant="h6">{t("adminObservability.health.title")}</Typography>
          <Typography variant="body2" color="text.secondary">
            {t("adminObservability.health.subtitle")}
          </Typography>
          {healthQuery.isLoading ? (
            <Stack spacing={1} alignItems="center" sx={{ py: 2 }}>
              <CircularProgress size={24} />
              <Typography variant="body2">{t("adminObservability.health.loading")}</Typography>
            </Stack>
          ) : healthQuery.isError ? (
            <Alert severity="error">{healthErrorMessage}</Alert>
          ) : health ? (
            <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems="center">
              <Chip
                color={health.status === "ok" ? "success" : "warning"}
                label={t("adminObservability.health.status", { value: health.status })}
              />
              <Typography variant="body2">
                {t("adminObservability.health.checkedAt", {
                  value: formatDateTime(healthCheckedAt, t("adminObservability.notAvailable")),
                })}
              </Typography>
            </Stack>
          ) : null}
        </Stack>
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Stack spacing={1.5}>
          <Typography variant="h6">{t("adminObservability.audit.title")}</Typography>
          <Typography variant="body2" color="text.secondary">
            {t("adminObservability.audit.subtitle")}
          </Typography>
          {auditQuery.isLoading ? (
            <Stack spacing={1} alignItems="center" sx={{ py: 2 }}>
              <CircularProgress size={24} />
              <Typography variant="body2">{t("adminObservability.audit.loading")}</Typography>
            </Stack>
          ) : auditQuery.isError ? (
            <Alert severity="error">{auditErrorMessage}</Alert>
          ) : auditItems.length === 0 ? (
            <Alert severity="info">{t("adminObservability.audit.empty")}</Alert>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t("adminObservability.audit.table.occurredAt")}</TableCell>
                  <TableCell>{t("adminObservability.audit.table.source")}</TableCell>
                  <TableCell>{t("adminObservability.audit.table.action")}</TableCell>
                  <TableCell>{t("adminObservability.audit.table.result")}</TableCell>
                  <TableCell>{t("adminObservability.audit.table.reason")}</TableCell>
                  <TableCell>{t("adminObservability.audit.table.correlationId")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {auditItems.map((item) => (
                  <TableRow key={item.event_id}>
                    <TableCell>{formatDateTime(item.occurred_at, t("adminObservability.notAvailable"))}</TableCell>
                    <TableCell>{t(`adminObservability.audit.source.${item.source}`)}</TableCell>
                    <TableCell>{item.action}</TableCell>
                    <TableCell>{t(`adminObservability.audit.result.${item.result}`)}</TableCell>
                    <TableCell>{item.reason || t("adminObservability.notAvailable")}</TableCell>
                    <TableCell>{item.correlation_id || t("adminObservability.notAvailable")}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Stack>
      </Paper>

      <Grid2 container spacing={2}>
        <Grid2 size={{ xs: 12, lg: 6 }}>
          <Paper sx={{ p: 2, height: "100%" }}>
            <Stack spacing={1.5} component="form" onSubmit={handleParsingLookupSubmit}>
              <Typography variant="h6">{t("adminObservability.parsing.title")}</Typography>
              <Typography variant="body2" color="text.secondary">
                {t("adminObservability.parsing.subtitle")}
              </Typography>
              <TextField
                fullWidth
                label={t("adminObservability.parsing.fields.candidateId")}
                value={parsingCandidateInput}
                onChange={(event) => setParsingCandidateInput(event.target.value)}
              />
              <Stack direction="row" spacing={1.5}>
                <Button type="submit" variant="contained" disabled={parsingStatusQuery.isFetching}>
                  {parsingStatusQuery.isFetching
                    ? t("adminObservability.parsing.actions.loading")
                    : t("adminObservability.parsing.actions.load")}
                </Button>
              </Stack>
              {parsingFeedback ? (
                <Alert severity={parsingFeedback.type}>{parsingFeedback.message}</Alert>
              ) : null}
              {parsingStatusQuery.isLoading || parsingStatusQuery.isFetching ? (
                <Stack spacing={1} alignItems="center" sx={{ py: 2 }}>
                  <CircularProgress size={24} />
                  <Typography variant="body2">{t("adminObservability.parsing.loading")}</Typography>
                </Stack>
              ) : parsingStatusQuery.isError ? (
                <Alert severity="error">{parsingErrorMessage}</Alert>
              ) : parsingStatusQuery.data ? (
                <ParsingStatusResult
                  response={parsingStatusQuery.data}
                  t={t}
                />
              ) : (
                <Alert severity="info">{t("adminObservability.parsing.empty")}</Alert>
              )}
            </Stack>
          </Paper>
        </Grid2>

        <Grid2 size={{ xs: 12, lg: 6 }}>
          <Paper sx={{ p: 2, height: "100%" }}>
            <Stack spacing={1.5} component="form" onSubmit={handleScoringLookupSubmit}>
              <Typography variant="h6">{t("adminObservability.scoring.title")}</Typography>
              <Typography variant="body2" color="text.secondary">
                {t("adminObservability.scoring.subtitle")}
              </Typography>
              <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
                <TextField
                  fullWidth
                  label={t("adminObservability.scoring.fields.vacancyId")}
                  value={scoringVacancyInput}
                  onChange={(event) => setScoringVacancyInput(event.target.value)}
                />
                <TextField
                  fullWidth
                  label={t("adminObservability.scoring.fields.candidateId")}
                  value={scoringCandidateInput}
                  onChange={(event) => setScoringCandidateInput(event.target.value)}
                />
              </Stack>
              <Stack direction="row" spacing={1.5}>
                <Button type="submit" variant="contained" disabled={scoringStatusQuery.isFetching}>
                  {scoringStatusQuery.isFetching
                    ? t("adminObservability.scoring.actions.loading")
                    : t("adminObservability.scoring.actions.load")}
                </Button>
              </Stack>
              {scoringFeedback ? (
                <Alert severity={scoringFeedback.type}>{scoringFeedback.message}</Alert>
              ) : null}
              {scoringStatusQuery.isLoading || scoringStatusQuery.isFetching ? (
                <Stack spacing={1} alignItems="center" sx={{ py: 2 }}>
                  <CircularProgress size={24} />
                  <Typography variant="body2">{t("adminObservability.scoring.loading")}</Typography>
                </Stack>
              ) : scoringStatusQuery.isError ? (
                <Alert severity="error">{scoringErrorMessage}</Alert>
              ) : scoringStatusQuery.data ? (
                <ScoringStatusResult response={scoringStatusQuery.data} t={t} />
              ) : (
                <Alert severity="info">{t("adminObservability.scoring.empty")}</Alert>
              )}
            </Stack>
          </Paper>
        </Grid2>
      </Grid2>
    </Stack>
  );
}

type ParsingStatusResultProps = {
  response: CandidateCvParsingStatusResponse;
  t: TranslationFn;
};

function ParsingStatusResult({ response, t }: ParsingStatusResultProps) {
  return (
    <Stack spacing={1.25}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip
          color={resolveJobStatusColor(response.status)}
          label={t("adminObservability.parsing.details.status", {
            value: t(`adminObservability.status.${response.status}`),
          })}
        />
        <Chip
          variant="outlined"
          label={t("adminObservability.parsing.details.analysisReady", {
            value: response.analysis_ready ? t("adminObservability.yes") : t("adminObservability.no"),
          })}
        />
        <Chip
          variant="outlined"
          label={t("adminObservability.parsing.details.detectedLanguage", {
            value: t(`adminObservability.language.${response.detected_language}`),
          })}
        />
      </Stack>
      <Typography variant="body2">
        {t("adminObservability.parsing.details.candidateId", { value: response.candidate_id })}
      </Typography>
      <Typography variant="body2">
        {t("adminObservability.parsing.details.jobId", { value: response.job_id })}
      </Typography>
      <Typography variant="body2">
        {t("adminObservability.parsing.details.documentId", { value: response.document_id })}
      </Typography>
      <Typography variant="body2">
        {t("adminObservability.parsing.details.attemptCount", {
          value: response.attempt_count,
        })}
      </Typography>
      <Typography variant="body2">
        {t("adminObservability.parsing.details.updatedAt", {
          value: formatDateTime(response.updated_at, t("adminObservability.notAvailable")),
        })}
      </Typography>
      {response.queued_at ? (
        <Typography variant="body2">
          {t("adminObservability.parsing.details.queuedAt", {
            value: formatDateTime(response.queued_at, t("adminObservability.notAvailable")),
          })}
        </Typography>
      ) : null}
      {response.started_at ? (
        <Typography variant="body2">
          {t("adminObservability.parsing.details.startedAt", {
            value: formatDateTime(response.started_at, t("adminObservability.notAvailable")),
          })}
        </Typography>
      ) : null}
      {response.finished_at ? (
        <Typography variant="body2">
          {t("adminObservability.parsing.details.finishedAt", {
            value: formatDateTime(response.finished_at, t("adminObservability.notAvailable")),
          })}
        </Typography>
      ) : null}
      {response.last_error ? <Alert severity="warning">{response.last_error}</Alert> : null}
    </Stack>
  );
}

type ScoringStatusResultProps = {
  response: MatchScoreResponse;
  t: TranslationFn;
};

function ScoringStatusResult({ response, t }: ScoringStatusResultProps) {
  const score = formatDecimal(response.score);
  const confidence = formatDecimal(response.confidence);

  return (
    <Stack spacing={1.25}>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip
          color={resolveJobStatusColor(response.status)}
          label={t("adminObservability.scoring.details.status", {
            value: t(`adminObservability.status.${response.status}`),
          })}
        />
        <Chip
          variant="outlined"
          label={t("adminObservability.scoring.details.score", {
            value: score ?? t("adminObservability.notAvailable"),
          })}
        />
        <Chip
          variant="outlined"
          label={t("adminObservability.scoring.details.confidence", {
            value: confidence ?? t("adminObservability.notAvailable"),
          })}
        />
        <Chip
          color={response.requires_manual_review ? "warning" : "default"}
          variant="outlined"
          label={t("adminObservability.scoring.details.manualReview", {
            value: response.requires_manual_review ? t("adminObservability.yes") : t("adminObservability.no"),
          })}
        />
      </Stack>
      <Typography variant="body2">
        {t("adminObservability.scoring.details.vacancyId", { value: response.vacancy_id })}
      </Typography>
      <Typography variant="body2">
        {t("adminObservability.scoring.details.candidateId", { value: response.candidate_id })}
      </Typography>
      <Typography variant="body2">
        {t("adminObservability.scoring.details.summary", {
          value: response.summary || t("adminObservability.notAvailable"),
        })}
      </Typography>
      <Typography variant="body2">
        {t("adminObservability.scoring.details.scoredAt", {
          value: formatDateTime(response.scored_at, t("adminObservability.notAvailable")),
        })}
      </Typography>
      {response.model_name || response.model_version ? (
        <Typography variant="body2">
          {t("adminObservability.scoring.details.model", {
            value: [response.model_name, response.model_version].filter(Boolean).join(" / "),
          })}
        </Typography>
      ) : null}
      {response.manual_review_reason ? (
        <Alert severity="warning">
          {t(`adminObservability.scoring.manualReviewReasons.${response.manual_review_reason}`)}
        </Alert>
      ) : null}
    </Stack>
  );
}

function resolveJobStatusColor(
  status: CandidateCvParsingStatusResponse["status"] | MatchScoreResponse["status"],
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

function formatDecimal(value: number | null | undefined): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  return value.toFixed(2);
}

function resolveObservabilityErrorMessage(error: unknown, t: TranslationFn): string {
  if (error instanceof Error && !(error instanceof ApiError)) {
    return error.message;
  }
  if (error instanceof ApiError) {
    const detail = error.detail.trim().toLowerCase();
    if (detail.includes("candidate not found")) {
      return t("adminObservability.errors.candidate_not_found");
    }
    if (detail.includes("vacancy not found")) {
      return t("adminObservability.errors.vacancy_not_found");
    }
    if (detail.includes("match score not found")) {
      return t("adminObservability.errors.match_score_not_found");
    }
    if (detail.includes("cv analysis is not ready")) {
      return t("adminObservability.errors.cv_analysis_not_ready");
    }
    if (detail.includes("invalid time range")) {
      return t("adminObservability.errors.invalid_time_range");
    }
    const normalizedDetail = detail.replace(/\s+/g, "_");
    const detailKey = `adminObservability.errors.${normalizedDetail}`;
    const detailMessage = t(detailKey);
    if (detailMessage !== detailKey) {
      return detailMessage;
    }
    const statusKey = `adminObservability.errors.http_${error.status}`;
    const statusMessage = t(statusKey);
    if (statusMessage !== statusKey) {
      return statusMessage;
    }
  }
  return t("adminObservability.errors.generic");
}
