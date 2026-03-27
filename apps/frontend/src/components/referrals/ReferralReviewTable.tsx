import { useMemo, useState } from "react";
import {
  Alert,
  Button,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import {
  listReferrals,
  reviewReferral,
  type ReferralListItemResponse,
  type ReferralReviewRequest,
} from "../../api";
import { formatDateTime } from "../../pages/hr/hrWorkspaceShared";
import { resolveReferralError } from "./referralErrors";

const REVIEW_STAGES: ReferralReviewRequest["to_stage"][] = ["screening", "shortlist"];
const TERMINAL_STAGES = new Set(["interview", "offer", "hired", "rejected"]);

type FeedbackState = {
  type: "success" | "error";
  message: string;
};

type ReferralReviewTableProps = {
  accessToken: string;
  vacancyId?: string | null;
};

export function ReferralReviewTable({
  accessToken,
  vacancyId,
}: ReferralReviewTableProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const [pendingReferralId, setPendingReferralId] = useState<string | null>(null);

  const referralQueryKey = useMemo(
    () => ["referrals", accessToken, vacancyId ?? "all"],
    [accessToken, vacancyId],
  );

  const referralsQuery = useQuery({
    queryKey: referralQueryKey,
    queryFn: () =>
      listReferrals(accessToken, { vacancy_id: vacancyId ?? undefined, limit: 50, offset: 0 }),
    enabled: Boolean(accessToken),
    retry: false,
  });

  const reviewMutation = useMutation({
    mutationFn: ({
      referralId,
      payload,
    }: {
      referralId: string;
      payload: ReferralReviewRequest;
    }) => reviewReferral(accessToken, referralId, payload),
    onMutate: ({ referralId }) => {
      setFeedback(null);
      setPendingReferralId(referralId);
    },
    onSuccess: () => {
      setFeedback({ type: "success", message: t("referrals.reviewSuccess") });
      void queryClient.invalidateQueries({ queryKey: referralQueryKey });
    },
    onError: (error: unknown) => {
      setFeedback({ type: "error", message: resolveReferralError(error, t) });
    },
    onSettled: () => {
      setPendingReferralId(null);
    },
  });

  const referralItems = referralsQuery.data?.items ?? [];

  if (!accessToken) {
    return <Alert severity="info">{t("referrals.authRequired")}</Alert>;
  }

  return (
    <Stack spacing={2}>
      {feedback ? <Alert severity={feedback.type}>{feedback.message}</Alert> : null}
      {referralsQuery.isLoading ? (
        <Typography variant="body2">{t("referrals.loading")}</Typography>
      ) : null}
      {referralsQuery.isError ? (
        <Alert severity="error">{resolveReferralError(referralsQuery.error, t)}</Alert>
      ) : null}
      {referralsQuery.data ? (
        <Typography variant="body2" color="text.secondary">
          {t("referrals.total", { total: referralsQuery.data.total })}
        </Typography>
      ) : null}
      {referralsQuery.data && referralItems.length === 0 ? (
        <Alert severity="info">{t("referrals.empty")}</Alert>
      ) : null}
      {referralItems.length > 0 ? (
        <Paper>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>{t("referrals.table.candidate")}</TableCell>
                <TableCell>{t("referrals.table.vacancy")}</TableCell>
                <TableCell>{t("referrals.table.referrer")}</TableCell>
                <TableCell>{t("referrals.table.submittedAt")}</TableCell>
                <TableCell>{t("referrals.table.stage")}</TableCell>
                <TableCell>{t("referrals.table.actions")}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {referralItems.map((item) => (
                <TableRow key={item.referral_id}>
                  <TableCell>
                    <Stack spacing={0.25}>
                      <Typography variant="body2">{item.candidate_full_name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {item.candidate_email}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {item.candidate_phone}
                      </Typography>
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Stack spacing={0.25}>
                      <Typography variant="body2">{item.vacancy_title}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {item.vacancy_id}
                      </Typography>
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Stack spacing={0.25}>
                      <Typography variant="body2">{item.referrer_full_name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {item.referrer_employee_id}
                      </Typography>
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{formatDateTime(item.submitted_at)}</Typography>
                  </TableCell>
                  <TableCell>
                    <Stack spacing={0.25}>
                      <Typography variant="body2">
                        {item.current_stage
                          ? t(`hrDashboard.stages.${item.current_stage}`)
                          : t("referrals.stagePending")}
                      </Typography>
                      {item.current_stage_at ? (
                        <Typography variant="caption" color="text.secondary">
                          {formatDateTime(item.current_stage_at)}
                        </Typography>
                      ) : null}
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Stack direction={{ xs: "column", md: "row" }} spacing={1}>
                      {REVIEW_STAGES.map((stage) => (
                        <Button
                          key={stage}
                          size="small"
                          variant="outlined"
                          onClick={() => handleReview(item, stage, reviewMutation.mutate)}
                          disabled={
                            pendingReferralId === item.referral_id
                            || isReviewDisabled(item.current_stage, stage)
                          }
                        >
                          {t(`referrals.actions.${stage}`)}
                        </Button>
                      ))}
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      ) : null}
    </Stack>
  );
}

function handleReview(
  item: ReferralListItemResponse,
  stage: ReferralReviewRequest["to_stage"],
  mutate: (payload: { referralId: string; payload: ReferralReviewRequest }) => void,
): void {
  mutate({
    referralId: item.referral_id,
    payload: { to_stage: stage },
  });
}

function isReviewDisabled(
  currentStage: string | null,
  targetStage: ReferralReviewRequest["to_stage"],
): boolean {
  if (!currentStage) {
    return false;
  }
  if (TERMINAL_STAGES.has(currentStage)) {
    return true;
  }
  if (currentStage === targetStage) {
    return true;
  }
  if (currentStage === "shortlist" && targetStage === "screening") {
    return true;
  }
  return false;
}
