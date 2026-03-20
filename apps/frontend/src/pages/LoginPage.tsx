import { useEffect, useState } from "react";
import { Alert, Box, Button, CircularProgress, Paper, Stack, TextField, Typography } from "@mui/material";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { ApiError, getMe, login } from "../api";
import {
  clearAuthSession,
  readAuthSession,
  resolveAuthRole,
  resolveWorkspaceRoute,
  writeAuthSession,
} from "../app/auth/session";
import { useSentryRouteTags } from "../app/observability/sentry";
import { PageHero } from "../components/PageHero";

const loginSchema = z.object({
  identifier: z.string().trim().min(1),
  password: z.string().min(1),
});

type LoginFormValues = z.infer<typeof loginSchema>;

/**
 * Staff login screen that boots session, persists token pair, and redirects by role.
 */
export function LoginPage() {
  const { t } = useTranslation();
  useSentryRouteTags("/login");
  const navigate = useNavigate();
  const [requestError, setRequestError] = useState<string | null>(null);
  const [isBootstrapPending, setIsBootstrapPending] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      identifier: "",
      password: "",
    },
  });

  useEffect(() => {
    let cancelled = false;
    const session = readAuthSession();
    if (!session.accessToken) {
      return () => {
        cancelled = true;
      };
    }
    const accessToken = session.accessToken;

    setIsBootstrapPending(true);
    void getMe(accessToken)
      .then((identity) => {
        if (cancelled) {
          return;
        }
        const role = resolveAuthRole(identity.role);
        if (!role) {
          clearAuthSession();
          navigate("/access-denied?reason=forbidden", { replace: true });
          return;
        }

        writeAuthSession({
          accessToken,
          refreshToken: session.refreshToken,
          role,
        });
        navigate(resolveWorkspaceRoute(role), { replace: true });
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        clearAuthSession();
        setIsBootstrapPending(false);
      });

    return () => {
      cancelled = true;
    };
  }, [navigate]);

  const onSubmit = async (values: LoginFormValues) => {
    setRequestError(null);
    try {
      const tokenPair = await login(values);
      const identity = await getMe(tokenPair.access_token);
      const role = resolveAuthRole(identity.role);
      if (!role) {
        clearAuthSession();
        navigate("/access-denied?reason=forbidden", { replace: true });
        return;
      }
      writeAuthSession({
        accessToken: tokenPair.access_token,
        refreshToken: tokenPair.refresh_token,
        role,
      });
      navigate(resolveWorkspaceRoute(role), { replace: true });
    } catch (error) {
      setRequestError(resolveLoginApiError(error, t));
    }
  };

  if (isBootstrapPending) {
    return (
      <Stack spacing={2} alignItems="center" sx={{ py: 6 }}>
        <CircularProgress size={28} />
        <Typography variant="body2">{t("loginPage.sessionBootstrap")}</Typography>
      </Stack>
    );
  }

  return (
    <Stack spacing={3}>
      <PageHero
        eyebrow={t("loginPage.eyebrow")}
        title={t("loginPage.title")}
        description={t("loginPage.subtitle")}
        imageSrc="/images/company-hero.jpg"
        imageAlt={t("loginPage.imageAlt")}
      />

      <Box display="flex" justifyContent="center">
        <Paper sx={{ width: "100%", maxWidth: 460, p: 3 }}>
          <Stack spacing={2} component="form" onSubmit={handleSubmit(onSubmit)}>
            <TextField
              label={t("loginPage.fields.identifier")}
              autoComplete="username"
              {...register("identifier")}
              error={Boolean(errors.identifier)}
              helperText={errors.identifier ? t("loginPage.errors.requiredField") : " "}
            />
            <TextField
              type="password"
              label={t("loginPage.fields.password")}
              autoComplete="current-password"
              {...register("password")}
              error={Boolean(errors.password)}
              helperText={errors.password ? t("loginPage.errors.requiredField") : " "}
            />

            {requestError ? <Alert severity="error">{requestError}</Alert> : null}

            <Button type="submit" variant="contained" disabled={isSubmitting}>
              {isSubmitting ? t("loginPage.submitLoading") : t("loginPage.submit")}
            </Button>
          </Stack>
        </Paper>
      </Box>
    </Stack>
  );
}

function resolveLoginApiError(error: unknown, t: (key: string) => string): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return t("loginPage.errors.http_401");
    }
    if (error.status === 422) {
      return t("loginPage.errors.http_422");
    }
  }
  return t("loginPage.errors.generic");
}
