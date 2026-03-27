import { useState } from "react";
import {
  Alert,
  Button,
  Grid2,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import {
  listPublicVacancies,
  submitReferral,
  type PublicVacancyListItemResponse,
  type ReferralSubmitRequest,
  type ReferralSubmitResponse,
} from "../../api";
import { readAuthSession } from "../../app/auth/session";
import { useSentryRouteTags } from "../../app/observability/sentry";
import { PageHero } from "../../components/PageHero";
import { resolveReferralError } from "../../components/referrals/referralErrors";

const REFERRAL_FORM_SCHEMA = z.object({
  vacancy_id: z.string().uuid(),
  full_name: z.string().trim().min(1),
  email: z.string().trim().email(),
  phone: z.string().trim().min(3),
});
const ACCEPT_ATTRIBUTE = ".pdf,.doc,.docx";

type ReferralForm = z.infer<typeof REFERRAL_FORM_SCHEMA>;
type SubmissionFeedback = {
  type: "success" | "warning";
  message: string;
  response?: ReferralSubmitResponse;
};

/**
 * Employee-facing referral submission workspace.
 */
export function EmployeeReferralsPage() {
  const { t } = useTranslation();
  useSentryRouteTags("/employee/referrals");
  const session = readAuthSession();
  const accessToken = session.accessToken;
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileFeedback, setFileFeedback] = useState<string | null>(null);
  const [submitFeedback, setSubmitFeedback] = useState<string | null>(null);
  const [submission, setSubmission] = useState<SubmissionFeedback | null>(null);
  const [isChecksumPending, setIsChecksumPending] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<ReferralForm>({
    resolver: zodResolver(REFERRAL_FORM_SCHEMA),
    defaultValues: {
      vacancy_id: "",
      full_name: "",
      email: "",
      phone: "",
    },
  });
  const selectedVacancyId = watch("vacancy_id");

  const vacanciesQuery = useQuery({
    queryKey: ["public-vacancies"],
    queryFn: () => listPublicVacancies(),
    retry: false,
  });

  const submitMutation = useMutation({
    mutationFn: (payload: ReferralSubmitRequest) =>
      submitReferral(accessToken!, payload),
  });

  const onSubmit = async (values: ReferralForm) => {
    if (!accessToken) {
      return;
    }
    setSubmitFeedback(null);
    setSubmission(null);

    if (!selectedFile) {
      setFileFeedback(t("referrals.errors.fileRequired"));
      return;
    }

    const fileError = validateReferralFile(selectedFile, t);
    if (fileError) {
      setFileFeedback(fileError);
      return;
    }

    setFileFeedback(null);
    setIsChecksumPending(true);
    try {
      const checksumSha256 = await computeFileChecksumSha256(selectedFile);
      const response = await submitMutation.mutateAsync({
        vacancy_id: values.vacancy_id,
        full_name: values.full_name.trim(),
        email: values.email.trim(),
        phone: values.phone.trim(),
        checksum_sha256: checksumSha256,
        file: selectedFile,
      });
      const message = response.is_duplicate
        ? t("referrals.submitDuplicate")
        : t("referrals.submitSuccess");
      setSubmission({
        type: response.is_duplicate ? "warning" : "success",
        message,
        response,
      });
    } catch (error) {
      setSubmitFeedback(resolveReferralError(error, t));
    } finally {
      setIsChecksumPending(false);
    }
  };

  const vacancyOptions = vacanciesQuery.data?.items ?? [];

  if (!accessToken) {
    return <Alert severity="info">{t("referrals.authRequired")}</Alert>;
  }

  return (
    <Stack spacing={3}>
      <PageHero
        title={t("referrals.employeeTitle")}
        description={t("referrals.employeeSubtitle")}
        imageSrc="/images/candidate-portal.jpg"
        imageAlt={t("referrals.employeeTitle")}
      />

      <Alert severity="info">{t("referrals.consentNote")}</Alert>

      <Grid2 container spacing={2}>
        <Grid2 size={{ xs: 12, lg: 7 }}>
          <Paper sx={{ p: 3 }}>
            <Stack spacing={2} component="form" onSubmit={handleSubmit(onSubmit)}>
              <Typography variant="h6">{t("referrals.formTitle")}</Typography>

              <TextField
                select
                label={t("referrals.fields.vacancy")}
                {...register("vacancy_id")}
                error={Boolean(errors.vacancy_id)}
                helperText={errors.vacancy_id ? t("referrals.errors.requiredField") : " "}
                value={selectedVacancyId}
                onChange={(event) =>
                  setValue("vacancy_id", event.target.value, { shouldValidate: true })
                }
              >
                <MenuItem value="">
                  {t("referrals.fields.vacancyPlaceholder")}
                </MenuItem>
                {vacancyOptions.map((vacancy) => (
                  <MenuItem key={vacancy.vacancy_id} value={vacancy.vacancy_id}>
                    {formatVacancyLabel(vacancy)}
                  </MenuItem>
                ))}
              </TextField>

              <TextField
                label={t("referrals.fields.fullName")}
                {...register("full_name")}
                error={Boolean(errors.full_name)}
                helperText={errors.full_name ? t("referrals.errors.requiredField") : " "}
              />
              <TextField
                label={t("referrals.fields.email")}
                {...register("email")}
                error={Boolean(errors.email)}
                helperText={errors.email ? t("referrals.errors.invalidEmail") : " "}
              />
              <TextField
                label={t("referrals.fields.phone")}
                {...register("phone")}
                error={Boolean(errors.phone)}
                helperText={errors.phone ? t("referrals.errors.requiredField") : " "}
              />

              <Button variant="contained" component="label">
                {selectedFile
                  ? t("referrals.fileSelected", { filename: selectedFile.name })
                  : t("referrals.fields.cvFile")}
                <input
                  hidden
                  type="file"
                  accept={ACCEPT_ATTRIBUTE}
                  onChange={(event) => {
                    const nextFile = event.target.files?.[0] ?? null;
                    setSelectedFile(nextFile);
                    setFileFeedback(validateReferralFile(nextFile, t));
                  }}
                />
              </Button>

              {fileFeedback ? <Alert severity="error">{fileFeedback}</Alert> : null}
              {submitFeedback ? <Alert severity="error">{submitFeedback}</Alert> : null}
              {submission ? (
                <Alert severity={submission.type}>
                  {submission.message}
                  {submission.response?.candidate_id ? (
                    <>
                      {" "}
                      {t("referrals.submitCandidateId", {
                        candidateId: submission.response.candidate_id,
                      })}
                    </>
                  ) : null}
                </Alert>
              ) : null}

              <Button
                type="submit"
                variant="contained"
                disabled={submitMutation.isPending || isChecksumPending}
              >
                {submitMutation.isPending || isChecksumPending
                  ? t("referrals.submitPending")
                  : t("referrals.submit")}
              </Button>
            </Stack>
          </Paper>
        </Grid2>

        <Grid2 size={{ xs: 12, lg: 5 }}>
          <Paper sx={{ p: 3, height: "100%" }}>
            <Stack spacing={2}>
              <Typography variant="h6">{t("referrals.sidebar.title")}</Typography>
              <Typography variant="body2" color="text.secondary">
                {t("referrals.sidebar.subtitle")}
              </Typography>
              <Typography variant="body2">{t("referrals.sidebar.note")}</Typography>
            </Stack>
          </Paper>
        </Grid2>
      </Grid2>
    </Stack>
  );
}

function formatVacancyLabel(vacancy: PublicVacancyListItemResponse): string {
  return `${vacancy.title} · ${vacancy.department}`;
}

function validateReferralFile(
  file: File | null,
  t: (key: string, options?: Record<string, string | number>) => string,
): string | null {
  if (!file) {
    return null;
  }
  const filename = file.name.toLowerCase();
  const mimeType = file.type.toLowerCase();
  const isAcceptedExtension =
    filename.endsWith(".pdf") || filename.endsWith(".doc") || filename.endsWith(".docx");
  const isAcceptedMime =
    mimeType === "application/pdf"
    || mimeType === "application/msword"
    || mimeType
      === "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  if (!isAcceptedExtension && !isAcceptedMime) {
    return t("referrals.errors.fileType");
  }
  return null;
}

async function computeFileChecksumSha256(file: File): Promise<string> {
  const payload = await file.arrayBuffer();
  const digest = await window.crypto.subtle.digest("SHA-256", payload);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}
