import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import "../app/i18n";
import { HrDashboardPage } from "./HrDashboardPage";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

function renderHrDashboardPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <HrDashboardPage />
    </QueryClientProvider>,
  );
}

describe("HrDashboardPage", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    window.localStorage.clear();
  });

  afterEach(() => {
    cleanup();
  });

  it("loads vacancies and pipeline history for the selected candidate", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "hr");

    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/vacancies") && !url.includes("/applications")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [
                {
                  vacancy_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                  title: "Backend Engineer",
                  description: "Build APIs",
                  department: "Engineering",
                  status: "open",
                  created_at: "2026-03-06T10:00:00Z",
                  updated_at: "2026-03-06T10:00:00Z",
                },
              ],
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      if (url.includes("/api/v1/candidates")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [
                {
                  candidate_id: "11111111-1111-1111-1111-111111111111",
                  owner_subject_id: "public",
                  first_name: "John",
                  last_name: "Doe",
                  email: "john@example.com",
                  phone: "+375291112233",
                  location: "Minsk",
                  current_title: "Engineer",
                  extra_data: {},
                  created_at: "2026-03-06T10:00:00Z",
                  updated_at: "2026-03-06T10:00:00Z",
                },
              ],
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      if (url.includes("/api/v1/pipeline/transitions?")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [
                {
                  transition_id: "99999999-9999-4999-8999-999999999999",
                  vacancy_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                  candidate_id: "11111111-1111-1111-1111-111111111111",
                  from_stage: null,
                  to_stage: "applied",
                  reason: "public_application",
                  changed_by_sub: "public",
                  changed_by_role: "public",
                  transitioned_at: "2026-03-06T10:00:00Z",
                },
              ],
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      return Promise.resolve(new Response("not-found", { status: 404 }));
    });

    renderHrDashboardPage();

    fireEvent.click(await screen.findByRole("button", { name: /^выбрать$/i }));
    fireEvent.change(screen.getByRole("combobox", { name: /^кандидат$/i }), {
      target: { value: "11111111-1111-1111-1111-111111111111" },
    });

    expect(await screen.findByText(/public_application/i)).toBeDefined();
    expect((await screen.findAllByRole("cell", { name: /отклик/i })).length).toBeGreaterThan(0);
  });

  it("renders localized invalid transition error", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "hr");

    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/api/v1/vacancies") && init?.method !== "POST" && init?.method !== "PATCH") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [
                {
                  vacancy_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                  title: "Backend Engineer",
                  description: "Build APIs",
                  department: "Engineering",
                  status: "open",
                  created_at: "2026-03-06T10:00:00Z",
                  updated_at: "2026-03-06T10:00:00Z",
                },
              ],
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      if (url.includes("/api/v1/candidates")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              items: [
                {
                  candidate_id: "11111111-1111-1111-1111-111111111111",
                  owner_subject_id: "public",
                  first_name: "John",
                  last_name: "Doe",
                  email: "john@example.com",
                  phone: "+375291112233",
                  location: "Minsk",
                  current_title: "Engineer",
                  extra_data: {},
                  created_at: "2026-03-06T10:00:00Z",
                  updated_at: "2026-03-06T10:00:00Z",
                },
              ],
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      if (url.includes("/api/v1/pipeline/transitions?")) {
        return Promise.resolve(
          new Response(JSON.stringify({ items: [] }), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      if (url.endsWith("/api/v1/pipeline/transitions") && init?.method === "POST") {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              detail: "Transition from 'applied' to 'offer' is not allowed",
            }),
            {
              status: 422,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      return Promise.resolve(new Response("not-found", { status: 404 }));
    });

    renderHrDashboardPage();

    fireEvent.click(await screen.findByRole("button", { name: /^выбрать$/i }));
    fireEvent.change(screen.getByRole("combobox", { name: /^кандидат$/i }), {
      target: { value: "11111111-1111-1111-1111-111111111111" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: /стадия перехода/i }), {
      target: { value: "offer" },
    });
    fireEvent.click(screen.getByRole("button", { name: /добавить переход/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/запрошенный переход по pipeline недопустим/i),
      ).toBeDefined();
    });
  });
});
