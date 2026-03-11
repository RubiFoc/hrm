import { OnboardingDashboardPanel } from "../components/OnboardingDashboardPanel";
import { useSentryRouteTags } from "../app/observability/sentry";

/**
 * Manager-facing onboarding progress workspace rendered on the existing root route.
 */
export function OnboardingDashboardPage() {
  useSentryRouteTags("/");
  return <OnboardingDashboardPanel mode="standalone" />;
}
