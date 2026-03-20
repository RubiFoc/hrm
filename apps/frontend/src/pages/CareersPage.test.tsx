import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import "../app/i18n";
import i18n from "i18next";
import { CareersPage } from "./CareersPage";

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
    {
      vacancy_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
      title: "People Partner",
      description: "Support hiring conversations and candidate experience.",
      department: "People",
      created_at: "2026-03-11T08:00:00Z",
      updated_at: "2026-03-13T08:30:00Z",
    },
  ],
};

function renderCareersPage(initialEntries = ["/careers"]) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <CareersPage />
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

describe("CareersPage", () => {
  beforeEach(async () => {
    window.localStorage.clear();
    window.history.pushState({}, "", "/careers");
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

  it("renders the job board and links each role to its vacancy page", async () => {
    renderCareersPage();

    expect(await screen.findByRole("heading", { name: /browse open roles and share your cv/i })).toBeDefined();
    expect(await screen.findByText(/backend engineer/i)).toBeDefined();

    const vacancyLink = (await screen.findAllByRole("link", { name: /open role page/i }))[0];
    expect(vacancyLink.getAttribute("href")).toContain(
      "/careers/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    );
  });
});
