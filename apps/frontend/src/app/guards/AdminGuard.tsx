import { useEffect } from "react";
import * as Sentry from "@sentry/react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { readAuthSession, resolveAdminGuardDecision } from "../auth/session";

export function AdminGuard() {
  const location = useLocation();
  const session = readAuthSession();
  const decision = resolveAdminGuardDecision(session);

  useEffect(() => {
    Sentry.setTag("workspace", "admin");
    Sentry.setTag("role", session.role ?? "anonymous");
    Sentry.setTag("route", location.pathname);
  }, [location.pathname, session.role]);

  if (!decision.allow) {
    const params = new URLSearchParams({ reason: decision.reason, next: location.pathname });
    return <Navigate to={`/access-denied?${params.toString()}`} replace />;
  }

  return <Outlet />;
}
