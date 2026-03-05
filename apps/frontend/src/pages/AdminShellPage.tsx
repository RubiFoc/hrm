import { Card, CardContent, Grid2, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

import type { ApiPath } from "../api";
import { typedApiClient } from "../api";

const adminCards = ["users", "audit", "settings"] as const;

const adminContractPath: ApiPath = "/api/v1/admin/staff";
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
        <Grid2 size={{ xs: 12, sm: 4 }} key={item}>
          <Card>
            <CardContent>
              <Typography variant="h6">{t(`adminCard.${item}.title`)}</Typography>
              <Typography variant="body2">{t(`adminCard.${item}.description`)}</Typography>
            </CardContent>
          </Card>
        </Grid2>
      ))}
    </Grid2>
  );
}
