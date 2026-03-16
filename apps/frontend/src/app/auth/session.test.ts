import { beforeEach, describe, expect, it } from "vitest";

import {
  clearAuthSession,
  readAuthSession,
  resolveAdminGuardDecision,
  resolveEmployeeGuardDecision,
  resolveLeaderGuardDecision,
  resolveWorkspaceRoute,
  writeAuthSession,
} from "./session";

describe("auth session storage", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("writes and reads access token, refresh token, and role", () => {
    writeAuthSession({
      accessToken: "access-token",
      refreshToken: "refresh-token",
      role: "hr",
    });

    expect(readAuthSession()).toEqual({
      accessToken: "access-token",
      refreshToken: "refresh-token",
      role: "hr",
    });
  });

  it("clears all session keys", () => {
    writeAuthSession({
      accessToken: "access-token",
      refreshToken: "refresh-token",
      role: "admin",
    });

    clearAuthSession();

    expect(readAuthSession()).toEqual({
      accessToken: null,
      refreshToken: null,
      role: null,
    });
  });

  it("treats unknown role as invalid", () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_refresh_token", "refresh-token");
    window.localStorage.setItem("hrm_user_role", "unknown-role");

    expect(readAuthSession()).toEqual({
      accessToken: "access-token",
      refreshToken: "refresh-token",
      role: null,
    });
  });
});

describe("resolveAdminGuardDecision", () => {
  it("returns unauthorized when access token is missing", () => {
    const decision = resolveAdminGuardDecision({ accessToken: null, refreshToken: null, role: null });
    expect(decision).toEqual({ allow: false, reason: "unauthorized" });
  });

  it("returns forbidden when role is not admin", () => {
    const decision = resolveAdminGuardDecision({ accessToken: "token", refreshToken: null, role: "hr" });
    expect(decision).toEqual({ allow: false, reason: "forbidden" });
  });

  it("returns allow for admin role with token", () => {
    const decision = resolveAdminGuardDecision({
      accessToken: "token",
      refreshToken: "refresh-token",
      role: "admin",
    });
    expect(decision).toEqual({ allow: true, role: "admin" });
  });
});

describe("resolveWorkspaceRoute", () => {
  it("routes employee role to /employee", () => {
    expect(resolveWorkspaceRoute("employee")).toBe("/employee");
  });

  it("routes leader role to /leader", () => {
    expect(resolveWorkspaceRoute("leader")).toBe("/leader");
  });
});

describe("resolveEmployeeGuardDecision", () => {
  it("returns unauthorized when access token is missing", () => {
    const decision = resolveEmployeeGuardDecision({
      accessToken: null,
      refreshToken: null,
      role: null,
    });
    expect(decision).toEqual({ allow: false, reason: "unauthorized" });
  });

  it("returns forbidden when role is not employee", () => {
    const decision = resolveEmployeeGuardDecision({
      accessToken: "token",
      refreshToken: null,
      role: "hr",
    });
    expect(decision).toEqual({ allow: false, reason: "forbidden" });
  });

  it("returns allow for employee role with token", () => {
    const decision = resolveEmployeeGuardDecision({
      accessToken: "token",
      refreshToken: "refresh-token",
      role: "employee",
    });
    expect(decision).toEqual({ allow: true, role: "employee" });
  });
});

describe("resolveLeaderGuardDecision", () => {
  it("returns unauthorized when access token is missing", () => {
    const decision = resolveLeaderGuardDecision({
      accessToken: null,
      refreshToken: null,
      role: null,
    });
    expect(decision).toEqual({ allow: false, reason: "unauthorized" });
  });

  it("returns forbidden when role is not leader/admin", () => {
    const decision = resolveLeaderGuardDecision({
      accessToken: "token",
      refreshToken: null,
      role: "hr",
    });
    expect(decision).toEqual({ allow: false, reason: "forbidden" });
  });

  it("returns allow for leader role with token", () => {
    const decision = resolveLeaderGuardDecision({
      accessToken: "token",
      refreshToken: "refresh-token",
      role: "leader",
    });
    expect(decision).toEqual({ allow: true, role: "leader" });
  });

  it("returns allow for admin role with token", () => {
    const decision = resolveLeaderGuardDecision({
      accessToken: "token",
      refreshToken: "refresh-token",
      role: "admin",
    });
    expect(decision).toEqual({ allow: true, role: "admin" });
  });
});
