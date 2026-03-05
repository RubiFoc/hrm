import { Card, CardActions, CardContent, Grid2, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import type { ApiPath } from "../api";
import { typedApiClient } from "../api";

const adminCards = [
  {
    key: "staff",
    to: "/admin/staff",
  },
  {
    key: "employeeKeys",
    to: "/admin/employee-keys",
  },
  {
    key: "audit",
    to: null,
  },
  {
    key: "settings",
    to: null,
  },
] as const;

const adminContractPath: ApiPath = "/api/v1/admin/employee-keys";
void typedApiClient;
void adminContractPath;

export function AdminShellPage() {
  const { t } = useTranslation();

  return (
    <Grid2 container spacing={2}>
      <Grid2 size={12}>
        <Typography variant="h4">{t("adminWorkspace")}</Typography>
        <Typography variant="body2">{t("adminWorkspaceSubtitle")}</Typography>
      </Grid2>
      {adminCards.map((item) => (
        <Grid2 size={{ xs: 12, sm: 4 }} key={item.key}>
          <Card>
            <CardContent>
              <Typography variant="h6">{t(`adminCard.${item.key}.title`)}</Typography>
              <Typography variant="body2">{t(`adminCard.${item.key}.description`)}</Typography>
            </CardContent>
            {item.to ? (
              <CardActions>
                <Typography
                  component={Link}
                  to={item.to}
                  sx={{ textDecoration: "none", fontWeight: 600, color: "primary.main" }}
                >
                  {t("adminCard.open")}
                </Typography>
              </CardActions>
            ) : null}
          </Card>
        </Grid2>
      ))}
    </Grid2>
  );
}
