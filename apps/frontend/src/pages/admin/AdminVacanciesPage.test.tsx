import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import i18n from "i18next";

import "../../app/i18n";
import { AdminVacanciesPage } from "./AdminVacanciesPage";

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
        <AdminVacanciesPage />
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

describe("AdminVacanciesPage", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(async () => {
    fetchMock.mockReset();
    await i18n.changeLanguage("ru");
  });

  it("renders list and supports RU/EN localization", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ items: [] }));

    renderPage();
    expect(await screen.findByRole("heading", { name: /консоль вакансий/i })).toBeDefined();

    await i18n.changeLanguage("en");
    expect(await screen.findByRole("heading", { name: /vacancy console/i })).toBeDefined();
  });

  it("creates a vacancy and exposes the pipeline shortcut", async () => {
    const vacancyId = "f760b1a7-4a9d-4a84-8a8a-b3dcf0c5d321";
    const createdVacancy = {
      vacancy_id: vacancyId,
      title: "Backend Engineer",
      description: "Build admin support surfaces.",
      department: "Platform",
      status: "open",
      hiring_manager_staff_id: "9d76c7a3-cc37-4f4a-a564-d0a62ff1d111",
      hiring_manager_login: "manager.one",
      created_at: "2026-03-19T10:00:00Z",
      updated_at: "2026-03-19T10:01:00Z",
    };
    const listResponse = { items: [] };
    const updatedListResponse = { items: [createdVacancy] };
    let listRequestCount = 0;

    fetchMock.mockImplementation((input, init) => {
      const requestUrl = new URL(String(input), window.location.origin);
      const { pathname } = requestUrl;
      const method = (init?.method ?? "GET").toUpperCase();

      if (pathname === "/api/v1/vacancies" && method === "GET") {
        listRequestCount += 1;
        return Promise.resolve(jsonResponse(listRequestCount === 1 ? listResponse : updatedListResponse));
      }
      if (pathname === "/api/v1/vacancies" && method === "POST") {
        return Promise.resolve(jsonResponse(createdVacancy));
      }
      if (pathname === `/api/v1/vacancies/${vacancyId}` && method === "GET") {
        return Promise.resolve(jsonResponse(createdVacancy));
      }
      return Promise.resolve(jsonResponse(listResponse));
    });

    renderPage();
    await screen.findByText(/по текущим фильтрам вакансии не найдены/i);

    const createHeading = screen.getByRole("heading", { name: /создать вакансию/i });
    const createForm = createHeading.closest("form");
    expect(createForm).not.toBeNull();
    const createFormScope = within(createForm as HTMLFormElement);

    fireEvent.change(createFormScope.getByLabelText(/название/i), {
      target: { value: "Backend Engineer" },
    });
    fireEvent.change(createFormScope.getByLabelText(/описание/i), {
      target: { value: "Build admin support surfaces." },
    });
    fireEvent.change(createFormScope.getByLabelText(/отдел/i), {
      target: { value: "Platform" },
    });
    fireEvent.change(createFormScope.getByLabelText(/статус/i), {
      target: { value: "open" },
    });
    fireEvent.change(createFormScope.getByLabelText(/логин hiring-менеджера/i), {
      target: { value: "manager.one" },
    });
    fireEvent.click(screen.getByRole("button", { name: /создать вакансию/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    const postCall = fetchMock.mock.calls.find((call) => {
      const requestUrl = new URL(String(call[0]), window.location.origin);
      return requestUrl.pathname === "/api/v1/vacancies" && ((call[1] as RequestInit)?.method ?? "GET").toUpperCase() === "POST";
    });
    expect(postCall).toBeDefined();
    expect((postCall?.[1] as RequestInit).body).toBe(
      JSON.stringify({
        title: "Backend Engineer",
        description: "Build admin support surfaces.",
        department: "Platform",
        status: "open",
        hiring_manager_login: "manager.one",
      }),
    );

    expect(await screen.findByText(/вакансия успешно создана/i)).toBeDefined();
    expect(await screen.findByRole("link", { name: /открыть pipeline/i })).toBeDefined();
  });
});
