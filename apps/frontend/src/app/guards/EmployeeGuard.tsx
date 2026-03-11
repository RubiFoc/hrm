import { Navigate, Outlet, useLocation } from "react-router-dom";

import { readAuthSession, resolveEmployeeGuardDecision } from "../auth/session";
import { useSentryRouteTags } from "../observability/sentry";

export function EmployeeGuard() {
  const location = useLocation();
  useSentryRouteTags(location.pathname);
  const session = readAuthSession();
  const decision = resolveEmployeeGuardDecision(session);

  if (!decision.allow) {
    const params = new URLSearchParams({ reason: decision.reason, next: location.pathname });
    return <Navigate to={`/access-denied?${params.toString()}`} replace />;
  }

  return <Outlet />;
}
