import { Navigate, Outlet, useLocation } from "react-router-dom";

import { readAuthSession, type AuthRole } from "../auth/session";
import { useSentryRouteTags } from "../observability/sentry";

type RoleGuardProps = {
  allowedRoles: AuthRole[];
};

/**
 * Generic guard for role-specific routes that do not need custom admin/employee semantics.
 */
export function RoleGuard({ allowedRoles }: RoleGuardProps) {
  const location = useLocation();
  useSentryRouteTags(location.pathname);
  const session = readAuthSession();

  if (!session.accessToken) {
    const params = new URLSearchParams({ reason: "unauthorized", next: location.pathname });
    return <Navigate to={`/access-denied?${params.toString()}`} replace />;
  }

  if (!session.role || !allowedRoles.includes(session.role)) {
    const params = new URLSearchParams({ reason: "forbidden", next: location.pathname });
    return <Navigate to={`/access-denied?${params.toString()}`} replace />;
  }

  return <Outlet />;
}
