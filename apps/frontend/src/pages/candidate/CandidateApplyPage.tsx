import { Stack } from "@mui/material";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";

import { useSentryRouteTags } from "../../app/observability/sentry";
import { CandidateApplyTrackingWorkspace } from "../../components/candidate/CandidateApplyTrackingWorkspace";
import { PageHero } from "../../components/PageHero";
import { PublicRailCard } from "../../components/public/PublicRailCard";
import { normalizeInput } from "./candidateUtils";

/**
 * Public candidate application page for a selected vacancy and the CV tracking workspace.
 */
export function CandidateApplyPage() {
  const { t } = useTranslation();
  useSentryRouteTags("/candidate/apply");
  const [searchParams] = useSearchParams();
  const queryVacancyId = normalizeInput(searchParams.get("vacancyId"));
  const queryVacancyTitle = normalizeInput(searchParams.get("vacancyTitle"));

  return (
    <Stack spacing={4}>
      <PageHero
        eyebrow={t("candidatePortal.eyebrow")}
        title={t("candidateWorkspace")}
        description={t("candidatePortal.subtitle")}
        imageSrc="/images/candidate-portal.jpg"
        imageAlt={t("candidatePortal.imageAlt")}
        chips={[
          t("candidatePortal.highlights.upload"),
          t("candidatePortal.highlights.track"),
          t("candidatePortal.highlights.interview"),
        ]}
        sideContent={
          <PublicRailCard
            eyebrow={t("candidateApply.prepRail.eyebrow")}
            title={t("candidateApply.prepRail.title")}
            subtitle={t("candidateApply.prepRail.subtitle")}
            chips={[
              t("candidatePortal.highlights.upload"),
              t("candidatePortal.highlights.track"),
              t("candidatePortal.highlights.interview"),
            ]}
            items={[
              {
                title: t("candidateApply.prepRail.items.file.title"),
                description: t("candidateApply.prepRail.items.file.description"),
              },
              {
                title: t("candidateApply.prepRail.items.tracking.title"),
                description: t("candidateApply.prepRail.items.tracking.description"),
              },
              {
                title: t("candidateApply.prepRail.items.account.title"),
                description: t("candidateApply.prepRail.items.account.description"),
              },
            ]}
          />
        }
      />

      <CandidateApplyTrackingWorkspace
        queryVacancyId={queryVacancyId}
        queryVacancyTitle={queryVacancyTitle}
      />
    </Stack>
  );
}
