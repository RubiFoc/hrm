import { Alert, Button, Stack, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import { readAuthSession, resolveWorkspaceRoute } from "../app/auth/session";

export function AccessDeniedPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const reason = searchParams.get("reason");
  const session = readAuthSession();
  const targetPath =
    session.accessToken && session.role ? resolveWorkspaceRoute(session.role) : "/login";

  return (
    <Stack spacing={2}>
      <Typography variant="h4">{t("accessDenied.title")}</Typography>
      <Alert severity="warning">
        {reason === "forbidden"
          ? t("accessDenied.forbidden")
          : t("accessDenied.unauthorized")}
      </Alert>
      <Button component={Link} to={targetPath} variant="contained">
        {t("backToWorkspace")}
      </Button>
    </Stack>
  );
}
