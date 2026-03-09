import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import "../i18n";
import { AppErrorBoundary } from "./AppErrorBoundary";

function CrashingScreen() {
  throw new Error("render boom");
}

describe("AppErrorBoundary", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders localized fallback UI when a child throws during render", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <AppErrorBoundary>
        <CrashingScreen />
      </AppErrorBoundary>,
    );

    expect(await screen.findByRole("heading", { name: /что-то пошло не так/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /повторить рендер/i })).toBeDefined();
  });
});
