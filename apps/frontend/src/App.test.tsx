import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import "./app/i18n";
import { App } from "./App";

describe("App", () => {
  it("renders root application", () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>,
    );
    expect(
      screen.getByRole("heading", {
        name: /northstar hrm is a large company with several business directions|northstar hrm — большая компания с несколькими направлениями работы/i,
      }),
    ).toBeDefined();
    expect(
      screen.getByRole("heading", {
        name: /one company, multiple directions|одна компания, несколько направлений/i,
      }),
    ).toBeDefined();
  });
});
