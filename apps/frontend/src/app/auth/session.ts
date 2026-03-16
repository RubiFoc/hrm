export type AuthRole = "admin" | "hr" | "manager" | "employee" | "leader" | "accountant";

export type AuthSessionState = {
  accessToken: string | null;
  refreshToken: string | null;
  role: AuthRole | null;
};

export type WritableAuthSession = {
  accessToken: string;
  refreshToken: string | null;
  role: AuthRole;
};

export type AdminGuardDecision =
  | { allow: true; role: AuthRole }
  | { allow: false; reason: "unauthorized" | "forbidden" };
export type EmployeeGuardDecision =
  | { allow: true; role: "employee" }
  | { allow: false; reason: "unauthorized" | "forbidden" };
export type LeaderGuardDecision =
  | { allow: true; role: "leader" | "admin" }
  | { allow: false; reason: "unauthorized" | "forbidden" };

const AUTH_TOKEN_KEY = "hrm_access_token";
const AUTH_REFRESH_TOKEN_KEY = "hrm_refresh_token";
const AUTH_ROLE_KEY = "hrm_user_role";

const KNOWN_ROLES: ReadonlySet<string> = new Set([
  "admin",
  "hr",
  "manager",
  "employee",
  "leader",
  "accountant",
]);

/**
 * Resolve raw string role value from transport/storage into known role union.
 */
export function resolveAuthRole(rawRole: string | null | undefined): AuthRole | null {
  if (!rawRole || !KNOWN_ROLES.has(rawRole)) {
    return null;
  }
  return rawRole as AuthRole;
}

/**
 * Read authentication session from browser local storage.
 */
export function readAuthSession(): AuthSessionState {
  const accessToken = normalizeStoredToken(window.localStorage.getItem(AUTH_TOKEN_KEY));
  const refreshToken = normalizeStoredToken(window.localStorage.getItem(AUTH_REFRESH_TOKEN_KEY));
  const role = resolveAuthRole(window.localStorage.getItem(AUTH_ROLE_KEY));
  return { accessToken, refreshToken, role };
}

/**
 * Persist auth session to local storage.
 */
export function writeAuthSession(session: WritableAuthSession): void {
  window.localStorage.setItem(AUTH_TOKEN_KEY, session.accessToken);
  if (session.refreshToken) {
    window.localStorage.setItem(AUTH_REFRESH_TOKEN_KEY, session.refreshToken);
  } else {
    window.localStorage.removeItem(AUTH_REFRESH_TOKEN_KEY);
  }
  window.localStorage.setItem(AUTH_ROLE_KEY, session.role);
}

/**
 * Remove all auth session keys from local storage.
 */
export function clearAuthSession(): void {
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
  window.localStorage.removeItem(AUTH_REFRESH_TOKEN_KEY);
  window.localStorage.removeItem(AUTH_ROLE_KEY);
}

/**
 * Resolve target workspace path by authenticated role.
 */
export function resolveWorkspaceRoute(role: AuthRole | null): string {
  if (!role) {
    return "/access-denied?reason=forbidden";
  }
  if (role === "admin") {
    return "/admin";
  }
  if (role === "employee") {
    return "/employee";
  }
  if (role === "leader") {
    return "/leader";
  }
  return "/";
}

/**
 * Evaluate `/admin` route access using current session snapshot.
 */
export function resolveAdminGuardDecision(session: AuthSessionState): AdminGuardDecision {
  if (!session.accessToken) {
    return { allow: false, reason: "unauthorized" };
  }
  if (session.role !== "admin") {
    return { allow: false, reason: "forbidden" };
  }
  return { allow: true, role: session.role };
}

/**
 * Evaluate `/employee` route access using current session snapshot.
 */
export function resolveEmployeeGuardDecision(session: AuthSessionState): EmployeeGuardDecision {
  if (!session.accessToken) {
    return { allow: false, reason: "unauthorized" };
  }
  if (session.role !== "employee") {
    return { allow: false, reason: "forbidden" };
  }
  return { allow: true, role: session.role };
}

/**
 * Evaluate `/leader` route access using current session snapshot.
 */
export function resolveLeaderGuardDecision(session: AuthSessionState): LeaderGuardDecision {
  if (!session.accessToken) {
    return { allow: false, reason: "unauthorized" };
  }
  if (session.role !== "leader" && session.role !== "admin") {
    return { allow: false, reason: "forbidden" };
  }
  return { allow: true, role: session.role };
}

function normalizeStoredToken(value: string | null): string | null {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}
