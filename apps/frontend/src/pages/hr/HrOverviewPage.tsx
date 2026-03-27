import { Button, Chip, Grid2, Paper, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { OnboardingDashboardPanel } from "../../components/OnboardingDashboardPanel";
import { PageHero } from "../../components/PageHero";
import { HrWorkspaceNav } from "./HrWorkspaceNav";

/**
 * High-level entrypoint for the HR workspace route split.
 */
export function HrOverviewPage() {
  const { t } = useTranslation();

  const cards = [
    {
      title: t("hrWorkspacePages.cards.vacancies.title"),
      description: t("hrWorkspacePages.cards.vacancies.description"),
      to: "/hr/vacancies",
      cta: t("hrWorkspacePages.cards.vacancies.cta"),
      chips: [t("hrDashboard.createSectionTitle"), t("hrDashboard.editSectionTitle")],
    },
    {
      title: t("hrWorkspacePages.cards.pipeline.title"),
      description: t("hrWorkspacePages.cards.pipeline.description"),
      to: "/hr/pipeline",
      cta: t("hrWorkspacePages.cards.pipeline.cta"),
      chips: [t("hrDashboard.pipelineTitle"), t("hrDashboard.shortlist.title")],
    },
    {
      title: t("hrWorkspacePages.cards.interviews.title"),
      description: t("hrWorkspacePages.cards.interviews.description"),
      to: "/hr/interviews",
      cta: t("hrWorkspacePages.cards.interviews.cta"),
      chips: [t("hrDashboard.interviews.title"), t("hrDashboard.interviews.feedback.title")],
    },
    {
      title: t("hrWorkspacePages.cards.offers.title"),
      description: t("hrWorkspacePages.cards.offers.description"),
      to: "/hr/offers",
      cta: t("hrWorkspacePages.cards.offers.cta"),
      chips: [t("hrDashboard.offers.title"), t("hrDashboard.offers.hints.sent")],
    },
    {
      title: t("hrWorkspacePages.cards.referrals.title"),
      description: t("hrWorkspacePages.cards.referrals.description"),
      to: "/hr/referrals",
      cta: t("hrWorkspacePages.cards.referrals.cta"),
      chips: [t("referrals.title"), t("referrals.actions.shortlist")],
    },
  ];

  return (
    <Stack spacing={3}>
      <PageHero
        eyebrow={t("hrWorkspacePages.overview.title")}
        title={t("hrDashboard.title")}
        description={t("hrWorkspacePages.overview.subtitle")}
        imageSrc="/images/company-hero.jpg"
        imageAlt={t("hrDashboard.title")}
        chips={[
          t("hrDashboard.createSectionTitle"),
          t("hrDashboard.pipelineTitle"),
          t("hrDashboard.interviews.title"),
        ]}
      />

      <HrWorkspaceNav />

      <Paper sx={{ p: 2 }}>
        <Stack spacing={1.5}>
          <Typography variant="h6">{t("hrWorkspacePages.overview.storyTitle")}</Typography>
          <Typography variant="body2" color="text.secondary">
            {t("hrWorkspacePages.overview.storySubtitle")}
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip label={t("hrDashboard.shortlist.title")} />
            <Chip label={t("hrDashboard.interviews.title")} />
            <Chip label={t("hrDashboard.offers.title")} />
            <Chip label={t("hrWorkspaceNav.workbench")} />
          </Stack>
        </Stack>
      </Paper>

      <Grid2 container spacing={2}>
        {cards.map((card) => (
          <Grid2 key={card.to} size={{ xs: 12, md: 6 }}>
            <Paper sx={{ p: 2, height: "100%" }}>
              <Stack spacing={1.5} sx={{ height: "100%" }}>
                <Stack spacing={1}>
                  <Typography variant="h6">{card.title}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {card.description}
                  </Typography>
                </Stack>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  {card.chips.map((chip) => (
                    <Chip key={chip} size="small" label={chip} />
                  ))}
                </Stack>
                <Button component={RouterLink} to={card.to} variant="contained" sx={{ mt: "auto" }}>
                  {card.cta}
                </Button>
              </Stack>
            </Paper>
          </Grid2>
        ))}
      </Grid2>

      <Paper sx={{ p: 2 }}>
        <Stack spacing={1}>
          <Typography variant="h6">{t("hrWorkspacePages.overview.onboardingTitle")}</Typography>
          <Typography variant="body2" color="text.secondary">
            {t("hrWorkspacePages.overview.onboardingSubtitle")}
          </Typography>
        </Stack>
        <OnboardingDashboardPanel mode="embedded" />
      </Paper>
    </Stack>
  );
}
