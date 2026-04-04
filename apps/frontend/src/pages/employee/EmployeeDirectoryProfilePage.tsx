import { useEffect, useRef, useState } from "react";
import {
  Alert,
  Avatar,
  Button,
  CircularProgress,
  FormControlLabel,
  Grid2,
  Paper,
  Stack,
  Switch,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link as RouterLink, useInRouterContext, useParams } from "react-router-dom";

import {
  ApiError,
  deleteMyEmployeeAvatar,
  fetchEmployeeAvatarBlob,
  getEmployeeDirectoryProfile,
  getMyEmployeeOnboardingPortal,
  getMyEmployeePrivacySettings,
  updateMyEmployeePrivacySettings,
  uploadMyEmployeeAvatar,
  type EmployeeProfilePrivacySettingsResponse,
} from "../../api";
import { readAuthSession } from "../../app/auth/session";
import { useSentryRouteTags } from "../../app/observability/sentry";
import { PageHero } from "../../components/PageHero";

const MAX_AVATAR_SIZE_BYTES = 10 * 1024 * 1024;
const ALLOWED_AVATAR_TYPES = ["image/jpeg", "image/png", "image/webp"];

type FeedbackState = {
  type: "success" | "error";
  message: string;
};

export function EmployeeDirectoryProfilePage() {
  const { t } = useTranslation();
  useSentryRouteTags("/employee");
  const { employeeId } = useParams();
  const session = readAuthSession();
  const accessToken = session.accessToken;
  const queryClient = useQueryClient();
  const inRouter = useInRouterContext();
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const profileQuery = useQuery({
    queryKey: ["employee-directory-profile", employeeId, accessToken],
    queryFn: () => getEmployeeDirectoryProfile(accessToken!, employeeId!),
    enabled: Boolean(accessToken && employeeId),
    retry: false,
  });

  const selfQuery = useQuery({
    queryKey: ["employee-self-portal", accessToken],
    queryFn: () => getMyEmployeeOnboardingPortal(accessToken!),
    enabled: Boolean(accessToken),
    retry: false,
  });

  const isSelf = Boolean(
    profileQuery.data?.employee_id && profileQuery.data?.employee_id === selfQuery.data?.employee_id,
  );

  const privacyQuery = useQuery({
    queryKey: ["employee-privacy-settings", accessToken],
    queryFn: () => getMyEmployeePrivacySettings(accessToken!),
    enabled: Boolean(accessToken && isSelf),
    retry: false,
  });

  const avatarUrl = useEmployeeAvatarUrl({
    employeeId: profileQuery.data?.employee_id ?? "",
    hasAvatar: Boolean(profileQuery.data?.avatar),
    accessToken,
  });

  const privacyMutation = useMutation({
    mutationFn: (payload: Partial<EmployeeProfilePrivacySettingsResponse>) =>
      updateMyEmployeePrivacySettings(accessToken!, payload),
    onSuccess: (updated) => {
      queryClient.setQueryData<EmployeeProfilePrivacySettingsResponse | undefined>(
        ["employee-privacy-settings", accessToken],
        updated,
      );
      setFeedback({ type: "success", message: t("employeeDirectory.privacy.updateSuccess") });
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveDirectoryError(error, t) });
    },
  });

  const avatarUploadMutation = useMutation({
    mutationFn: (file: File) => uploadMyEmployeeAvatar(accessToken!, file),
    onSuccess: () => {
      setFeedback({ type: "success", message: t("employeeDirectory.avatar.uploadSuccess") });
      queryClient.invalidateQueries({ queryKey: ["employee-directory-profile", employeeId] });
      queryClient.invalidateQueries({ queryKey: ["employee-directory", accessToken] });
      queryClient.invalidateQueries({ queryKey: ["employee-avatar", employeeId, accessToken] });
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveAvatarError(error, t) });
    },
  });

  const avatarDeleteMutation = useMutation({
    mutationFn: () => deleteMyEmployeeAvatar(accessToken!),
    onSuccess: () => {
      setFeedback({ type: "success", message: t("employeeDirectory.avatar.deleteSuccess") });
      queryClient.invalidateQueries({ queryKey: ["employee-directory-profile", employeeId] });
      queryClient.invalidateQueries({ queryKey: ["employee-directory", accessToken] });
      queryClient.invalidateQueries({ queryKey: ["employee-avatar", employeeId, accessToken] });
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveAvatarError(error, t) });
    },
  });

  if (!accessToken) {
    return (
      <Stack spacing={2}>
        <PageHero
          title={t("employeeDirectory.profileTitle")}
          description={t("employeeDirectory.profileSubtitle")}
          imageSrc="/images/candidate-portal.jpg"
          imageAlt={t("employeeDirectory.profileTitle")}
        />
        <Alert severity="warning">{t("employeeDirectory.authRequired")}</Alert>
      </Stack>
    );
  }

  if (profileQuery.isLoading || !employeeId) {
    return (
      <Stack spacing={2} alignItems="center" sx={{ py: 6 }}>
        <CircularProgress size={28} />
        <Typography variant="body2">{t("employeeDirectory.loadingProfile")}</Typography>
      </Stack>
    );
  }

  if (profileQuery.isError) {
    return (
      <Stack spacing={2}>
        <PageHero
          title={t("employeeDirectory.profileTitle")}
          description={t("employeeDirectory.profileSubtitle")}
          imageSrc="/images/candidate-portal.jpg"
          imageAlt={t("employeeDirectory.profileTitle")}
        />
        <Alert severity="error">{resolveDirectoryError(profileQuery.error, t)}</Alert>
      </Stack>
    );
  }

  const profile = profileQuery.data;
  if (!profile) {
    return null;
  }

  return (
    <Stack spacing={3}>
      <PageHero
        title={t("employeeDirectory.profileTitle")}
        description={t("employeeDirectory.profileSubtitle")}
        imageSrc="/images/candidate-portal.jpg"
        imageAlt={t("employeeDirectory.profileTitle")}
      />

      {feedback ? <Alert severity={feedback.type}>{feedback.message}</Alert> : null}

      <Button
        component={inRouter ? RouterLink : "button"}
        to={inRouter ? "/employee/directory" : undefined}
        variant="outlined"
        size="small"
        sx={{ alignSelf: "flex-start" }}
      >
        {t("employeeDirectory.actions.backToDirectory")}
      </Button>

      <Paper sx={{ p: 3 }}>
        <Grid2 container spacing={3}>
          <Grid2 size={{ xs: 12, md: 4 }}>
            <Stack spacing={2} alignItems={{ xs: "center", md: "flex-start" }}>
              <Avatar
                src={avatarUrl ?? undefined}
                sx={{ width: 96, height: 96, bgcolor: "primary.main" }}
              >
                {resolveInitials(profile.full_name)}
              </Avatar>
              {isSelf ? (
                <Stack spacing={1} alignItems={{ xs: "center", md: "flex-start" }}>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept={ALLOWED_AVATAR_TYPES.join(",")}
                    hidden
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (!file) {
                        return;
                      }
                      const validationError = validateAvatarFile(file, t);
                      if (validationError) {
                        setFeedback({ type: "error", message: validationError });
                        event.target.value = "";
                        return;
                      }
                      avatarUploadMutation.mutate(file);
                      event.target.value = "";
                    }}
                  />
                  <Button
                    variant="contained"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={avatarUploadMutation.isPending}
                  >
                    {profile.avatar
                      ? t("employeeDirectory.avatar.update")
                      : t("employeeDirectory.avatar.upload")}
                  </Button>
                  {profile.avatar ? (
                    <Button
                      variant="text"
                      color="error"
                      onClick={() => avatarDeleteMutation.mutate()}
                      disabled={avatarDeleteMutation.isPending}
                    >
                      {t("employeeDirectory.avatar.delete")}
                    </Button>
                  ) : null}
                </Stack>
              ) : null}
            </Stack>
          </Grid2>
          <Grid2 size={{ xs: 12, md: 8 }}>
            <Stack spacing={2}>
              <Typography variant="h5">{profile.full_name}</Typography>
              <Stack spacing={1}>
                <ProfileField
                  label={t("employeeDirectory.fields.positionTitle")}
                  value={profile.position_title}
                />
                <ProfileField
                  label={t("employeeDirectory.fields.department")}
                  value={profile.department}
                />
                <ProfileField
                  label={t("employeeDirectory.fields.manager")}
                  value={profile.manager}
                />
                <ProfileField
                  label={t("employeeDirectory.fields.location")}
                  value={profile.location}
                />
                <ProfileField
                  label={t("employeeDirectory.fields.tenure")}
                  value={formatTenure(profile.tenure_in_company, t)}
                  allowEmpty={false}
                />
                <ProfileField
                  label={t("employeeDirectory.fields.subordinates")}
                  value={
                    profile.subordinates === null || profile.subordinates === undefined
                      ? null
                      : String(profile.subordinates)
                  }
                />
              </Stack>

              <Stack spacing={1}>
                <ProfileField
                  label={t("employeeDirectory.fields.phone")}
                  value={profile.phone}
                  emptyLabel={t("employeeDirectory.hiddenValue")}
                />
                <ProfileField
                  label={t("employeeDirectory.fields.email")}
                  value={profile.email}
                  emptyLabel={t("employeeDirectory.hiddenValue")}
                />
                <ProfileField
                  label={t("employeeDirectory.fields.birthday")}
                  value={profile.birthday_day_month}
                  emptyLabel={t("employeeDirectory.hiddenValue")}
                />
              </Stack>
            </Stack>
          </Grid2>
        </Grid2>
      </Paper>

      {isSelf ? (
        <Paper sx={{ p: 3 }}>
          <Stack spacing={1.5}>
            <Typography variant="h6">{t("employeeDirectory.privacy.title")}</Typography>
            <Typography variant="body2" color="text.secondary">
              {t("employeeDirectory.privacy.subtitle")}
            </Typography>
            {privacyQuery.isLoading ? (
              <Stack direction="row" spacing={1} alignItems="center">
                <CircularProgress size={20} />
                <Typography variant="body2">{t("employeeDirectory.privacy.loading")}</Typography>
              </Stack>
            ) : null}
            {privacyQuery.isError ? (
              <Alert severity="error">{resolveDirectoryError(privacyQuery.error, t)}</Alert>
            ) : null}
            {privacyQuery.data ? (
              <Stack spacing={1}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={privacyQuery.data.is_phone_visible}
                      onChange={(event) =>
                        privacyMutation.mutate({ is_phone_visible: event.target.checked })
                      }
                    />
                  }
                  label={t("employeeDirectory.privacy.showPhone")}
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={privacyQuery.data.is_email_visible}
                      onChange={(event) =>
                        privacyMutation.mutate({ is_email_visible: event.target.checked })
                      }
                    />
                  }
                  label={t("employeeDirectory.privacy.showEmail")}
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={privacyQuery.data.is_birthday_visible}
                      onChange={(event) =>
                        privacyMutation.mutate({ is_birthday_visible: event.target.checked })
                      }
                    />
                  }
                  label={t("employeeDirectory.privacy.showBirthday")}
                />
              </Stack>
            ) : null}
          </Stack>
        </Paper>
      ) : null}
    </Stack>
  );
}

