import { useEffect } from "react";
import * as Sentry from "@sentry/react";

import { readAuthSession } from "../auth/session";

type SentryScopeLike = {
  setExtra(key: string, value: unknown): void;
  setTag(key: string, value: string): void;
};

type ObservabilityTags = {
  role: string;
  route: string;
  workspace: string;
};

type HttpFailureCaptureInput = {
  detail?: string;
  input: RequestInfo | URL;
  method?: string;
  status?: number;
};

/**
 * Apply canonical Sentry route tags for the active browser location.
 *
 * Inputs:
 * - optional `pathname`: explicit browser pathname for callers that already track route changes.
 *
 * Outputs:
 * - none; writes `workspace`, `role`, and `route` tags into the active Sentry scope.
 *
 * Side effects:
 * - emits Sentry tags on route mount and navigation updates.
 */
export function useSentryRouteTags(pathname?: string): void {
  useEffect(() => {
    setSentryRouteTags(pathname ?? window.location.pathname);
  }, [pathname]);
}

/**
 * Record a frontend HTTP failure in Sentry without changing the thrown exception contract.
 *
 * Inputs:
 * - `error`: the original request error or API error.
 * - `request`: request metadata used for Sentry tags and extras.
 *
 * Outputs:
 * - none.
 *
 * Side effects:
 * - sends a Sentry exception event with current route/workspace/role tags and HTTP metadata.
 */
export function captureFrontendHttpFailure(
  error: unknown,
  request: HttpFailureCaptureInput,
): void {
  const method = (request.method ?? "GET").toUpperCase();
  const requestPath = resolveRequestPath(request.input);
  const pathname = window.location.pathname;

  Sentry.withScope((scope) => {
    applySentryRouteTagsToScope(scope, pathname);
    scope.setTag("http_method", method);
    if (request.status !== undefined) {
      scope.setTag("http_status", String(request.status));
    }
    scope.setExtra("http_request_path", requestPath);
    if (request.detail) {
      scope.setExtra("http_detail", request.detail);
    }
    Sentry.captureException(resolveErrorInstance(error, method, requestPath, request.status));
  });
}

/**
 * Apply canonical route tags to an arbitrary Sentry scope.
 *
 * Inputs:
 * - `scope`: mutable Sentry scope used by error boundaries or scoped captures.
 * - `pathname`: browser pathname to normalize into a canonical route tag.
 *
 * Outputs:
 * - normalized observability tags for optional downstream use.
 *
 * Side effects:
 * - mutates the provided scope with route/workspace/role tags.
 */
export function applySentryRouteTagsToScope(
  scope: SentryScopeLike,
  pathname: string,
): ObservabilityTags {
  const tags = resolveObservabilityTags(pathname);
  scope.setTag("workspace", tags.workspace);
  scope.setTag("role", tags.role);
  scope.setTag("route", tags.route);
  return tags;
}

function setSentryRouteTags(pathname: string): ObservabilityTags {
  const tags = resolveObservabilityTags(pathname);
  Sentry.setTag("workspace", tags.workspace);
  Sentry.setTag("role", tags.role);
  Sentry.setTag("route", tags.route);
  return tags;
}

function resolveObservabilityTags(pathname: string): ObservabilityTags {
  const session = readAuthSession();
  const normalizedPath = normalizePath(pathname);

  return {
    workspace: resolveWorkspaceTag(normalizedPath),
    role: session.role ?? "anonymous",
    route: resolveRouteTag(normalizedPath),
  };
}

