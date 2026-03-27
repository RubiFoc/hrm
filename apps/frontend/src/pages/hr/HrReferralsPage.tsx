import { Alert, Stack } from "@mui/material";
import { useTranslation } from "react-i18next";

import { readAuthSession } from "../../app/auth/session";
import { useSentryRouteTags } from "../../app/observability/sentry";
import { PageHero } from "../../components/PageHero";
import { ReferralReviewTable } from "../../components/referrals/ReferralReviewTable";
import { HrWorkspaceNav } from "./HrWorkspaceNav";

/**
 * HR-facing referral review workspace.
 */
export function HrReferralsPage() {
  const { t } = useTranslation();
  useSentryRouteTags("/hr/referrals");
  const session = readAuthSession();
  const accessToken = session.accessToken;

  if (!accessToken) {
    return <Alert severity="info">{t("referrals.authRequired")}</Alert>;
  }

  return (
    <Stack spacing={3}>
      <PageHero
        eyebrow={t("hrDashboard.title")}
        title={t("hrWorkspacePages.referrals.title")}
        description={t("hrWorkspacePages.referrals.subtitle")}
        imageSrc="/images/company-hero.jpg"
        imageAlt={t("hrWorkspacePages.referrals.title")}
      />

      <HrWorkspaceNav />

      <ReferralReviewTable accessToken={accessToken} />
    </Stack>
  );
}
