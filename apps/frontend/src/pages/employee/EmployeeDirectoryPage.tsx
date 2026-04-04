import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Avatar,
  Button,
  Card,
  CardActions,
  CardContent,
  CircularProgress,
  Grid2,
  Stack,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, useInRouterContext } from "react-router-dom";

import {
  ApiError,
  fetchEmployeeAvatarBlob,
  listEmployeeDirectory,
  type EmployeeDirectoryListResponse,
} from "../../api";
import { readAuthSession } from "../../app/auth/session";
import { useSentryRouteTags } from "../../app/observability/sentry";
import { PageHero } from "../../components/PageHero";

const DIRECTORY_LIMIT = 20;

type DirectoryItem = EmployeeDirectoryListResponse["items"][number];

export function EmployeeDirectoryPage() {
  const { t } = useTranslation();
  useSentryRouteTags("/employee");
  const session = readAuthSession();
  const accessToken = session.accessToken;
  const inRouter = useInRouterContext();

  const directoryQuery = useQuery({
    queryKey: ["employee-directory", accessToken],
    queryFn: () => listEmployeeDirectory(accessToken!, { limit: DIRECTORY_LIMIT, offset: 0 }),
    enabled: Boolean(accessToken),
    retry: false,
  });

  if (!accessToken) {
    return (
      <Stack spacing={2}>
        <PageHero
          title={t("employeeDirectory.title")}
          description={t("employeeDirectory.subtitle")}
          imageSrc="/images/candidate-portal.jpg"
          imageAlt={t("employeeDirectory.title")}
        />
        <Alert severity="warning">{t("employeeDirectory.authRequired")}</Alert>
      </Stack>
    );
  }

  if (directoryQuery.isLoading) {
    return (
      <Stack spacing={2} alignItems="center" sx={{ py: 6 }}>
        <CircularProgress size={28} />
        <Typography variant="body2">{t("employeeDirectory.loading")}</Typography>
      </Stack>
    );
  }

  if (directoryQuery.isError) {
    return (
      <Stack spacing={2}>
        <PageHero
          title={t("employeeDirectory.title")}
          description={t("employeeDirectory.subtitle")}
          imageSrc="/images/candidate-portal.jpg"
          imageAlt={t("employeeDirectory.title")}
        />
        <Alert severity="error">{resolveDirectoryError(directoryQuery.error, t)}</Alert>
      </Stack>
    );
  }

  const directory = directoryQuery.data;
  if (!directory) {
    return null;
  }

  return (
    <Stack spacing={3}>
      <PageHero
        title={t("employeeDirectory.title")}
        description={t("employeeDirectory.subtitle")}
        imageSrc="/images/candidate-portal.jpg"
        imageAlt={t("employeeDirectory.title")}
      />

      {directory.items.length === 0 ? (
        <Alert severity="info">{t("employeeDirectory.empty")}</Alert>
      ) : (
        <Grid2 container spacing={3}>
          {directory.items.map((item) => (
            <Grid2 key={item.employee_id} size={{ xs: 12, md: 6, lg: 4 }}>
              <EmployeeDirectoryCard
                item={item}
                accessToken={accessToken}
                inRouter={inRouter}
              />
            </Grid2>
          ))}
        </Grid2>
      )}
    </Stack>
  );
}

