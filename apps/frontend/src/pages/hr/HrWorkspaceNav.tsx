import { Button, Stack } from "@mui/material";
import { Link as RouterLink, useInRouterContext, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

type HrWorkspaceRoute = {
  labelKey: string;
  to: string;
};

const WORKSPACE_ROUTES: HrWorkspaceRoute[] = [
  { labelKey: "hrWorkspaceNav.overview", to: "/hr" },
  { labelKey: "hrWorkspaceNav.vacancies", to: "/hr/vacancies" },
  { labelKey: "hrWorkspaceNav.pipeline", to: "/hr/pipeline" },
  { labelKey: "hrWorkspaceNav.interviews", to: "/hr/interviews" },
  { labelKey: "hrWorkspaceNav.offers", to: "/hr/offers" },
  { labelKey: "hrWorkspaceNav.referrals", to: "/hr/referrals" },
  { labelKey: "hrWorkspaceNav.workbench", to: "/hr/workbench" },
];

/**
 * Shared navigation for the HR workspace route split.
 */
export function HrWorkspaceNav() {
  const inRouter = useInRouterContext();

  if (!inRouter) {
    return <HrWorkspaceNavStatic />;
  }

  return <HrWorkspaceNavLinks />;
}

function HrWorkspaceNavStatic() {
  const { t } = useTranslation();

  return (
    <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" aria-label={t("hrWorkspaceNav.ariaLabel")}>
      {WORKSPACE_ROUTES.map((route) => (
        <Button key={route.to} variant="outlined" size="small">
          {t(route.labelKey)}
        </Button>
      ))}
    </Stack>
  );
}

function HrWorkspaceNavLinks() {
  const { t } = useTranslation();
  const location = useLocation();

  return (
    <Stack
      direction="row"
      spacing={1}
      useFlexGap
      flexWrap="wrap"
      aria-label={t("hrWorkspaceNav.ariaLabel")}
    >
      {WORKSPACE_ROUTES.map((route) => {
        const isActive = location.pathname === route.to;
        return (
          <Button
            key={route.to}
            component={RouterLink}
            to={route.to}
            variant={isActive ? "contained" : "outlined"}
            size="small"
            color={isActive ? "primary" : "inherit"}
          >
            {t(route.labelKey)}
          </Button>
        );
      })}
    </Stack>
  );
}
