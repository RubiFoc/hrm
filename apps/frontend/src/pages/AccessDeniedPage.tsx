import { Alert, Button, Stack, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

export function AccessDeniedPage() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const reason = searchParams.get("reason");

  return (
    <Stack spacing={2}>
      <Typography variant="h4">{t("adminAccessDeniedTitle")}</Typography>
      <Alert severity="warning">
        {reason === "forbidden"
          ? t("adminAccessForbiddenDescription")
          : t("adminAccessUnauthorizedDescription")}
      </Alert>
      <Button component={Link} to="/" variant="contained">
        {t("backToWorkspace")}
      </Button>
    </Stack>
  );
}
