import {
  Button,
  Chip,
  Grid2,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";

import { readAuthSession, resolveWorkspaceRoute } from "../app/auth/session";
import { useSentryRouteTags } from "../app/observability/sentry";
import { PageHero } from "../components/PageHero";
import { PublicRailCard } from "../components/public/PublicRailCard";

/**
 * Public company landing page with the refreshed visual identity and careers entrypoint.
 */
export function CompanyHomePage() {
  const { t } = useTranslation();
  useSentryRouteTags("/");
  const session = readAuthSession();
  const workspacePath = resolveWorkspaceRoute(session.role);

  const highlights = [
    t("companyHome.highlights.hiring"),
    t("companyHome.highlights.transparency"),
    t("companyHome.highlights.localization"),
  ];
  const metrics = [
    {
      label: t("companyHome.metrics.recruitment.label"),
      value: t("companyHome.metrics.recruitment.value"),
    },
    {
      label: t("companyHome.metrics.roles.label"),
      value: t("companyHome.metrics.roles.value"),
    },
    {
      label: t("companyHome.metrics.experience.label"),
      value: t("companyHome.metrics.experience.value"),
    },
  ];
  const pillars = [
    {
      title: t("companyHome.pillars.hiring.title"),
      description: t("companyHome.pillars.hiring.description"),
    },
    {
      title: t("companyHome.pillars.teams.title"),
      description: t("companyHome.pillars.teams.description"),
    },
    {
      title: t("companyHome.pillars.operations.title"),
      description: t("companyHome.pillars.operations.description"),
    },
  ];
  const roles = [
    {
      description: t("companyHome.roles.hr.description"),
      title: t("companyHome.roles.hr.title"),
    },
    {
      description: t("companyHome.roles.manager.description"),
      title: t("companyHome.roles.manager.title"),
    },
    {
      description: t("companyHome.roles.employee.description"),
      title: t("companyHome.roles.employee.title"),
    },
    {
      description: t("companyHome.roles.leader.description"),
      title: t("companyHome.roles.leader.title"),
    },
    {
      description: t("companyHome.roles.accountant.description"),
      title: t("companyHome.roles.accountant.title"),
    },
  ];

  return (
    <Stack spacing={4}>
      <PageHero
        eyebrow={t("companyHome.eyebrow")}
        title={t("companyHome.title")}
        description={t("companyHome.subtitle")}
        imageSrc="/images/company-hero.jpg"
        imageAlt={t("companyHome.imageAlt")}
        chips={highlights}
        sideContent={
          <PublicRailCard
            eyebrow={t("companyHome.portalRail.eyebrow")}
            title={t("companyHome.portalRail.title")}
            subtitle={t("companyHome.portalRail.subtitle")}
            chips={highlights}
            items={[
              {
                title: t("companyHome.portalRail.items.careers.title"),
                description: t("companyHome.portalRail.items.careers.description"),
              },
              {
                title: t("companyHome.portalRail.items.workspace.title"),
                description: t("companyHome.portalRail.items.workspace.description"),
              },
              {
                title: t("companyHome.portalRail.items.language.title"),
                description: t("companyHome.portalRail.items.language.description"),
              },
            ]}
          />
        }
        actions={[
          {
            href: "/careers",
            label: t("companyHome.actions.careers"),
          },
          {
            href: session.accessToken ? workspacePath : "/login",
            label: session.accessToken
              ? t("companyHome.actions.workspace")
              : t("companyHome.actions.login"),
            variant: "outlined",
          },
        ]}
        caption={t("companyHome.caption")}
      />

      <Grid2 container spacing={2}>
        {metrics.map((metric) => (
          <Grid2 key={metric.label} size={{ xs: 12, md: 4 }}>
            <Paper sx={{ p: 3, height: "100%" }}>
              <Stack spacing={1}>
                <Typography variant="h4">{metric.value}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {metric.label}
                </Typography>
              </Stack>
            </Paper>
          </Grid2>
        ))}
      </Grid2>

      <Grid2 container spacing={2}>
        {pillars.map((pillar) => (
          <Grid2 key={pillar.title} size={{ xs: 12, md: 4 }}>
            <Paper sx={{ p: 3, height: "100%" }}>
              <Stack spacing={1.5}>
                <Typography variant="h6">{pillar.title}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {pillar.description}
                </Typography>
              </Stack>
            </Paper>
          </Grid2>
        ))}
      </Grid2>

      <Paper sx={{ p: 3.5 }}>
        <Stack spacing={2.5}>
          <Stack spacing={1}>
            <Typography variant="h4">{t("companyHome.rolesSection.title")}</Typography>
            <Typography variant="body2" color="text.secondary">
              {t("companyHome.rolesSection.subtitle")}
            </Typography>
          </Stack>

          <Grid2 container spacing={2}>
            {roles.map((role) => (
              <Grid2 key={role.title} size={{ xs: 12, md: 6, lg: 4 }}>
                <Paper
                  sx={{
                    p: 2.5,
                    height: "100%",
                    background:
                      "linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(240,247,250,0.88) 100%)",
                  }}
                >
                  <Stack spacing={1.5}>
                    <Chip label={role.title} color="primary" variant="outlined" sx={{ alignSelf: "flex-start" }} />
                    <Typography variant="body2" color="text.secondary">
                      {role.description}
                    </Typography>
                  </Stack>
                </Paper>
              </Grid2>
            ))}
          </Grid2>
        </Stack>
      </Paper>

      <Paper
        sx={{
          p: { xs: 3, md: 4 },
          background:
            "linear-gradient(135deg, rgba(11,79,108,0.95) 0%, rgba(31,100,88,0.94) 100%)",
          color: "primary.contrastText",
        }}
      >
        <Grid2 container spacing={3} alignItems="center">
          <Grid2 size={{ xs: 12, md: 8 }}>
            <Stack spacing={1.5}>
              <Typography variant="h4" color="inherit">
                {t("companyHome.careersBanner.title")}
              </Typography>
              <Typography variant="body1" sx={{ color: "rgba(247, 242, 234, 0.82)" }}>
                {t("companyHome.careersBanner.description")}
              </Typography>
            </Stack>
          </Grid2>
          <Grid2 size={{ xs: 12, md: 4 }}>
            <Stack direction={{ xs: "column", sm: "row", md: "column" }} spacing={1.5}>
              <Button component={RouterLink} to="/careers" variant="contained" color="secondary">
                {t("companyHome.careersBanner.primaryAction")}
              </Button>
              <Button
                component={RouterLink}
                to={session.accessToken ? workspacePath : "/login"}
                variant="outlined"
                sx={{
                  color: "primary.contrastText",
                  borderColor: "rgba(247, 242, 234, 0.4)",
                }}
              >
                {session.accessToken
                  ? t("companyHome.careersBanner.secondaryActionWorkspace")
                  : t("companyHome.careersBanner.secondaryActionLogin")}
              </Button>
            </Stack>
          </Grid2>
        </Grid2>
      </Paper>
    </Stack>
  );
}
