import { useState } from "react";
import {
  Alert,
  Box,
  Button,
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
  ApiError,
  createPipelineTransition,
  createVacancy,
  listCandidateProfiles,
  listPipelineTransitions,
  listVacancies,
  updateVacancy,
  type CandidateResponse,
  type PipelineTransitionCreateRequest,
  type VacancyCreateRequest,
  type VacancyResponse,
  type VacancyUpdateRequest,
} from "../api";
import { readAuthSession } from "../app/auth/session";

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

type VacancyDraft = VacancyCreateRequest;

const DEFAULT_VACANCY_DRAFT: VacancyDraft = {
  title: "",
  description: "",
  department: "",
  status: "open",
};

/**
 * Staff recruitment workspace for vacancy CRUD and pipeline control.
 */
export function HrDashboardPage() {
  const { t } = useTranslation();
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
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveRecruitmentApiError(error, t) });
    },
  });

  const vacancyItems = vacanciesQuery.data?.items ?? [];
  const candidateItems = candidatesQuery.data?.items ?? [];
  const selectedVacancy =
    vacancyItems.find((item) => item.vacancy_id === selectedVacancyId) ?? null;
  const selectedCandidate =
    candidateItems.find((item) => item.candidate_id === selectedCandidateId) ?? null;

  const handleSelectVacancy = (vacancy: VacancyResponse) => {
    setSelectedVacancyId(vacancy.vacancy_id);
    setEditDraft(toVacancyDraft(vacancy));
    setFeedback(null);
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
              onChange={(event) => setSelectedCandidateId(event.target.value)}
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

function normalizeInput(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function resolveRecruitmentApiError(
  error: unknown,
  t: (key: string) => string,
): string {
  if (error instanceof ApiError) {
    const detail = error.detail.toLowerCase();
    if (detail.includes("vacancy not found")) {
      return t("hrDashboard.errors.vacancyNotFound");
    }
    if (detail.includes("candidate not found")) {
      return t("hrDashboard.errors.candidateNotFound");
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
