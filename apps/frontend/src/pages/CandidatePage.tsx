import { Navigate, useSearchParams } from "react-router-dom";

import { useSentryRouteTags } from "../app/observability/sentry";
import { normalizeInput } from "./candidate/candidateUtils";

/**
 * Legacy `/candidate` compatibility shell that redirects to dedicated apply or interview routes.
 *
 * The shell never renders its own workspace. It forwards legacy vacancy and interview links to
 * the canonical public routes and prefers interview registration when both legacy parameters are
 * present.
 */
export function CandidatePage() {
  useSentryRouteTags("/candidate");
  const [searchParams] = useSearchParams();
  const queryVacancyId = normalizeInput(searchParams.get("vacancyId"));
  const queryVacancyTitle = normalizeInput(searchParams.get("vacancyTitle"));
  const interviewToken = normalizeInput(searchParams.get("interviewToken"));

  if (interviewToken) {
    return <Navigate replace to={`/candidate/interview/${encodeURIComponent(interviewToken)}`} />;
  }

  return <Navigate replace to={buildCandidateApplyRoute(queryVacancyId, queryVacancyTitle)} />;
}

function buildCandidateApplyRoute(
  queryVacancyId: string | null,
  queryVacancyTitle: string | null,
): string {
  const searchParams = new URLSearchParams();
  if (queryVacancyId) {
    searchParams.set("vacancyId", queryVacancyId);
  }
  if (queryVacancyTitle) {
    searchParams.set("vacancyTitle", queryVacancyTitle);
  }

  const queryString = searchParams.toString();
  return queryString ? `/candidate/apply?${queryString}` : "/candidate/apply";
}
