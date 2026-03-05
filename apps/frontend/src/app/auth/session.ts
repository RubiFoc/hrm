export type AuthRole = "admin" | "hr" | "manager" | "employee" | "leader" | "accountant";

export type AuthSessionState = {
  accessToken: string | null;
  role: AuthRole | null;
};

export type AdminGuardDecision =
  | { allow: true; role: AuthRole }
  | { allow: false; reason: "unauthorized" | "forbidden" };

const AUTH_TOKEN_KEY = "hrm_access_token";
const AUTH_ROLE_KEY = "hrm_user_role";

const KNOWN_ROLES: ReadonlySet<string> = new Set([
  "admin",
  "hr",
  "manager",
  "employee",
  "leader",
  "accountant",
]);

export function readAuthSession(): AuthSessionState {
  const accessToken = window.localStorage.getItem(AUTH_TOKEN_KEY);
  const rawRole = window.localStorage.getItem(AUTH_ROLE_KEY);
  const role = rawRole && KNOWN_ROLES.has(rawRole) ? (rawRole as AuthRole) : null;
  return { accessToken, role };
}

export function resolveAdminGuardDecision(session: AuthSessionState): AdminGuardDecision {
  if (!session.accessToken) {
    return { allow: false, reason: "unauthorized" };
  }
  if (session.role !== "admin") {
    return { allow: false, reason: "forbidden" };
  }
  return { allow: true, role: session.role };
}
