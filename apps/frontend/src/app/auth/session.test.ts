import { describe, expect, it } from "vitest";

import { resolveAdminGuardDecision } from "./session";

describe("resolveAdminGuardDecision", () => {
  it("returns unauthorized when access token is missing", () => {
    const decision = resolveAdminGuardDecision({ accessToken: null, role: null });
    expect(decision).toEqual({ allow: false, reason: "unauthorized" });
  });

  it("returns forbidden when role is not admin", () => {
    const decision = resolveAdminGuardDecision({ accessToken: "token", role: "hr" });
    expect(decision).toEqual({ allow: false, reason: "forbidden" });
  });

  it("returns allow for admin role with token", () => {
    const decision = resolveAdminGuardDecision({ accessToken: "token", role: "admin" });
    expect(decision).toEqual({ allow: true, role: "admin" });
  });
});
