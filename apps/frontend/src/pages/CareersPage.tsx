import { useMemo, useState } from "react";
import {
  Alert,
  Button,
  Chip,
  Grid2,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, Navigate, useSearchParams } from "react-router-dom";

import { listPublicVacancies, type PublicVacancyListItemResponse } from "../api";
import { useSentryRouteTags } from "../app/observability/sentry";
import { PageHero } from "../components/PageHero";
import { PublicRailCard } from "../components/public/PublicRailCard";
import {
  buildVacancyDetailPath,
  formatDateLabel,
  normalizeInput,
} from "./careers/careersUtils";

const EMPTY_PUBLIC_VACANCIES: PublicVacancyListItemResponse[] = [];

/**
 * Public careers board with searchable open roles and a link to each vacancy page.
 */
export function CareersPage() {
  const { t, i18n } = useTranslation();
  useSentryRouteTags("/careers");
  const [searchParams] = useSearchParams();
  const queryVacancyId = normalizeInput(searchParams.get("vacancyId"));
  const queryVacancyTitle = normalizeInput(searchParams.get("vacancyTitle"));
  const [searchTerm, setSearchTerm] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("");
  const vacanciesQuery = useQuery({
    queryKey: ["public-vacancies"],
    queryFn: listPublicVacancies,
    retry: false,
    enabled: !queryVacancyId,
  });

  const openVacancies = vacanciesQuery.data?.items ?? EMPTY_PUBLIC_VACANCIES;
  const departmentOptions = useMemo(
    () =>
      Array.from(
        new Set(
          openVacancies
            .map((vacancy) => vacancy.department)
            .filter((department): department is string => Boolean(department)),
        ),
      ).sort((left, right) => left.localeCompare(right, i18n.language)),
    [i18n.language, openVacancies],
  );
  const filteredVacancies = useMemo(() => {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    return openVacancies.filter((vacancy) => {
      if (departmentFilter && vacancy.department !== departmentFilter) {
        return false;
      }
      if (!normalizedSearch) {
        return true;
      }
      return [vacancy.title, vacancy.department, vacancy.description].some((value) =>
        value.toLowerCase().includes(normalizedSearch),
      );
    });
  }, [departmentFilter, openVacancies, searchTerm]);

  if (queryVacancyId) {
    return <Navigate replace to={buildVacancyDetailPath(queryVacancyId, queryVacancyTitle)} />;
  }

  return (
    <Stack spacing={4}>
      <PageHero
        eyebrow={t("careersPage.eyebrow")}
        title={t("careersPage.title")}
        description={t("careersPage.subtitle")}
        imageSrc="/images/careers-team.jpg"
        imageAlt={t("careersPage.imageAlt")}
        chips={[
          t("careersPage.highlights.board"),
          t("careersPage.highlights.cvUpload"),
          t("careersPage.highlights.ruEn"),
        ]}
        caption={t("careersPage.caption")}
      />

      <Grid2 container spacing={2}>
        <Grid2 size={{ xs: 12, lg: 8 }}>
          <Paper
            sx={{
              p: { xs: 2.5, md: 3 },
              height: "100%",
              background:
                "linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(247,241,234,0.92) 100%)",
            }}
          >
            <Stack spacing={2.5}>
              <Stack spacing={1}>
                <Typography variant="h4">{t("careersPage.boardSection.title")}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {t("careersPage.boardSection.subtitle")}
                </Typography>
              </Stack>

              <Stack spacing={1.5} direction={{ xs: "column", md: "row" }}>
                <TextField
                  fullWidth
                  label={t("careersPage.boardSection.searchLabel")}
                  placeholder={t("careersPage.boardSection.searchPlaceholder")}
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                />
                <TextField
                  select
                  fullWidth
                  label={t("careersPage.boardSection.departmentLabel")}
                  value={departmentFilter}
                  onChange={(event) => setDepartmentFilter(event.target.value)}
                >
                  <MenuItem value="">{t("careersPage.boardSection.allDepartments")}</MenuItem>
                  {departmentOptions.map((department) => (
                    <MenuItem key={department} value={department}>
                      {department}
                    </MenuItem>
                  ))}
                </TextField>
              </Stack>

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

              {!vacanciesQuery.isLoading && !vacanciesQuery.isError ? (
                filteredVacancies.length > 0 ? (
                  <Grid2 container spacing={2}>
                    {filteredVacancies.map((vacancy) => (
                      <Grid2 key={vacancy.vacancy_id} size={{ xs: 12, md: 6 }}>
                        <Paper
                          sx={{
                            p: 2.5,
                            height: "100%",
                            border: "1px solid",
                            borderColor: "divider",
                            background:
                              "linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,244,238,0.92) 100%)",
                          }}
                        >
                          <Stack spacing={1.5}>
                            <Stack
                              direction="row"
                              justifyContent="space-between"
                              alignItems="flex-start"
                              spacing={1}
                            >
                              <Chip label={vacancy.department} variant="outlined" size="small" />
                              <Chip
                                label={t("careersPage.boardSection.openBadge")}
                                color="success"
                                size="small"
                                variant="outlined"
                              />
                            </Stack>

                            <Stack spacing={0.75}>
                              <Typography variant="h6">{vacancy.title}</Typography>
                              <Typography variant="body2" color="text.secondary">
                                {vacancy.description}
                              </Typography>
                            </Stack>

                            <Stack
                              direction="row"
                              justifyContent="space-between"
                              alignItems="center"
                              spacing={1}
                            >
                              <Typography variant="caption" color="text.secondary">
                                {t("careersPage.boardSection.updatedAt", {
                                  value: formatDateLabel(vacancy.updated_at, i18n.language),
                                })}
                              </Typography>
                              <Button
                                component={RouterLink}
                                to={buildVacancyDetailPath(vacancy.vacancy_id, vacancy.title)}
                                variant="contained"
                                size="small"
                              >
                                {t("careersPage.boardSection.openAction")}
                              </Button>
                            </Stack>
                          </Stack>
                        </Paper>
                      </Grid2>
                    ))}
                  </Grid2>
                ) : (
                  <Alert severity="info">{t("careersPage.boardSection.empty")}</Alert>
                )
              ) : null}
            </Stack>
          </Paper>
        </Grid2>

        <Grid2 size={{ xs: 12, lg: 4 }}>
          <PublicRailCard
            eyebrow={t("careersPage.heroCard.eyebrow")}
            title={t("careersPage.heroCard.title")}
            subtitle={t("careersPage.heroCard.subtitle")}
            chips={[
              t("careersPage.boardSection.count", { count: openVacancies.length }),
              t("careersPage.highlights.ruEn"),
              t("careersPage.highlights.cvUpload"),
            ]}
            items={[
              {
                title: t("careersPage.heroCard.steps.browse.title"),
                description: t("careersPage.heroCard.steps.browse.description"),
              },
              {
                title: t("careersPage.heroCard.steps.select.title"),
                description: t("careersPage.heroCard.steps.select.description"),
              },
              {
                title: t("careersPage.heroCard.steps.upload.title"),
                description: t("careersPage.heroCard.steps.upload.description"),
              },
            ]}
            footnote={t("careersPage.heroCard.note")}
          />
        </Grid2>
      </Grid2>
    </Stack>
  );
}