function EmployeeDirectoryCard({
  item,
  accessToken,
  inRouter,
}: {
  item: DirectoryItem;
  accessToken: string;
  inRouter: boolean;
}) {
  const { t } = useTranslation();
  const avatarUrl = useEmployeeAvatarUrl({
    employeeId: item.employee_id,
    hasAvatar: Boolean(item.avatar),
    accessToken,
  });
  const initials = useMemo(() => resolveInitials(item.full_name), [item.full_name]);

  return (
    <Card variant="outlined" sx={{ height: "100%" }}>
      <CardContent>
        <Stack spacing={2}>
          <Stack direction="row" spacing={2} alignItems="center">
            <Avatar
              src={avatarUrl ?? undefined}
              sx={{ width: 56, height: 56, bgcolor: "primary.main" }}
            >
              {initials}
            </Avatar>
            <Stack spacing={0.25}>
              <Typography variant="h6">{item.full_name}</Typography>
              <Typography variant="body2" color="text.secondary">
                {item.position_title || t("employeeDirectory.noValue")}
              </Typography>
            </Stack>
          </Stack>

          <Stack spacing={0.75}>
            <DirectoryField
              label={t("employeeDirectory.fields.department")}
              value={item.department}
            />
            <DirectoryField
              label={t("employeeDirectory.fields.manager")}
              value={item.manager}
            />
            <DirectoryField
              label={t("employeeDirectory.fields.location")}
              value={item.location}
            />
            <DirectoryField
              label={t("employeeDirectory.fields.tenure")}
              value={formatTenure(item.tenure_in_company, t)}
              allowEmpty={false}
            />
            <DirectoryField
              label={t("employeeDirectory.fields.subordinates")}
              value={
                item.subordinates === null || item.subordinates === undefined
                  ? null
                  : String(item.subordinates)
              }
            />
          </Stack>

          <Stack spacing={0.75}>
            <DirectoryField
              label={t("employeeDirectory.fields.phone")}
              value={item.phone}
              emptyLabel={t("employeeDirectory.hiddenValue")}
            />
            <DirectoryField
              label={t("employeeDirectory.fields.email")}
              value={item.email}
              emptyLabel={t("employeeDirectory.hiddenValue")}
            />
            <DirectoryField
              label={t("employeeDirectory.fields.birthday")}
              value={item.birthday_day_month}
              emptyLabel={t("employeeDirectory.hiddenValue")}
            />
          </Stack>
        </Stack>
      </CardContent>
      <CardActions sx={{ px: 2, pb: 2 }}>
        <Button
          component={inRouter ? RouterLink : "button"}
          to={inRouter ? `/employee/directory/${item.employee_id}` : undefined}
          variant="outlined"
          size="small"
        >
          {t("employeeDirectory.actions.viewProfile")}
        </Button>
      </CardActions>
    </Card>
  );
}

function DirectoryField({
  label,
  value,
  allowEmpty = true,
  emptyLabel,
}: {
  label: string;
  value: string | null | undefined;
  allowEmpty?: boolean;
  emptyLabel?: string;
}) {
  const { t } = useTranslation();
  const resolved = value?.trim();
  const fallback = emptyLabel ?? t("employeeDirectory.noValue");
  const displayValue = resolved ? resolved : allowEmpty ? fallback : resolved;

  if (!displayValue) {
    return null;
  }

  return (
    <Stack direction="row" spacing={1}>
      <Typography variant="caption" color="text.secondary" sx={{ minWidth: 100 }}>
        {label}
      </Typography>
      <Typography variant="body2">{displayValue}</Typography>
    </Stack>
  );
}

function resolveDirectoryError(error: unknown, t: (key: string) => string): string {
  if (error instanceof ApiError) {
    const mapped = t(`employeeDirectory.errors.${error.detail}`);
    if (mapped !== `employeeDirectory.errors.${error.detail}`) {
      return mapped;
    }
    const fallback = t(`employeeDirectory.errors.http_${error.status}`);
    if (fallback !== `employeeDirectory.errors.http_${error.status}`) {
      return fallback;
    }
  }
  return t("employeeDirectory.errors.generic");
}

function resolveInitials(fullName: string): string {
  const parts = fullName
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (parts.length === 0) {
    return "?";
  }
  if (parts.length === 1) {
    return parts[0].slice(0, 1).toUpperCase();
  }
  return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
}

function formatTenure(value: number | null | undefined, t: (key: string, params?: object) => string) {
  if (value === null || value === undefined) {
    return t("employeeDirectory.noValue");
  }
  return t("employeeDirectory.tenureValue", { value });
}

function useEmployeeAvatarUrl({
  employeeId,
  hasAvatar,
  accessToken,
}: {
  employeeId: string;
  hasAvatar: boolean;
  accessToken: string;
}) {
  const avatarQuery = useQuery({
    queryKey: ["employee-avatar", employeeId, accessToken],
    queryFn: () => fetchEmployeeAvatarBlob(accessToken, employeeId),
    enabled: hasAvatar,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!avatarQuery.data) {
      setAvatarUrl(null);
      return undefined;
    }
    const objectUrl = URL.createObjectURL(avatarQuery.data);
    setAvatarUrl(objectUrl);
    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [avatarQuery.data]);

  return avatarUrl;
}
