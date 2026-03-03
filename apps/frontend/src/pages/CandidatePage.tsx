import { Button, Stack, TextField, Typography } from "@mui/material";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

const candidateSchema = z.object({
  fullName: z.string().min(2),
  email: z.string().email(),
});

type CandidateForm = z.infer<typeof candidateSchema>;

export function CandidatePage() {
  const { t } = useTranslation();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CandidateForm>({
    resolver: zodResolver(candidateSchema),
    defaultValues: { fullName: "", email: "" },
  });

  const onSubmit = (data: CandidateForm) => {
    console.log("candidate form", data);
  };

  return (
    <Stack spacing={2} component="form" onSubmit={handleSubmit(onSubmit)}>
      <Typography variant="h5">{t("candidateWorkspace")}</Typography>
      <TextField
        label="Full Name"
        {...register("fullName")}
        error={Boolean(errors.fullName)}
        helperText={errors.fullName?.message}
      />
      <TextField
        label="Email"
        {...register("email")}
        error={Boolean(errors.email)}
        helperText={errors.email?.message}
      />
      <Button variant="contained" component="label">
        {t("uploadCv")}
        <input hidden type="file" accept=".pdf,.doc,.docx" />
      </Button>
      <Button type="submit" variant="outlined">{t("signProfile")}</Button>
      <Button type="button" variant="contained">{t("registerInterview")}</Button>
    </Stack>
  );
}
