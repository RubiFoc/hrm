import { useState } from "react";
import { Alert, Button, Divider, Paper, Stack, TextField, Typography } from "@mui/material";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import {
  ApiError,
  getCandidateCvAnalysis,
  getCandidateCvParsingStatus,
  type CandidateCvAnalysisResponse,
  type CandidateCvParsingStatusResponse,
} from "../api";

const candidateSchema = z.object({
  fullName: z.string().min(2),
  email: z.string().email(),
});

type CandidateForm = z.infer<typeof candidateSchema>;

export function CandidatePage() {
  const { t } = useTranslation();
  const [candidateIdInput, setCandidateIdInput] = useState("");
  const [selectedCandidateId, setSelectedCandidateId] = useState("");
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CandidateForm>({
    resolver: zodResolver(candidateSchema),
    defaultValues: { fullName: "", email: "" },
  });

  const onSubmit = (data: CandidateForm) => {
    console.log("candidate form", data);
  };

  const statusQuery = useQuery({
    queryKey: ["candidate-cv-status", selectedCandidateId],
    queryFn: () => getCandidateCvParsingStatus(selectedCandidateId),
    enabled: selectedCandidateId.length > 0,
    retry: false,
  });

  const analysisQuery = useQuery({
    queryKey: ["candidate-cv-analysis", selectedCandidateId],
    queryFn: () => getCandidateCvAnalysis(selectedCandidateId),
    enabled: selectedCandidateId.length > 0 && statusQuery.data?.analysis_ready === true,
    retry: false,
  });

  const handleLoadAnalysis = () => {
    setSelectedCandidateId(candidateIdInput.trim());
  };

  const statusError =
    statusQuery.error ? resolveCandidateApiError(statusQuery.error, t) : null;
  const analysisError =
    analysisQuery.error ? resolveCandidateApiError(analysisQuery.error, t) : null;

  return (
    <Stack spacing={2} component="form" onSubmit={handleSubmit(onSubmit)}>
      <Typography variant="h5">{t("candidateWorkspace")}</Typography>
      <TextField
        label="Full Name"
        {...register("fullName")}
        error={Boolean(errors.fullName)}
        helperText={errors.fullName?.message}
      />
      <TextField
        label="Email"
        {...register("email")}
        error={Boolean(errors.email)}
        helperText={errors.email?.message}
      />
      <Button variant="contained" component="label">
        {t("uploadCv")}
        <input hidden type="file" accept=".pdf,.doc,.docx" />
      </Button>
      <Button type="submit" variant="outlined">{t("signProfile")}</Button>
      <Button type="button" variant="contained">{t("registerInterview")}</Button>

      <Divider />

      <Paper sx={{ p: 2 }}>
        <Stack spacing={2}>
          <Typography variant="h6">{t("candidateCvAnalysis.title")}</Typography>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField
              fullWidth
              size="small"
              label={t("candidateCvAnalysis.candidateIdLabel")}
              placeholder={t("candidateCvAnalysis.candidateIdPlaceholder")}
              value={candidateIdInput}
              onChange={(event) => setCandidateIdInput(event.target.value)}
            />
            <Button variant="contained" onClick={handleLoadAnalysis}>
              {t("candidateCvAnalysis.load")}
            </Button>
          </Stack>

          {!selectedCandidateId ? (
            <Typography variant="body2">{t("candidateCvAnalysis.enterCandidateId")}</Typography>
          ) : null}

          {statusQuery.isLoading ? (
            <Typography variant="body2">{t("candidateCvAnalysis.loadingStatus")}</Typography>
          ) : null}

          {statusError ? <Alert severity="error">{statusError}</Alert> : null}

          {statusQuery.data ? <StatusCard status={statusQuery.data} /> : null}

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
            offsets: {item.start_offset}-{item.end_offset}
          </Typography>
        </Paper>
      ))}
    </Stack>
  );
}

function resolveCandidateApiError(error: unknown, t: (key: string) => string): string {
  if (error instanceof ApiError) {
    const detailMessage = t(`candidateCvAnalysis.errors.${error.detail}`);
    if (detailMessage !== `candidateCvAnalysis.errors.${error.detail}`) {
      return detailMessage;
    }
    const statusMessage = t(`candidateCvAnalysis.errors.http_${error.status}`);
    if (statusMessage !== `candidateCvAnalysis.errors.http_${error.status}`) {
      return statusMessage;
    }
  }
  return t("candidateCvAnalysis.errors.generic");
}
