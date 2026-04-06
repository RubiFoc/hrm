import { useState } from "react";
import {
  Alert,
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
  createVacancy,
  createSalaryBand,
  listSalaryBands,
  listVacancies,
  updateVacancy,
  type VacancyResponse,
  type VacancyUpdateRequest,
} from "../../api";
import { readAuthSession } from "../../app/auth/session";
import { PageHero } from "../../components/PageHero";
import { HrWorkspaceNav } from "./HrWorkspaceNav";
import { resolveCompensationApiError } from "../compensation/compensationErrors";
import {
  DEFAULT_VACANCY_DRAFT,
  type FeedbackState,
  type VacancyDraft,
  buildVacancyPatchPayload,
  formatDateTime,
  resolveRecruitmentApiError,
  toVacancyDraft,
} from "./hrWorkspaceShared";

/**
 * Focused vacancy management page for the HR workspace.
 */
export function HrVacanciesPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const session = readAuthSession();
  const accessToken = session.accessToken;
  const [selectedVacancyId, setSelectedVacancyId] = useState("");
  const [createDraft, setCreateDraft] = useState<VacancyDraft>(DEFAULT_VACANCY_DRAFT);
  const [editDraft, setEditDraft] = useState<VacancyDraft>(DEFAULT_VACANCY_DRAFT);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const [bandMin, setBandMin] = useState("");
  const [bandMax, setBandMax] = useState("");
  const [bandFeedback, setBandFeedback] = useState<FeedbackState | null>(null);

  const vacanciesQuery = useQuery({
    queryKey: ["hr-vacancies", accessToken],
    queryFn: () => listVacancies(),
    enabled: Boolean(accessToken),
  });

  const vacancyItems = vacanciesQuery.data?.items ?? [];
  const selectedVacancy =
    vacancyItems.find((item) => item.vacancy_id === selectedVacancyId) ?? null;

  const salaryBandsQuery = useQuery({
    queryKey: ["salary-bands", accessToken, selectedVacancyId],
    queryFn: () => listSalaryBands(accessToken!, selectedVacancyId),
    enabled: Boolean(accessToken && selectedVacancyId),
    retry: false,
  });
  const salaryBandItems = salaryBandsQuery.data?.items ?? [];

  const createVacancyMutation = useMutation({
    mutationFn: (payload: VacancyDraft) => createVacancy(payload),
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
    mutationFn: (payload: VacancyUpdateRequest) => updateVacancy(selectedVacancyId, payload),
    onSuccess: (vacancy) => {
      setFeedback({ type: "success", message: t("hrDashboard.updateSuccess") });
      setEditDraft(toVacancyDraft(vacancy));
      void queryClient.invalidateQueries({ queryKey: ["hr-vacancies"] });
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveRecruitmentApiError(error, t) });
    },
  });

  const createSalaryBandMutation = useMutation({
    mutationFn: ({ vacancyId, minAmount, maxAmount }: { vacancyId: string; minAmount: number; maxAmount: number }) =>
      createSalaryBand(accessToken!, {
        vacancy_id: vacancyId,
        min_amount: minAmount,
        max_amount: maxAmount,
      }),
    onSuccess: () => {
      setBandFeedback({ type: "success", message: t("compensationBand.createSuccess") });
      setBandMin("");
      setBandMax("");
      void queryClient.invalidateQueries({ queryKey: ["salary-bands", accessToken, selectedVacancyId] });
    },
    onError: (error: unknown) => {
      setBandFeedback({ type: "error", message: resolveCompensationApiError(error, t) });
    },
  });

  const handleSelectVacancy = (vacancy: VacancyResponse) => {
    setSelectedVacancyId(vacancy.vacancy_id);
    setEditDraft(toVacancyDraft(vacancy));
    setFeedback(null);
    setBandFeedback(null);
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

  const handleCreateSalaryBand = () => {
    if (!selectedVacancy) {
      setBandFeedback({ type: "error", message: t("compensationBand.errors.selectVacancy") });
      return;
    }
    const minValue = Number.parseFloat(bandMin);
    const maxValue = Number.parseFloat(bandMax);
    if (!Number.isFinite(minValue) || minValue <= 0) {
      setBandFeedback({ type: "error", message: t("compensationBand.errors.minRequired") });
      return;
    }
    if (!Number.isFinite(maxValue) || maxValue <= 0) {
      setBandFeedback({ type: "error", message: t("compensationBand.errors.maxRequired") });
      return;
    }
    if (minValue > maxValue) {
      setBandFeedback({ type: "error", message: t("compensationBand.errors.rangeInvalid") });
      return;
    }
    setBandFeedback(null);
    createSalaryBandMutation.mutate({
      vacancyId: selectedVacancy.vacancy_id,
      minAmount: minValue,
      maxAmount: maxValue,
    });
  };

  if (!accessToken) {
    return <Alert severity="info">{t("hrDashboard.authRequired")}</Alert>;
  }

  return (
    <Stack spacing={3}>
      <PageHero
        eyebrow={t("hrDashboard.title")}
        title={t("hrWorkspacePages.vacancies.title")}
        description={t("hrWorkspacePages.vacancies.subtitle")}
        imageSrc="/images/company-hero.jpg"
        imageAlt={t("hrDashboard.title")}
        chips={[
          t("hrDashboard.createSectionTitle"),
          t("hrDashboard.editSectionTitle"),
          t("hrWorkspaceNav.workbench"),
        ]}
      />

      <HrWorkspaceNav />

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
          <Stack spacing={0.5}>
            <Typography variant="h6">{t("compensationBand.title")}</Typography>
            <Typography variant="body2" color="text.secondary">
              {t("compensationBand.subtitle")}
            </Typography>
          </Stack>

          {bandFeedback ? <Alert severity={bandFeedback.type}>{bandFeedback.message}</Alert> : null}

          {!selectedVacancy ? (
            <Alert severity="info">{t("compensationBand.selectVacancyPrompt")}</Alert>
          ) : (
            <>
              <Typography variant="body2" color="text.secondary">
                {t("compensationBand.selectedVacancy", {
                  vacancyTitle: selectedVacancy.title,
                  vacancyId: selectedVacancy.vacancy_id,
                })}
              </Typography>
              <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
                <TextField
                  label={t("compensationBand.fields.minAmount")}
                  type="number"
                  value={bandMin}
                  onChange={(event) => setBandMin(event.target.value)}
                  fullWidth
                />
                <TextField
                  label={t("compensationBand.fields.maxAmount")}
                  type="number"
                  value={bandMax}
                  onChange={(event) => setBandMax(event.target.value)}
                  fullWidth
                />
              </Stack>
              <Button
                variant="contained"
                onClick={handleCreateSalaryBand}
                disabled={createSalaryBandMutation.isPending}
              >
                {createSalaryBandMutation.isPending
                  ? t("compensationBand.createPending")
                  : t("compensationBand.createAction")}
              </Button>

              <Typography variant="subtitle1">{t("compensationBand.historyTitle")}</Typography>
              {salaryBandsQuery.isLoading ? (
                <Stack spacing={2} alignItems="center" sx={{ py: 2 }}>
                  <Typography variant="body2">{t("compensationBand.loading")}</Typography>
                </Stack>
              ) : salaryBandsQuery.isError ? (
                <Alert severity="error" sx={{ borderRadius: 0 }}>
                  {resolveCompensationApiError(salaryBandsQuery.error, t)}
                </Alert>
              ) : salaryBandItems.length === 0 ? (
                <Alert severity="info" sx={{ borderRadius: 0 }}>
                  {t("compensationBand.empty")}
                </Alert>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>{t("compensationBand.columns.version")}</TableCell>
                      <TableCell>{t("compensationBand.columns.range")}</TableCell>
                      <TableCell>{t("compensationBand.columns.createdBy")}</TableCell>
                      <TableCell>{t("compensationBand.columns.createdAt")}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {salaryBandItems.map((band) => (
                      <TableRow key={band.band_id}>
                        <TableCell>{band.band_version}</TableCell>
                        <TableCell>
                          {band.min_amount.toFixed(2)} - {band.max_amount.toFixed(2)} {band.currency}
                        </TableCell>
                        <TableCell>{band.created_by_staff_id.slice(0, 8)}</TableCell>
                        <TableCell>{formatDateTime(band.created_at)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </>
          )}
        </Stack>
      </Paper>
    </Stack>
  );
}
