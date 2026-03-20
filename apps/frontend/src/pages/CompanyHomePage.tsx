import { useTranslation } from "react-i18next";
import {
  Box,
  Button,
  Card,
  CardContent,
  Divider,
  Chip,
  Grid2,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import { readAuthSession, resolveWorkspaceRoute } from "../app/auth/session";
import { useSentryRouteTags } from "../app/observability/sentry";
import { PageHero } from "../components/PageHero";

const companyPillars = [
  {
    descriptionKey: "companyHome.pillars.recruiting.description",
    titleKey: "companyHome.pillars.recruiting.title",
  },
  {
    descriptionKey: "companyHome.pillars.onboarding.description",
    titleKey: "companyHome.pillars.onboarding.title",
  },
  {
    descriptionKey: "companyHome.pillars.reporting.description",
    titleKey: "companyHome.pillars.reporting.title",
  },
] as const;

const storyBullets = [
  "companyHome.story.bullets.public",
  "companyHome.story.bullets.private",
  "companyHome.story.bullets.locale",
] as const;

/**
 * Public company landing page with branded marketing sections and public/private entrypoints.
 *
 * Inputs:
 * - none; reads localized copy and the current authentication session from browser storage.
 *
 * Outputs:
 * - React element tree for the public company homepage, including the hero, marketing cards,
 *   story section, and calls to action.
 *
 * Side effects:
 * - tags the active Sentry route for `/`.
 */
export function CompanyHomePage() {
  const { t } = useTranslation();
  useSentryRouteTags("/");
  const session = readAuthSession();
  const workspacePath = resolveWorkspaceRoute(session.role);
  const workspaceActionLabel = session.accessToken
    ? t("companyHome.actions.workspace")
    : t("companyHome.actions.login");

  return (
    <Stack spacing={4}>
      <PageHero
        eyebrow={t("companyHome.eyebrow")}
        title={t("companyHome.title")}
        description={t("companyHome.subtitle")}
        caption={t("companyHome.caption")}
        chips={[
          t("companyHome.highlights.people"),
          t("companyHome.highlights.technology"),
          t("companyHome.highlights.reporting"),
        ]}
        imageSrc="/images/company-hero.jpg"
        imageAlt={t("companyHome.imageAlt")}
        actions={[
          {
            href: "/careers",
            label: t("companyHome.actions.careers"),
          },
          {
            href: session.accessToken ? workspacePath : "/login",
            label: workspaceActionLabel,
            variant: "outlined",
          },
        ]}
      />

      <Paper
        sx={{
          p: { xs: 2.5, md: 3 },
          background:
            "linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(247,241,234,0.92) 100%)",
        }}
      >
        <Stack spacing={2.5}>
          <Stack spacing={1}>
            <Typography variant="overline" sx={{ color: "secondary.main", fontWeight: 700 }}>
              {t("companyHome.pillars.eyebrow")}
            </Typography>
            <Typography variant="h4">{t("companyHome.pillars.title")}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 760 }}>
              {t("companyHome.pillars.subtitle")}
            </Typography>
          </Stack>

          <Grid2 container spacing={2}>
            {companyPillars.map((pillar, index) => (
              <Grid2 key={pillar.titleKey} size={{ xs: 12, md: 4 }}>
                <Card
                  sx={{
                    height: "100%",
                    border: "1px solid",
                    borderColor: "divider",
                    background:
                      "linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,244,238,0.92) 100%)",
                  }}
                >
                  <CardContent>
                    <Stack spacing={1.25}>
                      <Typography
                        variant="overline"
                        sx={{
                          color: "secondary.main",
                          fontWeight: 700,
                          letterSpacing: "0.2em",
                        }}
                      >
                        {String(index + 1).padStart(2, "0")}
                      </Typography>
                      <Typography variant="h5">{t(pillar.titleKey)}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {t(pillar.descriptionKey)}
                      </Typography>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid2>
            ))}
          </Grid2>
        </Stack>
      </Paper>

      <Paper
        sx={{
          p: { xs: 2.5, md: 3 },
          background:
            "linear-gradient(135deg, rgba(234, 223, 208, 0.5) 0%, rgba(255,255,255,0.98) 100%)",
        }}
      >
        <Grid2 container spacing={3} alignItems="center">
          <Grid2 size={{ xs: 12, lg: 6 }}>
            <Stack spacing={2.25}>
              <Typography variant="overline" sx={{ color: "secondary.main", fontWeight: 700 }}>
                {t("companyHome.story.eyebrow")}
              </Typography>
              <Typography variant="h4">{t("companyHome.story.title")}</Typography>
              <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 680 }}>
                {t("companyHome.story.subtitle")}
              </Typography>

              <Stack component="ul" spacing={1.25} sx={{ m: 0, pl: 2 }}>
                {storyBullets.map((bulletKey) => (
                  <Box component="li" key={bulletKey} sx={{ pl: 0.5 }}>
                    <Typography variant="body2">{t(bulletKey)}</Typography>
                  </Box>
                ))}
              </Stack>

              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
                <Button component={RouterLink} to="/careers" variant="contained">
                  {t("companyHome.actions.careers")}
                </Button>
                <Button
                  component={RouterLink}
                  to={session.accessToken ? workspacePath : "/login"}
                  variant="outlined"
                >
                  {workspaceActionLabel}
                </Button>
              </Stack>
            </Stack>
          </Grid2>

          <Grid2 size={{ xs: 12, lg: 6 }}>
            <Box
              component="img"
              src="/images/careers-team.jpg"
              alt={t("companyHome.story.imageAlt")}
              sx={{
                width: "100%",
                minHeight: { xs: 260, md: 360 },
                objectFit: "cover",
                borderRadius: 4,
                boxShadow: "0 28px 60px rgba(20, 36, 52, 0.18)",
              }}
            />

            <Paper
              sx={{
                mt: 2,
                p: 2.5,
                border: "1px solid",
                borderColor: "divider",
                background:
                  "linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,244,238,0.96) 100%)",
              }}
            >
              <Stack spacing={1.5}>
                <Typography variant="overline" sx={{ color: "secondary.main", fontWeight: 700 }}>
                  {t("companyHome.snapshot.eyebrow")}
                </Typography>
                <Typography variant="h6">{t("companyHome.snapshot.title")}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {t("companyHome.snapshot.subtitle")}
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  <Chip label={t("companyHome.snapshot.chips.public")} variant="outlined" />
                  <Chip label={t("companyHome.snapshot.chips.private")} variant="outlined" />
                  <Chip label={t("companyHome.snapshot.chips.locale")} variant="outlined" />
                </Stack>
              </Stack>
            </Paper>
          </Grid2>
        </Grid2>
      </Paper>

      <Paper
        component="footer"
        sx={{
          p: { xs: 2.5, md: 3 },
          border: "1px solid",
          borderColor: "rgba(11, 79, 108, 0.12)",
          background:
            "linear-gradient(135deg, rgba(11, 79, 108, 0.96) 0%, rgba(20, 36, 52, 0.99) 100%)",
          color: "common.white",
        }}
      >
        <Grid2 container spacing={3}>
          <Grid2 size={{ xs: 12, md: 6 }}>
            <Stack spacing={1.25}>
              <Typography variant="overline" sx={{ color: "secondary.light", fontWeight: 700 }}>
                {t("companyHome.footer.eyebrow")}
              </Typography>
              <Typography variant="h5">{t("companyHome.footer.title")}</Typography>
              <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.82)", maxWidth: 680 }}>
                {t("companyHome.footer.subtitle")}
              </Typography>
            </Stack>
          </Grid2>

          <Grid2 size={{ xs: 12, sm: 6, md: 3 }}>
            <Stack spacing={1.25}>
              <Typography variant="overline" sx={{ color: "secondary.light", fontWeight: 700 }}>
                {t("companyHome.footer.linksTitle")}
              </Typography>
              <Stack direction="column" spacing={0.5}>
                <Button
                  component={RouterLink}
                  to="/"
                  variant="text"
                  color="inherit"
                  sx={{ justifyContent: "flex-start", px: 0, width: "fit-content" }}
                >
                  {t("navigation.company")}
                </Button>
                <Button
                  component={RouterLink}
                  to="/careers"
                  variant="text"
                  color="inherit"
                  sx={{ justifyContent: "flex-start", px: 0, width: "fit-content" }}
                >
                  {t("companyHome.actions.careers")}
                </Button>
                <Button
                  component={RouterLink}
                  to={session.accessToken ? workspacePath : "/login"}
                  variant="text"
                  color="inherit"
                  sx={{ justifyContent: "flex-start", px: 0, width: "fit-content" }}
                >
                  {workspaceActionLabel}
                </Button>
              </Stack>
            </Stack>
          </Grid2>

          <Grid2 size={{ xs: 12, sm: 6, md: 3 }}>
            <Stack spacing={1.25}>
              <Typography variant="overline" sx={{ color: "secondary.light", fontWeight: 700 }}>
                {t("companyHome.footer.scopeTitle")}
              </Typography>
              <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.82)" }}>
                {t("companyHome.footer.scope")}
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                <Chip label={t("companyHome.highlights.people")} variant="outlined" sx={{ color: "common.white", borderColor: "rgba(255,255,255,0.32)" }} />
                <Chip label={t("companyHome.highlights.technology")} variant="outlined" sx={{ color: "common.white", borderColor: "rgba(255,255,255,0.32)" }} />
                <Chip label={t("companyHome.highlights.reporting")} variant="outlined" sx={{ color: "common.white", borderColor: "rgba(255,255,255,0.32)" }} />
              </Stack>
            </Stack>
          </Grid2>

          <Grid2 size={12}>
            <Divider sx={{ borderColor: "rgba(255,255,255,0.16)", my: 0.5 }} />
          </Grid2>

          <Grid2 size={{ xs: 12, md: 8 }}>
            <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.72)" }}>
              {t("companyHome.footer.note")}
            </Typography>
          </Grid2>

          <Grid2 size={{ xs: 12, md: 4 }}>
            <Stack direction={{ xs: "column", sm: "row" }} justifyContent={{ md: "flex-end" }} spacing={1}>
              <Button
                component={RouterLink}
                to="/careers"
                variant="contained"
                color="secondary"
              >
                {t("companyHome.actions.careers")}
              </Button>
              <Button
                component={RouterLink}
                to={session.accessToken ? workspacePath : "/login"}
                variant="outlined"
                sx={{
                  borderColor: "rgba(255,255,255,0.4)",
                  color: "common.white",
                  "&:hover": {
                    borderColor: "common.white",
                    backgroundColor: "rgba(255,255,255,0.08)",
                  },
                }}
              >
                {workspaceActionLabel}
              </Button>
            </Stack>
          </Grid2>
        </Grid2>
      </Paper>
    </Stack>
  );
}