function ProfileField({
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
      <Typography variant="caption" color="text.secondary" sx={{ minWidth: 140 }}>
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

function resolveAvatarError(error: unknown, t: (key: string) => string): string {
  if (error instanceof ApiError) {
    const mapped = t(`employeeDirectory.avatar.errors.${error.detail}`);
    if (mapped !== `employeeDirectory.avatar.errors.${error.detail}`) {
      return mapped;
    }
    const fallback = t(`employeeDirectory.avatar.errors.http_${error.status}`);
    if (fallback !== `employeeDirectory.avatar.errors.http_${error.status}`) {
      return fallback;
    }
  }
  return t("employeeDirectory.avatar.errors.generic");
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

function validateAvatarFile(file: File, t: (key: string) => string): string | null {
  if (!ALLOWED_AVATAR_TYPES.includes(file.type)) {
    return t("employeeDirectory.avatar.errors.avatar_mime_unsupported");
  }
  if (file.size > MAX_AVATAR_SIZE_BYTES) {
    return t("employeeDirectory.avatar.errors.avatar_too_large");
  }
  return null;
}

function useEmployeeAvatarUrl({
  employeeId,
  hasAvatar,
  accessToken,
}: {
  employeeId: string;
  hasAvatar: boolean;
  accessToken: string | null;
}) {
  const avatarQuery = useQuery({
    queryKey: ["employee-avatar", employeeId, accessToken],
    queryFn: () => fetchEmployeeAvatarBlob(accessToken!, employeeId),
    enabled: Boolean(accessToken && employeeId && hasAvatar),
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