function resolveWorkspaceTag(pathname: string): string {
  if (pathname === "/") {
    return "company";
  }
  if (pathname === "/careers" || pathname.startsWith("/careers/")) {
    return "careers";
  }
  if (pathname === "/hr" || pathname.startsWith("/hr/")) {
    return "hr";
  }
  if (pathname === "/manager" || pathname.startsWith("/manager/")) {
    return "manager";
  }
  if (pathname === "/accountant" || pathname.startsWith("/accountant/")) {
    return "accountant";
  }
  if (pathname === "/leader" || pathname.startsWith("/leader/")) {
    return "leader";
  }
  if (pathname === "/employee" || pathname.startsWith("/employee/")) {
    return "employee";
  }
  if (pathname === "/candidate" || pathname.startsWith("/candidate/")) {
    return "candidate";
  }
  if (pathname === "/login") {
    return "auth";
  }
  if (pathname === "/admin" || pathname.startsWith("/admin/")) {
    return "admin";
  }
  return "unknown";
}

function resolveRouteTag(pathname: string): string {
  if (pathname === "/admin" || pathname.startsWith("/admin/")) {
    if (pathname === "/admin/candidates" || pathname.startsWith("/admin/candidates/")) {
      return "/admin/candidates";
    }
    if (pathname === "/admin/vacancies" || pathname.startsWith("/admin/vacancies/")) {
      return "/admin/vacancies";
    }
    if (pathname === "/admin/pipeline" || pathname.startsWith("/admin/pipeline/")) {
      return "/admin/pipeline";
    }
    if (pathname === "/admin/audit" || pathname.startsWith("/admin/audit/")) {
      return "/admin/audit";
    }
    if (
      pathname === "/admin/observability"
      || pathname.startsWith("/admin/observability/")
    ) {
      return "/admin/observability";
    }
    if (pathname === "/admin/staff" || pathname.startsWith("/admin/staff/")) {
      return "/admin/staff";
    }
    if (
      pathname === "/admin/employee-keys"
      || pathname.startsWith("/admin/employee-keys/")
    ) {
      return "/admin/employee-keys";
    }
    return "/admin";
  }
  if (pathname === "/leader" || pathname.startsWith("/leader/")) {
    return "/leader";
  }
  if (pathname === "/employee" || pathname.startsWith("/employee/")) {
    return "/employee";
  }
  if (pathname === "/hr" || pathname.startsWith("/hr/")) {
    return "/hr";
  }
  if (pathname === "/manager" || pathname.startsWith("/manager/")) {
    return "/manager";
  }
  if (pathname === "/accountant" || pathname.startsWith("/accountant/")) {
    return "/accountant";
  }
  if (pathname === "/careers" || pathname.startsWith("/careers/")) {
    return "/careers";
  }
  if (pathname === "/candidate/apply" || pathname.startsWith("/candidate/apply/")) {
    return "/candidate/apply";
  }
  if (
    pathname === "/candidate/interview"
    || pathname.startsWith("/candidate/interview/")
  ) {
    return "/candidate/interview";
  }
  if (pathname === "/candidate" || pathname.startsWith("/candidate/")) {
    return "/candidate";
  }
  if (pathname === "/login" || pathname.startsWith("/login/")) {
    return "/login";
  }
  if (pathname === "/") {
    return "/";
  }
  return pathname;
}

function normalizePath(pathname: string): string {
  const trimmed = pathname.trim();
  if (!trimmed) {
    return "/";
  }
  if (trimmed === "/") {
    return "/";
  }
  return trimmed.replace(/\/+$/, "");
}

function resolveRequestPath(input: RequestInfo | URL): string {
  const rawUrl = resolveRequestUrl(input);
  try {
    const parsed = new URL(rawUrl, window.location.origin);
    return `${parsed.pathname}${parsed.search}`;
  } catch {
    return rawUrl;
  }
}

function resolveRequestUrl(input: RequestInfo | URL): string {
  if (input instanceof URL) {
    return input.toString();
  }
  if (input instanceof Request) {
    return input.url;
  }
  return String(input);
}

function resolveErrorInstance(
  error: unknown,
  method: string,
  requestPath: string,
  status?: number,
): Error {
  if (error instanceof Error) {
    return error;
  }
  return new Error(
    `Frontend HTTP failure: ${method} ${requestPath}${status ? ` (${status})` : ""}`,
  );
}
