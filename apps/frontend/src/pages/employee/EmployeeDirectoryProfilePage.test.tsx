import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import "../../app/i18n";
import { EmployeeDirectoryProfilePage } from "./EmployeeDirectoryProfilePage";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

const EMPLOYEE_ID = "11111111-1111-4111-8111-111111111111";

const PROFILE_PAYLOAD = {
  employee_id: EMPLOYEE_ID,
  full_name: "Ada Lovelace",
  department: "Engineering",
  position_title: "Platform Engineer",
  manager: "Grace Hopper",
  location: "Minsk",
  tenure_in_company: 12,
  subordinates: null,
  phone: "+375291234567",
  email: "ada@example.com",
  birthday_day_month: "03-12",
  avatar: null,
};

const PRIVACY_PAYLOAD = {
  is_phone_visible: true,
  is_email_visible: false,
  is_birthday_visible: false,
};

function renderProfilePage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/employee/directory/${EMPLOYEE_ID}`]}>
        <Routes>
          <Route
            path="/employee/directory/:employeeId"
            element={<EmployeeDirectoryProfilePage />}
          />
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

describe("EmployeeDirectoryProfilePage", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    window.localStorage.clear();
    window.localStorage.setItem("hrm_access_token", "employee-token");
    window.localStorage.setItem("hrm_user_role", "employee");
    fetchMock.mockReset();
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith(`/api/v1/employees/directory/${EMPLOYEE_ID}`)) {
        return jsonResponse(PROFILE_PAYLOAD);
      }
      if (url.endsWith("/api/v1/employees/me/onboarding")) {
        return jsonResponse({
          employee_id: EMPLOYEE_ID,
          first_name: "Ada",
          last_name: "Lovelace",
          email: "ada@example.com",
          location: "Minsk",
          current_title: "Engineer",
          start_date: null,
          offer_terms_summary: null,
          onboarding_id: null,
          onboarding_status: null,
          onboarding_started_at: null,
          tasks: [],
        });
      }
      if (url.endsWith("/api/v1/employees/me/privacy") && init?.method === "PATCH") {
        return jsonResponse({
          ...PRIVACY_PAYLOAD,
          is_email_visible: true,
        });
      }
      if (url.endsWith("/api/v1/employees/me/privacy")) {
        return jsonResponse(PRIVACY_PAYLOAD);
      }
      return jsonResponse({});
    });
  });

  it("updates privacy settings and shows success feedback", async () => {
    renderProfilePage();

    const emailToggle = await screen.findByLabelText(/показывать email/i);
    fireEvent.click(emailToggle);

    expect(await screen.findByText(/видимость обновлена/i)).toBeDefined();
  });

  it("shows client-side validation error for unsupported avatar type", async () => {
    renderProfilePage();

    await screen.findByRole("button", { name: /загрузить аватар/i });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement | null;
    expect(fileInput).not.toBeNull();
    const file = new File(["binary"], "avatar.bmp", { type: "image/bmp" });
    if (fileInput instanceof HTMLInputElement) {
      fireEvent.change(fileInput, { target: { files: [file] } });
    }

    expect(await screen.findByText(/разрешены только jpeg, png или webp/i)).toBeDefined();
  });
});
