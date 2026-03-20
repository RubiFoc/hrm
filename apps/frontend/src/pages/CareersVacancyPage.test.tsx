import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import "../app/i18n";
import i18n from "i18next";
import { CareersVacancyPage } from "./CareersVacancyPage";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

const PUBLIC_VACANCIES = {
  items: [
    {
      vacancy_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      title: "Backend Engineer",
      description: "Build public APIs, candidate flows, and internal tooling.",
      department: "Engineering",
      created_at: "2026-03-10T08:00:00Z",
      updated_at: "2026-03-12T08:30:00Z",
    },
  ],
};

function renderCareersVacancyPage(initialEntries = ["/careers/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"]) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/careers/:vacancyId" element={<CareersVacancyPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function jsonResponse(payload: unknown, status = 200): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("CareersVacancyPage", () => {
  beforeEach(async () => {
    window.localStorage.clear();
    window.history.pushState({}, "", "/careers/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa");
    fetchMock.mockReset();
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/public/vacancies")) {
        return jsonResponse(PUBLIC_VACANCIES);
      }
      return jsonResponse({}, 404);
    });
    await i18n.changeLanguage("en");
  });

  afterEach(() => {
    cleanup();
  });

  it("renders the vacancy detail page and application workspace for the selected role", async () => {
    renderCareersVacancyPage();

    expect(
      await screen.findByRole("heading", { name: /backend engineer/i }),
    ).toBeDefined();
    expect(await screen.findByRole("heading", { name: /application workspace/i })).toBeDefined();
    expect(await screen.findByRole("link", { name: /back to open roles/i })).toBeDefined();
    expect(screen.getByText(/shareable public vacancy page for review and application/i)).toBeDefined();
  });
});
