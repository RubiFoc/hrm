import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import i18n from "i18next";

import "../../app/i18n";
import { AdminCandidatesPage } from "./AdminCandidatesPage";

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
        <AdminCandidatesPage />
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

describe("AdminCandidatesPage", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(async () => {
    fetchMock.mockReset();
    window.localStorage.clear();
    window.localStorage.setItem("hrm_access_token", "admin-token");
    window.localStorage.setItem("hrm_user_role", "admin");
    await i18n.changeLanguage("ru");
  });

  it("renders list and supports RU/EN localization", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      }),
    );

    renderPage();
    expect(await screen.findByRole("heading", { name: /консоль кандидатов/i })).toBeDefined();

    await i18n.changeLanguage("en");
    expect(await screen.findByRole("heading", { name: /candidate console/i })).toBeDefined();
  });

  it("creates a candidate and refreshes the detail panel", async () => {
    const candidateId = "4a5a66db-0f23-4d72-9d7f-b52f8d118c01";
    const createdCandidate = {
      candidate_id: candidateId,
      owner_subject_id: "owner-1",
      first_name: "Anna",
      last_name: "Ivanova",
      email: "anna@example.com",
      phone: "+375291112233",
      location: "Minsk",
      current_title: "Engineer",
      extra_data: { source: "admin" },
      created_at: "2026-03-19T10:00:00Z",
      updated_at: "2026-03-19T10:01:00Z",
    };
    const listResponse = {
      items: [],
      total: 0,
      limit: 20,
      offset: 0,
    };
    const updatedListResponse = {
      items: [
        {
          ...createdCandidate,
          analysis_ready: true,
          detected_language: "en",
          parsed_at: "2026-03-19T10:02:00Z",
          years_experience: 7,
          skills: ["TypeScript", "React"],
          vacancy_stage: "screening",
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
    };
    let listRequestCount = 0;

    fetchMock.mockImplementation((input, init) => {
      const requestUrl = new URL(String(input), window.location.origin);
      const { pathname } = requestUrl;
      const method = (init?.method ?? "GET").toUpperCase();

      if (pathname === "/api/v1/candidates" && method === "GET") {
        listRequestCount += 1;
        return Promise.resolve(jsonResponse(listRequestCount === 1 ? listResponse : updatedListResponse));
      }
      if (pathname === "/api/v1/candidates" && method === "POST") {
        return Promise.resolve(jsonResponse(createdCandidate));
      }
      if (pathname === `/api/v1/candidates/${candidateId}` && method === "GET") {
        return Promise.resolve(jsonResponse(createdCandidate));
      }
      return Promise.resolve(jsonResponse(listResponse));
    });

    renderPage();
    await screen.findByText(/по текущим фильтрам кандидаты не найдены/i);

    const createHeading = screen.getByRole("heading", { name: /создать кандидата/i });
    const createForm = createHeading.closest("form");
    expect(createForm).not.toBeNull();
    const createFormScope = within(createForm as HTMLFormElement);

    fireEvent.change(createFormScope.getByLabelText(/имя/i), { target: { value: "Anna" } });
    fireEvent.change(createFormScope.getByLabelText(/фамилия/i), { target: { value: "Ivanova" } });
    fireEvent.change(createFormScope.getByLabelText(/email/i), {
      target: { value: "anna@example.com" },
    });
    fireEvent.change(createFormScope.getByLabelText(/локация/i), { target: { value: "Minsk" } });
    fireEvent.change(createFormScope.getByLabelText(/текущая должность/i), {
      target: { value: "Engineer" },
    });
    fireEvent.click(screen.getByRole("button", { name: /создать кандидата/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    const postCall = fetchMock.mock.calls.find((call) => {
      const requestUrl = new URL(String(call[0]), window.location.origin);
      return requestUrl.pathname === "/api/v1/candidates" && ((call[1] as RequestInit)?.method ?? "GET").toUpperCase() === "POST";
    });
    expect(postCall).toBeDefined();
    expect((postCall?.[1] as RequestInit).body).toBe(
      JSON.stringify({
        owner_subject_id: null,
        first_name: "Anna",
        last_name: "Ivanova",
        email: "anna@example.com",
        phone: null,
        location: "Minsk",
        current_title: "Engineer",
        extra_data: {},
      }),
    );

    expect(await screen.findByText(/кандидат успешно создан/i)).toBeDefined();
    expect(await screen.findByText(/выбранный кандидат/i)).toBeDefined();
    expect(await screen.findByText(/TypeScript, React/i)).toBeDefined();
  });
});
