import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import i18n from "i18next";

import "../../app/i18n";
import { AdminAuditPage } from "./AdminAuditPage";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AdminAuditPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function jsonResponse(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

describe("AdminAuditPage", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(async () => {
    fetchMock.mockReset();
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:mock"),
    });
    Object.defineProperty(window.URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
    Object.defineProperty(HTMLAnchorElement.prototype, "click", {
      configurable: true,
      value: vi.fn(),
    });
    await i18n.changeLanguage("ru");
  });

  it("renders audit rows and supports RU/EN localization", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      }),
    );

    renderPage();
    expect(await screen.findByRole("heading", { name: /консоль аудита/i })).toBeDefined();

    await i18n.changeLanguage("en");
    expect(await screen.findByRole("heading", { name: /audit console/i })).toBeDefined();
  });

  it("applies filters and exports xlsx", async () => {
    const listResponse = {
      items: [
        {
          event_id: "1d1e1f1a-2b2c-4d4e-8f8a-9a9b9c9d9e9f",
          occurred_at: "2026-03-19T10:00:00Z",
          source: "api",
          actor_sub: "admin-1",
          actor_role: "admin",
          action: "vacancy:create",
          resource_type: "vacancy",
          resource_id: "vacancy-1",
          result: "success",
          reason: null,
          correlation_id: "corr-1",
          ip: "127.0.0.1",
          user_agent: "Mozilla/5.0",
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
    };

    fetchMock.mockImplementation((input) => {
      const requestUrl = new URL(String(input), window.location.origin);
      if (requestUrl.pathname === "/api/v1/audit/events") {
        return Promise.resolve(jsonResponse(listResponse));
      }
      if (requestUrl.pathname === "/api/v1/audit/events/export") {
        return Promise.resolve(
          new Response("xlsx-bytes", {
            status: 200,
            headers: {
              "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              "Content-Disposition": 'attachment; filename="audit-events.xlsx"',
            },
          }),
        );
      }
      return Promise.resolve(jsonResponse(listResponse));
    });

    renderPage();
    await screen.findByText("vacancy:create");

    fireEvent.change(screen.getByLabelText(/действие/i), {
      target: { value: "vacancy:create" },
    });
    fireEvent.click(screen.getByRole("button", { name: /применить/i }));

    await waitFor(() => {
      expect(fetchMock.mock.calls.some((call) => String(call[0]).includes("action=vacancy%3Acreate"))).toBe(true);
    });

    fireEvent.click(screen.getByRole("button", { name: /экспорт excel/i }));

    await waitFor(() => {
      expect(fetchMock.mock.calls.some((call) => String(call[0]).includes("/api/v1/audit/events/export"))).toBe(true);
    });

    expect(
      fetchMock.mock.calls.some((call) => String(call[0]).includes("format=xlsx")),
    ).toBe(true);
    expect(await screen.findByText(/файл excel экспортирован/i)).toBeDefined();
  });
});
