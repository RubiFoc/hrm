import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import i18n from "i18next";

import "../../app/i18n";
import { AdminPipelinePage } from "./AdminPipelinePage";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

function renderPage(initialEntries = ["/admin/pipeline"]) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <AdminPipelinePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function requestUrlFromInput(input: RequestInfo | URL): URL {
  if (input instanceof Request) {
    return new URL(input.url);
  }
  return new URL(String(input), window.location.origin);
}

describe("AdminPipelinePage", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(async () => {
    fetchMock.mockReset();
    await i18n.changeLanguage("ru");
  });

  it("renders pipeline selectors and supports RU/EN localization", async () => {
    fetchMock.mockImplementation((input) => {
      const requestUrl = requestUrlFromInput(input);
      if (requestUrl.pathname === "/api/v1/vacancies") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }
      if (requestUrl.pathname === "/api/v1/candidates") {
        return Promise.resolve(
          jsonResponse({
            items: [],
            total: 0,
            limit: 10,
            offset: 0,
          }),
        );
      }
      if (requestUrl.pathname === "/api/v1/pipeline/transitions") {
        return Promise.resolve(jsonResponse({ items: [] }));
      }
      return Promise.resolve(jsonResponse({ items: [] }));
    });

    renderPage();
    expect(await screen.findByRole("heading", { name: /консоль pipeline/i })).toBeDefined();

    await i18n.changeLanguage("en");
    expect(await screen.findByRole("heading", { name: /pipeline console/i })).toBeDefined();
  });

  it("appends a pipeline transition for the selected vacancy and candidate", async () => {
    const vacancyId = "b1b2b3b4-b5b6-4b7b-8b8c-9d9e9f9a9b9c";
    const candidateId = "a1a2a3a4-a5a6-4a7a-8a8b-9c9d9e9f9a9b";
    const vacancy = {
      vacancy_id: vacancyId,
      title: "Backend Engineer",
      description: "Build admin control plane.",
      department: "Platform",
      status: "open",
      hiring_manager_staff_id: "staff-1",
      hiring_manager_login: "manager.one",
      created_at: "2026-03-19T10:00:00Z",
      updated_at: "2026-03-19T10:00:00Z",
    };
    const candidate = {
      candidate_id: candidateId,
      owner_subject_id: "owner-1",
      first_name: "Anna",
      last_name: "Ivanova",
      email: "anna@example.com",
      phone: "+375291112233",
      location: "Minsk",
      current_title: "Engineer",
      extra_data: {},
      created_at: "2026-03-19T10:00:00Z",
      updated_at: "2026-03-19T10:00:00Z",
      analysis_ready: true,
      detected_language: "en",
      parsed_at: "2026-03-19T10:00:00Z",
      years_experience: 7,
      skills: ["TypeScript", "React"],
      vacancy_stage: null,
    };
    const transition = {
      transition_id: "c1c2c3c4-c5c6-4c7c-8c8d-9d9e9f9a9c9d",
      vacancy_id: vacancyId,
      candidate_id: candidateId,
      from_stage: null,
      to_stage: "applied",
      reason: "Initial triage",
      changed_by_sub: "admin-1",
      changed_by_role: "admin",
      transitioned_at: "2026-03-19T10:05:00Z",
    };
    let transitionsRequestCount = 0;

    fetchMock.mockImplementation((input, init) => {
      const requestUrl = requestUrlFromInput(input);
      const { pathname } = requestUrl;
      const method = (init?.method ?? "GET").toUpperCase();

      if (pathname === "/api/v1/vacancies" && method === "GET") {
        return Promise.resolve(jsonResponse({ items: [vacancy] }));
      }
      if (pathname === "/api/v1/candidates" && method === "GET") {
        return Promise.resolve(
          jsonResponse({
            items: [candidate],
            total: 1,
            limit: 10,
            offset: 0,
          }),
        );
      }
      if (pathname === "/api/v1/pipeline/transitions" && method === "GET") {
        transitionsRequestCount += 1;
        return Promise.resolve(
          jsonResponse({
            items: transitionsRequestCount > 1 ? [transition] : [],
          }),
        );
      }
      if (pathname === "/api/v1/pipeline/transitions" && method === "POST") {
        return Promise.resolve(jsonResponse(transition));
      }
      return Promise.resolve(jsonResponse({ items: [] }));
    });

    renderPage();
    const selectVacancyButton = await screen.findByRole("button", {
      name: /выбрать вакансию/i,
    });
    const selectCandidateButton = await screen.findByRole("button", {
      name: /выбрать кандидата/i,
    });

    fireEvent.click(selectVacancyButton);
    fireEvent.click(selectCandidateButton);

    fireEvent.change(screen.getByLabelText(/причина перехода/i), {
      target: { value: "Initial triage" },
    });
    fireEvent.click(screen.getByRole("button", { name: /добавить переход/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    const postCall = fetchMock.mock.calls.find((call) => {
      const requestUrl = new URL(String(call[0]), window.location.origin);
      return requestUrl.pathname === "/api/v1/pipeline/transitions" && ((call[1] as RequestInit)?.method ?? "GET").toUpperCase() === "POST";
    });
    expect(postCall).toBeDefined();
    expect((postCall?.[1] as RequestInit).body).toBe(
      JSON.stringify({
        vacancy_id: vacancyId,
        candidate_id: candidateId,
        to_stage: "applied",
        reason: "Initial triage",
      }),
    );

    expect(await screen.findByText(/переход pipeline успешно добавлен/i)).toBeDefined();
    expect(await screen.findByText(/Initial triage/i)).toBeDefined();
  });
});
