import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import i18n from "i18next";

import "../app/i18n";
import { AdminEmployeeKeysManagementPage } from "./AdminEmployeeKeysManagementPage";

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
      <AdminEmployeeKeysManagementPage />
    </QueryClientProvider>,
  );
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("AdminEmployeeKeysManagementPage", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(async () => {
    fetchMock.mockReset();
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
    expect(await screen.findByRole("heading", { name: /ключи регистрации сотрудников/i })).toBeDefined();

    await i18n.changeLanguage("en");
    expect(await screen.findByRole("heading", { name: /employee registration keys/i })).toBeDefined();
  });

  it("applies search and created-by filters and sends query params", async () => {
    fetchMock
      .mockResolvedValueOnce(
        jsonResponse({
          items: [],
          total: 0,
          limit: 20,
          offset: 0,
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          items: [
            {
              key_id: "52ae0f95-9c60-4a0f-b96c-8631346815f1",
              employee_key: "ad2f171f-2ac0-4417-bf07-df6ae0eb0dd5",
              target_role: "employee",
              status: "active",
              expires_at: "2026-03-12T10:00:00Z",
              used_at: null,
              revoked_at: null,
              revoked_by_staff_id: null,
              created_by_staff_id: "5f4cb725-9eb1-49b4-9ca1-f8b87f3063f8",
              created_at: "2026-03-05T10:00:00Z",
            },
          ],
          total: 1,
          limit: 20,
          offset: 0,
        }),
      );

    renderPage();
    await screen.findByText(/по текущим фильтрам ключи не найдены/i);

    fireEvent.change(screen.getByLabelText(/поиск по key id или employee key/i), {
      target: { value: "ad2f171f" },
    });
    fireEvent.change(screen.getByLabelText(/created by staff id/i), {
      target: { value: "5f4cb725-9eb1-49b4-9ca1-f8b87f3063f8" },
    });
    fireEvent.click(screen.getByRole("button", { name: /применить/i }));

    expect(await screen.findByText("ad2f171f-2ac0-4417-bf07-df6ae0eb0dd5")).toBeDefined();

    const requestUrl = String(fetchMock.mock.calls[1][0]);
    expect(requestUrl).toContain("/api/v1/admin/employee-keys?");
    expect(requestUrl).toContain("search=ad2f171f");
    expect(requestUrl).toContain("created_by_staff_id=5f4cb725-9eb1-49b4-9ca1-f8b87f3063f8");
  });

  it("requests next page with updated offset", async () => {
    fetchMock
      .mockResolvedValueOnce(
        jsonResponse({
          items: [
            {
              key_id: "c4c7678d-41cb-4c9b-b30d-7b8b6fef4fba",
              employee_key: "100d76b8-ae45-4c5a-adf3-9f8f49f14f7e",
              target_role: "employee",
              status: "active",
              expires_at: "2026-03-12T10:00:00Z",
              used_at: null,
              revoked_at: null,
              revoked_by_staff_id: null,
              created_by_staff_id: "5f4cb725-9eb1-49b4-9ca1-f8b87f3063f8",
              created_at: "2026-03-05T10:00:00Z",
            },
          ],
          total: 25,
          limit: 20,
          offset: 0,
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          items: [],
          total: 25,
          limit: 20,
          offset: 20,
        }),
      );

    renderPage();
    await screen.findByText("100d76b8-ae45-4c5a-adf3-9f8f49f14f7e");

    fireEvent.click(screen.getByLabelText(/go to next page/i));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });
    const requestUrl = String(fetchMock.mock.calls[1][0]);
    expect(requestUrl).toContain("offset=20");
    expect(requestUrl).toContain("limit=20");
  });

  it("creates employee key and shows success feedback", async () => {
    fetchMock
      .mockResolvedValueOnce(
        jsonResponse({
          items: [],
          total: 0,
          limit: 20,
          offset: 0,
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          key_id: "f80ceb6a-e1f7-4c36-bbb0-f72eced916ca",
          employee_key: "a1a64374-daf2-43d7-bdc0-5cb4f78e95cb",
          target_role: "employee",
          expires_at: "2026-03-12T10:00:00Z",
          used_at: null,
          created_by_staff_id: "31ce9287-265e-4f91-bf58-8127d23008d2",
          created_at: "2026-03-05T10:00:00Z",
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          items: [
            {
              key_id: "f80ceb6a-e1f7-4c36-bbb0-f72eced916ca",
              employee_key: "a1a64374-daf2-43d7-bdc0-5cb4f78e95cb",
              target_role: "employee",
              status: "active",
              expires_at: "2026-03-12T10:00:00Z",
              used_at: null,
              revoked_at: null,
              revoked_by_staff_id: null,
              created_by_staff_id: "31ce9287-265e-4f91-bf58-8127d23008d2",
              created_at: "2026-03-05T10:00:00Z",
            },
          ],
          total: 1,
          limit: 20,
          offset: 0,
        }),
      );

    renderPage();
    await screen.findByText(/по текущим фильтрам ключи не найдены/i);

    fireEvent.click(screen.getByRole("button", { name: /создать ключ/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(3);
    });

    const postCall = fetchMock.mock.calls[1];
    expect(String(postCall[0])).toContain("/api/v1/admin/employee-keys");
    expect((postCall[1] as RequestInit).method).toBe("POST");
    expect((postCall[1] as RequestInit).body).toBe(
      JSON.stringify({
        target_role: "employee",
        ttl_seconds: 604800,
      }),
    );

    expect(await screen.findByText(/ключ регистрации создан/i)).toBeDefined();
  });

  it("maps revoke reason-code to localized error message", async () => {
    fetchMock
      .mockResolvedValueOnce(
        jsonResponse({
          items: [
            {
              key_id: "f80ceb6a-e1f7-4c36-bbb0-f72eced916ca",
              employee_key: "a1a64374-daf2-43d7-bdc0-5cb4f78e95cb",
              target_role: "employee",
              status: "active",
              expires_at: "2026-03-12T10:00:00Z",
              used_at: null,
              revoked_at: null,
              revoked_by_staff_id: null,
              created_by_staff_id: "31ce9287-265e-4f91-bf58-8127d23008d2",
              created_at: "2026-03-05T10:00:00Z",
            },
          ],
          total: 1,
          limit: 20,
          offset: 0,
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ detail: "key_already_used" }, 409));

    renderPage();
    await screen.findByText("a1a64374-daf2-43d7-bdc0-5cb4f78e95cb");

    fireEvent.click(screen.getByRole("button", { name: /отозвать/i }));

    expect(await screen.findByText(/ключ регистрации уже использован/i)).toBeDefined();
  });
});
