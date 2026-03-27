import { Alert, Stack } from "@mui/material";
import { useTranslation } from "react-i18next";

import { readAuthSession } from "../../app/auth/session";
import { useSentryRouteTags } from "../../app/observability/sentry";
import { PageHero } from "../../components/PageHero";
import { ReferralReviewTable } from "../../components/referrals/ReferralReviewTable";

/**
 * Manager-facing referral review page scoped to owned vacancies.
 */
export function ManagerReferralsPage() {
  const { t } = useTranslation();
  useSentryRouteTags("/manager/referrals");
  const session = readAuthSession();
  const accessToken = session.accessToken;

  if (!accessToken) {
    return <Alert severity="info">{t("referrals.authRequired")}</Alert>;
  }

  return (
    <Stack spacing={3}>
      <PageHero
        eyebrow={t("managerWorkspace")}
        title={t("referrals.managerTitle")}
        description={t("referrals.managerSubtitle")}
        imageSrc="/images/company-hero.jpg"
        imageAlt={t("referrals.managerTitle")}
      />

      <ReferralReviewTable accessToken={accessToken} />
    </Stack>
  );
}
