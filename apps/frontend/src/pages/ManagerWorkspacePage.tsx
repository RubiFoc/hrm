import { useEffect, useState } from "react";
import {
  Alert,
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
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import {
  ApiError,
  getManagerWorkspaceCandidateSnapshot,
  getManagerWorkspaceOverview,
  type ManagerWorkspaceCandidateSnapshotResponse,
  type ManagerWorkspaceOverviewResponse,
} from "../api";
import { readAuthSession } from "../app/auth/session";
import { useSentryRouteTags } from "../app/observability/sentry";
import { NotificationsPanel } from "../components/NotificationsPanel";
import { OnboardingDashboardPanel } from "../components/OnboardingDashboardPanel";

const EMPTY_OVERVIEW: ManagerWorkspaceOverviewResponse = {
  summary: {
    vacancy_count: 0,
    open_vacancy_count: 0,
    candidate_count: 0,
    active_interview_count: 0,
    upcoming_interview_count: 0,
  },
  items: [],
};

/**
 * Manager-facing workspace that combines hiring visibility with embedded onboarding progress.
 */
export function ManagerWorkspacePage() {
  const { t } = useTranslation();
  useSentryRouteTags("/");
  const session = readAuthSession();
  const accessToken = session.accessToken;
  const [selectedVacancyId, setSelectedVacancyId] = useState<string | null>(null);

  const overviewQuery = useQuery({
    queryKey: ["manager-workspace-overview", accessToken],
    queryFn: () => getManagerWorkspaceOverview(accessToken!),
    enabled: Boolean(accessToken),
    retry: false,
  });

  const overview = overviewQuery.data ?? EMPTY_OVERVIEW;
  const vacancyItems = overview.items;

  useEffect(() => {
    if (vacancyItems.length === 0) {
      if (selectedVacancyId !== null) {
        setSelectedVacancyId(null);
      }
      return;
    }
    if (!selectedVacancyId || !vacancyItems.some((item) => item.vacancy_id === selectedVacancyId)) {
      setSelectedVacancyId(vacancyItems[0].vacancy_id);
    }
  }, [selectedVacancyId, vacancyItems]);

  const snapshotQuery = useQuery({
    queryKey: ["manager-workspace-snapshot", accessToken, selectedVacancyId],
    queryFn: () => getManagerWorkspaceCandidateSnapshot(accessToken!, selectedVacancyId!),
    enabled: Boolean(accessToken && selectedVacancyId),
    retry: false,
  });

  if (!accessToken) {
    return <Alert severity="warning">{t("managerDashboard.authRequired")}</Alert>;
  }

  return (
    <Stack spacing={3}>
      <Stack spacing={1}>
        <Typography variant="h4">{t("managerWorkspace")}</Typography>
        <Typography variant="body2" color="text.secondary">
          {t("managerDashboard.subtitle")}
        </Typography>
      </Stack>

      <NotificationsPanel accessToken={accessToken} workspace="manager" />

      <Stack direction={{ xs: "column", md: "row" }} spacing={1} flexWrap="wrap" useFlexGap>
        <Chip
          label={t("managerDashboard.summary.vacancies", {
            value: overview.summary.vacancy_count,
          })}
          color="primary"
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.summary.openVacancies", {
            value: overview.summary.open_vacancy_count,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.summary.candidates", {
            value: overview.summary.candidate_count,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.summary.activeInterviews", {
            value: overview.summary.active_interview_count,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.summary.upcomingInterviews", {
            value: overview.summary.upcoming_interview_count,
          })}
          variant="outlined"
        />
      </Stack>

      {overviewQuery.isLoading ? (
        <Stack spacing={2} alignItems="center" sx={{ py: 4 }}>
          <CircularProgress size={28} />
          <Typography variant="body2">{t("managerDashboard.loading")}</Typography>
        </Stack>
      ) : null}

      {overviewQuery.isError ? (
        <Alert severity="error">{resolveManagerWorkspaceError(overviewQuery.error, t)}</Alert>
      ) : null}

      {overviewQuery.isLoading || overviewQuery.isError ? null : (
        <Grid2 container spacing={2}>
          <Grid2 size={{ xs: 12, lg: 5 }}>
            <Paper sx={{ overflowX: "auto" }}>
              <Stack spacing={1} sx={{ p: 3, pb: vacancyItems.length === 0 ? 3 : 1 }}>
                <Typography variant="h6">{t("managerDashboard.vacancies.title")}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {t("managerDashboard.vacancies.subtitle")}
                </Typography>
              </Stack>
              {vacancyItems.length === 0 ? (
                <Alert severity="info" sx={{ borderRadius: 0 }}>
                  {t("managerDashboard.empty")}
                </Alert>
              ) : (
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>{t("managerDashboard.vacancies.table.title")}</TableCell>
                      <TableCell>{t("managerDashboard.vacancies.table.counts")}</TableCell>
                      <TableCell>{t("managerDashboard.vacancies.table.activity")}</TableCell>
                      <TableCell align="right">
                        {t("managerDashboard.vacancies.table.actions")}
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {vacancyItems.map((vacancy) => (
                      <TableRow
                        key={vacancy.vacancy_id}
                        hover
                        selected={vacancy.vacancy_id === selectedVacancyId}
                      >
                        <TableCell>
                          <Stack spacing={0.5}>
                            <Typography variant="body2" fontWeight={600}>
                              {vacancy.title}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {t("managerDashboard.vacancies.meta", {
                                department: vacancy.department,
                                status: vacancy.status,
                              })}
                            </Typography>
                          </Stack>
                        </TableCell>
                        <TableCell>
                          <Stack spacing={0.5}>
                            <Typography variant="body2">
                              {t("managerDashboard.vacancies.counts.candidates", {
                                value: vacancy.candidate_count,
                              })}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {t("managerDashboard.vacancies.counts.interviews", {
                                value: vacancy.active_interview_count,
                              })}
                            </Typography>
                          </Stack>
                        </TableCell>
                        <TableCell>{formatDateTimeValue(vacancy.latest_activity_at)}</TableCell>
                        <TableCell align="right">
                          <Button size="small" onClick={() => setSelectedVacancyId(vacancy.vacancy_id)}>
                            {t("managerDashboard.vacancies.actions.view")}
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </Paper>
          </Grid2>

          <Grid2 size={{ xs: 12, lg: 7 }}>
            <Paper sx={{ p: 3, minHeight: 320 }}>
              {selectedVacancyId === null ? (
                <Alert severity="info">{t("managerDashboard.snapshot.selectVacancy")}</Alert>
              ) : snapshotQuery.isLoading ? (
                <Stack spacing={2} alignItems="center" sx={{ py: 4 }}>
                  <CircularProgress size={24} />
                  <Typography variant="body2">{t("managerDashboard.snapshot.loading")}</Typography>
                </Stack>
              ) : snapshotQuery.isError ? (
                <Alert severity="error">{resolveManagerWorkspaceError(snapshotQuery.error, t)}</Alert>
              ) : snapshotQuery.data ? (
                <CandidateSnapshot snapshot={snapshotQuery.data} />
              ) : null}
            </Paper>
          </Grid2>
        </Grid2>
      )}

      <OnboardingDashboardPanel mode="embedded" />
    </Stack>
  );
}

type CandidateSnapshotProps = {
  snapshot: ManagerWorkspaceCandidateSnapshotResponse;
};

function CandidateSnapshot({ snapshot }: CandidateSnapshotProps) {
  const { t } = useTranslation();

  return (
    <Stack spacing={2}>
      <Stack spacing={0.5}>
        <Typography variant="h6">{snapshot.vacancy.title}</Typography>
        <Typography variant="body2" color="text.secondary">
          {t("managerDashboard.snapshot.subtitle", {
            department: snapshot.vacancy.department,
            status: snapshot.vacancy.status,
          })}
        </Typography>
      </Stack>

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip
          label={t("managerDashboard.snapshot.summary.candidates", {
            value: snapshot.summary.candidate_count,
          })}
          color="primary"
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.snapshot.summary.activeInterviews", {
            value: snapshot.summary.active_interview_count,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.snapshot.summary.upcomingInterviews", {
            value: snapshot.summary.upcoming_interview_count,
          })}
          variant="outlined"
        />
      </Stack>

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Chip
          label={t("managerDashboard.snapshot.stageCounts.applied", {
            value: snapshot.summary.stage_counts.applied,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.snapshot.stageCounts.screening", {
            value: snapshot.summary.stage_counts.screening,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.snapshot.stageCounts.shortlist", {
            value: snapshot.summary.stage_counts.shortlist,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.snapshot.stageCounts.interview", {
            value: snapshot.summary.stage_counts.interview,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.snapshot.stageCounts.offer", {
            value: snapshot.summary.stage_counts.offer,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.snapshot.stageCounts.hired", {
            value: snapshot.summary.stage_counts.hired,
          })}
          variant="outlined"
        />
        <Chip
          label={t("managerDashboard.snapshot.stageCounts.rejected", {
            value: snapshot.summary.stage_counts.rejected,
          })}
          variant="outlined"
        />
      </Stack>

      {snapshot.items.length === 0 ? (
        <Alert severity="info">{t("managerDashboard.snapshot.empty")}</Alert>
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>{t("managerDashboard.snapshot.table.candidate")}</TableCell>
              <TableCell>{t("managerDashboard.snapshot.table.stage")}</TableCell>
              <TableCell>{t("managerDashboard.snapshot.table.analysis")}</TableCell>
              <TableCell>{t("managerDashboard.snapshot.table.interview")}</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {snapshot.items.map((item) => (
              <TableRow key={item.candidate_id}>
                <TableCell>
                  <Stack spacing={0.5}>
                    <Typography variant="body2" fontWeight={600}>
                      {item.first_name} {item.last_name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {item.email}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {t("managerDashboard.snapshot.candidateMeta", {
                        title: item.current_title || t("managerDashboard.noValue"),
                        location: item.location || t("managerDashboard.noValue"),
                        years: formatYearsExperience(item.years_experience, t),
                      })}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {t("managerDashboard.snapshot.skills", {
                        value: item.skills.length > 0
                          ? item.skills.join(", ")
                          : t("managerDashboard.noValue"),
                      })}
                    </Typography>
                  </Stack>
                </TableCell>
                <TableCell>
                  <Stack spacing={0.5}>
                    <Chip
                      size="small"
                      label={t(`hrDashboard.stages.${item.stage}`)}
                      color={resolveStageChipColor(item.stage)}
                    />
                    <Typography variant="caption" color="text.secondary">
                      {formatDateTimeValue(item.stage_updated_at)}
                    </Typography>
                  </Stack>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {item.analysis_ready
                      ? t("managerDashboard.snapshot.analysisReady")
                      : t("managerDashboard.snapshot.analysisPending")}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {formatInterviewSummary(item, t)}
                  </Typography>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Stack>
  );
}

function resolveManagerWorkspaceError(
  error: unknown,
  t: ReturnType<typeof useTranslation>["t"],
) {
  if (error instanceof ApiError) {
    if (error.detail === "manager_workspace_vacancy_not_found") {
      return t("managerDashboard.errors.vacancyNotFound");
    }
    return t(`managerDashboard.errors.${error.detail}`, {
      defaultValue: t(`managerDashboard.errors.http_${error.status}`, {
        defaultValue: t("managerDashboard.errors.generic"),
      }),
    });
  }
  return t("managerDashboard.errors.generic");
}

function resolveStageChipColor(stage: ManagerWorkspaceCandidateSnapshotResponse["items"][number]["stage"]) {
  if (stage === "hired") {
    return "success" as const;
  }
  if (stage === "offer" || stage === "interview") {
    return "warning" as const;
  }
  return "default" as const;
}

function formatInterviewSummary(
  item: ManagerWorkspaceCandidateSnapshotResponse["items"][number],
  t: ReturnType<typeof useTranslation>["t"],
) {
  if (!item.interview_status || !item.interview_scheduled_start_at) {
    return t("managerDashboard.snapshot.noInterview");
  }
  return t("managerDashboard.snapshot.interviewValue", {
    status: t(`candidateInterview.status.${item.interview_status}`),
    value: formatDateTimeValue(item.interview_scheduled_start_at),
  });
}

function formatDateTimeValue(value: string | null) {
  if (!value) {
    return "n/a";
  }
  return new Date(value).toLocaleString();
}

function formatYearsExperience(
  value: number | null,
  t: ReturnType<typeof useTranslation>["t"],
) {
  if (value === null) {
    return t("managerDashboard.noValue");
  }
  return t("managerDashboard.snapshot.yearsExperience", { value });
}
