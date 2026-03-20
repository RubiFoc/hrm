import { useMemo } from "react";
import {
  Alert,
  Button,
  Chip,
  Grid2,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useParams, useSearchParams } from "react-router-dom";

import { listPublicVacancies, type PublicVacancyListItemResponse } from "../api";
import { useSentryRouteTags } from "../app/observability/sentry";
import { CandidateApplyTrackingWorkspace } from "../components/candidate/CandidateApplyTrackingWorkspace";
import { PageHero } from "../components/PageHero";
import { formatDateLabel, normalizeInput } from "./careers/careersUtils";

const EMPTY_PUBLIC_VACANCIES: PublicVacancyListItemResponse[] = [];

/**
 * Public careers vacancy page for a single shareable role and the attached application flow.
 */
export function CareersVacancyPage() {
  const { t, i18n } = useTranslation();
  useSentryRouteTags("/careers");
  const { vacancyId } = useParams<{ vacancyId: string }>();
  const [searchParams] = useSearchParams();
  const routeVacancyId = normalizeInput(vacancyId) ?? normalizeInput(searchParams.get("vacancyId"));
  const queryVacancyTitle = normalizeInput(searchParams.get("vacancyTitle"));

  const vacanciesQuery = useQuery({
    queryKey: ["public-vacancies"],
    queryFn: listPublicVacancies,
    retry: false,
  });

  const openVacancies = vacanciesQuery.data?.items ?? EMPTY_PUBLIC_VACANCIES;
  const selectedVacancy = useMemo(
    () => (routeVacancyId ? openVacancies.find((vacancy) => vacancy.vacancy_id === routeVacancyId) : null),
    [openVacancies, routeVacancyId],
  );
  const selectedVacancyTitle = selectedVacancy?.title ?? queryVacancyTitle ?? null;
  const heroTitle = selectedVacancyTitle ?? t("careersPage.careersVacancyPage.fallbackTitle");
  const heroDescription = selectedVacancy?.description ?? t("careersPage.careersVacancyPage.subtitle");
  const heroChips = [
    selectedVacancy?.department,
    t("careersPage.careersVacancyPage.chips.open"),
    t("careersPage.careersVacancyPage.chips.shareable"),
  ].filter((value): value is string => Boolean(value));

  return (
    <Stack spacing={4}>
      <PageHero
        eyebrow={t("careersPage.careersVacancyPage.eyebrow")}
        title={heroTitle}
        description={heroDescription}
        imageSrc="/images/candidate-portal.jpg"
        imageAlt={t("careersPage.careersVacancyPage.imageAlt")}
        chips={heroChips}
        actions={[
          {
            href: "/careers",
            label: t("careersPage.careersVacancyPage.backAction"),
            variant: "outlined",
          },
        ]}
      />

      {vacanciesQuery.isLoading ? (
        <Alert severity="info">{t("careersPage.boardSection.loading")}</Alert>
      ) : null}
      {vacanciesQuery.isError ? (
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={() => void vacanciesQuery.refetch()}>
              {t("careersPage.boardSection.retry")}
            </Button>
          }
        >
          {t("careersPage.boardSection.error")}
        </Alert>
      ) : null}

      <Grid2 container spacing={2}>
        <Grid2 size={{ xs: 12, lg: 5 }}>
          <Paper
            sx={{
              p: 3,
              height: "100%",
              background:
                "linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(240,247,250,0.92) 100%)",
            }}
          >
            <Stack spacing={2}>
              <Stack spacing={0.75}>
                <Typography variant="h6">{t("careersPage.selectedRole.title")}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {selectedVacancy?.description ?? t("careersPage.careersVacancyPage.summaryFallback")}
                </Typography>
              </Stack>

              {selectedVacancy ? (
                <Stack spacing={1.5}>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    <Chip label={selectedVacancy.department} color="primary" variant="outlined" />
                    <Chip
                      label={t("careersPage.selectedRole.open")}
                      color="success"
                      variant="outlined"
                    />
                  </Stack>
                  <Stack spacing={0.5}>
                    <Typography variant="body2" color="text.secondary">
                      {t("careersPage.selectedRole.vacancyId")}: {selectedVacancy.vacancy_id}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {t("careersPage.selectedRole.updatedAt", {
                        value: formatDateLabel(selectedVacancy.updated_at, i18n.language),
                      })}
                    </Typography>
                  </Stack>
                </Stack>
              ) : (
                <Alert severity="warning">{t("careersPage.careersVacancyPage.notFound")}</Alert>
              )}
            </Stack>
          </Paper>
        </Grid2>

        <Grid2 size={{ xs: 12, lg: 7 }}>
          <Paper sx={{ p: 3, height: "100%" }}>
            <Stack spacing={2}>
              <CandidateApplyTrackingWorkspace
                queryVacancyId={routeVacancyId}
                queryVacancyTitle={selectedVacancyTitle}
                title={t("careersPage.applySection.workspaceTitle")}
                subtitle={
                  selectedVacancyTitle
                    ? t("careersPage.applySection.workspaceSubtitleSelected", {
                        vacancyTitle: selectedVacancyTitle,
                      })
                    : t("careersPage.applySection.workspaceSubtitle")
                }
              />
            </Stack>
          </Paper>
        </Grid2>
      </Grid2>
    </Stack>
  );
}
