import { Card, CardActions, CardContent, Grid2, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

type AdminCardConfig = {
  key: string;
  to: string;
};

const adminCards: AdminCardConfig[] = [
  { key: "candidates", to: "/admin/candidates" },
  { key: "vacancies", to: "/admin/vacancies" },
  { key: "pipeline", to: "/admin/pipeline" },
  { key: "audit", to: "/admin/audit" },
  { key: "observability", to: "/admin/observability" },
  { key: "staff", to: "/admin/staff" },
  { key: "employeeKeys", to: "/admin/employee-keys" },
];

/**
 * Admin landing page with navigation cards for privileged control-plane consoles.
 *
 * Inputs:
 * - none; reads localized labels from the active translation catalog.
 *
 * Outputs:
 * - React element tree containing the admin shell cards and links.
 *
 * Side effects:
 * - none.
 */
export function AdminShellPage() {
  const { t } = useTranslation();

  return (
    <Grid2 container spacing={2}>
      <Grid2 size={12}>
        <Typography variant="h4">{t("adminWorkspace")}</Typography>
        <Typography variant="body2">{t("adminWorkspaceSubtitle")}</Typography>
      </Grid2>
      {adminCards.map((item) => (
        <Grid2 size={{ xs: 12, sm: 6, md: 4 }} key={item.key}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="h6">{t(`adminCard.${item.key}.title`)}</Typography>
              <Typography variant="body2">{t(`adminCard.${item.key}.description`)}</Typography>
            </CardContent>
            <CardActions>
              <Typography
                component={Link}
                to={item.to}
                sx={{ textDecoration: "none", fontWeight: 600, color: "primary.main" }}
              >
                {t("adminCard.open")}
              </Typography>
            </CardActions>
          </Card>
        </Grid2>
      ))}
    </Grid2>
  );
}
