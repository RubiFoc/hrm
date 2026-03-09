import { Navigate, Outlet, useLocation } from "react-router-dom";

import { readAuthSession, resolveAdminGuardDecision } from "../auth/session";
import { useSentryRouteTags } from "../observability/sentry";

export function AdminGuard() {
  const location = useLocation();
  useSentryRouteTags(location.pathname);
  const session = readAuthSession();
  const decision = resolveAdminGuardDecision(session);

  if (!decision.allow) {
    const params = new URLSearchParams({ reason: decision.reason, next: location.pathname });
    return <Navigate to={`/access-denied?${params.toString()}`} replace />;
  }

  return <Outlet />;
}
