import { ApiError } from "../../api";

export function resolveReferralError(
  error: unknown,
  t: (key: string) => string,
): string {
  if (error instanceof Error && !(error instanceof ApiError)) {
    return error.message;
  }
  if (error instanceof ApiError) {
    const detail = error.detail.toLowerCase();
    if (detail.includes("vacancy_not_found") || detail.includes("vacancy not found")) {
      return t("referrals.errors.vacancyNotFound");
    }
    if (detail.includes("vacancy_not_open") || detail.includes("not open")) {
      return t("referrals.errors.vacancyClosed");
    }
    if (detail.includes("referrer_employee_profile_not_found")) {
      return t("referrals.errors.referrerNotFound");
    }
    if (detail.includes("referral_not_found")) {
      return t("referrals.errors.referralNotFound");
    }
    if (detail.includes("referral_forbidden")) {
      return t("referrals.errors.referralForbidden");
    }
    if (detail.includes("referral_stage_not_allowed")) {
      return t("referrals.errors.referralStageNotAllowed");
    }
    if (detail.includes("referral_invalid_transition")) {
      return t("referrals.errors.referralInvalidTransition");
    }
    if (detail.includes("referral_already_in_stage")) {
      return t("referrals.errors.referralAlreadyInStage");
    }
    if (detail.includes("referral_candidate_missing")) {
      return t("referrals.errors.referralCandidateMissing");
    }
    if (detail.includes("referral_duplicate")) {
      return t("referrals.errors.duplicate");
    }
    const statusMessage = t(`referrals.errors.http_${error.status}`);
    if (statusMessage !== `referrals.errors.http_${error.status}`) {
      return statusMessage;
    }
  }
  return t("referrals.errors.generic");
}
