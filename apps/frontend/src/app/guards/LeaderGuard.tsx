import { Navigate, Outlet, useLocation } from "react-router-dom";

import { readAuthSession, resolveLeaderGuardDecision } from "../auth/session";
import { useSentryRouteTags } from "../observability/sentry";

/**
 * Route guard for the leader/admin KPI workspace on `/leader`.
 */
export function LeaderGuard() {
  const location = useLocation();
  useSentryRouteTags(location.pathname);
  const session = readAuthSession();
  const decision = resolveLeaderGuardDecision(session);

  if (!decision.allow) {
    const params = new URLSearchParams({ reason: decision.reason, next: location.pathname });
    return <Navigate to={`/access-denied?${params.toString()}`} replace />;
  }

  return <Outlet />;
}
