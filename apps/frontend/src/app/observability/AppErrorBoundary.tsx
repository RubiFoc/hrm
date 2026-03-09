import type { PropsWithChildren } from "react";
import { Alert, Button, Paper, Stack, Typography } from "@mui/material";
import * as Sentry from "@sentry/react";
import { useTranslation } from "react-i18next";

import { applySentryRouteTagsToScope } from "./sentry";

/**
 * Global React render-failure boundary for the frontend application shell.
 *
 * Inputs:
 * - `children`: application subtree to protect.
 *
 * Outputs:
 * - wrapped children or a localized fallback UI after a render failure.
 *
 * Side effects:
 * - captures render exceptions in Sentry with current route/workspace/role tags.
 */
export function AppErrorBoundary({ children }: PropsWithChildren) {
  return (
    <Sentry.ErrorBoundary
      beforeCapture={(scope) => {
        applySentryRouteTagsToScope(scope, window.location.pathname);
        scope.setExtra("render_pathname", window.location.pathname);
      }}
      fallback={({ resetError }) => <AppErrorFallback onRetry={resetError} />}
    >
      {children}
    </Sentry.ErrorBoundary>
  );
}

type AppErrorFallbackProps = {
  onRetry: () => void;
};

function AppErrorFallback({ onRetry }: AppErrorFallbackProps) {
  const { t } = useTranslation();

  return (
    <Stack alignItems="center" sx={{ py: 6 }}>
      <Paper sx={{ maxWidth: 520, p: 3, width: "100%" }}>
        <Stack spacing={2}>
          <Typography variant="h5">{t("appErrorBoundary.title")}</Typography>
          <Alert severity="error">{t("appErrorBoundary.message")}</Alert>
          <Button variant="contained" onClick={onRetry}>
            {t("appErrorBoundary.retry")}
          </Button>
        </Stack>
      </Paper>
    </Stack>
  );
}
