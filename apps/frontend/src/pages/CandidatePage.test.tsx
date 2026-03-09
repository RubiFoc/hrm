import { webcrypto } from "node:crypto";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import "../app/i18n";
import { CandidatePage } from "./CandidatePage";

const fetchMock = vi.fn();
const digestMock = vi.fn(async () => new Uint8Array(32).buffer);
const fileArrayBufferMock = vi.fn(
  async () => new TextEncoder().encode("candidate-cv").buffer,
);
vi.stubGlobal("fetch", fetchMock);
const INTERVIEW_TOKEN = "interview-token-123";
const INTERVIEW_REGISTRATION = {
  interview_id: "77777777-7777-4777-8777-777777777777",
  vacancy_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  vacancy_title: "Backend Engineer",
  status: "awaiting_candidate_confirmation",
  calendar_sync_status: "synced",
  schedule_version: 1,
  scheduled_start_at: "2026-03-12T07:00:00Z",
  scheduled_end_at: "2026-03-12T08:00:00Z",
  timezone: "Europe/Minsk",
  location_kind: "google_meet",
  location_details: "https://meet.google.com/test-room",
  candidate_response_status: "pending",
  candidate_response_note: null,
  candidate_token_expires_at: "2026-03-12T20:00:00Z",
  cancelled_by: null,
  cancel_reason_code: null,
  updated_at: "2026-03-09T10:00:00Z",
};

Object.defineProperty(window, "crypto", {
  value: webcrypto,
  configurable: true,
});

function renderCandidatePage(pathname = "/candidate") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  render(
    <MemoryRouter initialEntries={[pathname]}>
      <QueryClientProvider client={queryClient}>
        <CandidatePage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

function installCandidateInterviewFetchMock({
  getResponse = jsonResponse(INTERVIEW_REGISTRATION),
  confirmResponse = jsonResponse({
    ...INTERVIEW_REGISTRATION,
    status: "confirmed",
    candidate_response_status: "confirmed",
  }),
  rescheduleResponse = jsonResponse({
    ...INTERVIEW_REGISTRATION,
    status: "reschedule_requested",
    candidate_response_status: "reschedule_requested",
    candidate_response_note: "Need a later slot",
  }),
  cancelResponse = jsonResponse({
    ...INTERVIEW_REGISTRATION,
    status: "cancelled",
    candidate_response_status: "declined",
    candidate_response_note: "Cannot attend",
    cancelled_by: "candidate",
    cancel_reason_code: "candidate_declined",
  }),
}: {
  getResponse?: Promise<Response>;
  confirmResponse?: Promise<Response>;
  rescheduleResponse?: Promise<Response>;
  cancelResponse?: Promise<Response>;
} = {}) {
  fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    const encodedToken = encodeURIComponent(INTERVIEW_TOKEN);

    if (url.endsWith(`/api/v1/public/interview-registrations/${encodedToken}`) && method === "GET") {
      return getResponse;
    }
    if (
      url.endsWith(`/api/v1/public/interview-registrations/${encodedToken}/confirm`)
      && method === "POST"
    ) {
      return confirmResponse;
    }
    if (
      url.endsWith(`/api/v1/public/interview-registrations/${encodedToken}/request-reschedule`)
      && method === "POST"
    ) {
      return rescheduleResponse;
    }
    if (
      url.endsWith(`/api/v1/public/interview-registrations/${encodedToken}/cancel`)
      && method === "POST"
    ) {
      return cancelResponse;
    }
    return Promise.resolve(new Response("not-found", { status: 404 }));
  });
}

function jsonResponse(payload: unknown, status = 200): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("CandidatePage", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    digestMock.mockClear();
    fileArrayBufferMock.mockClear();
    window.sessionStorage.clear();
    Object.defineProperty(window, "crypto", {
      value: {
        subtle: {
          digest: digestMock,
        },
      },
      configurable: true,
    });
    Object.defineProperty(File.prototype, "arrayBuffer", {
      value: fileArrayBufferMock,
      configurable: true,
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("submits a public application and renders tracking status plus analysis", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/applications")) {
        expect(init?.method).toBe("POST");
        expect(init?.body).toBeDefined();
        return Promise.resolve(
          new Response(
            JSON.stringify({
              vacancy_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
              candidate_id: "11111111-1111-1111-1111-111111111111",
              document_id: "22222222-2222-2222-2222-222222222222",
              parsing_job_id: "33333333-3333-4333-8333-333333333333",
              transition_id: "44444444-4444-4444-4444-444444444444",
              applied_at: "2026-03-06T10:00:00Z",
            }),
            {
              status: 201,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      if (url.endsWith("/api/v1/public/cv-parsing-jobs/33333333-3333-4333-8333-333333333333")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              candidate_id: "11111111-1111-1111-1111-111111111111",
              document_id: "22222222-2222-2222-2222-222222222222",
              job_id: "33333333-3333-4333-8333-333333333333",
              status: "succeeded",
              attempt_count: 1,
              last_error: null,
              queued_at: "2026-03-06T10:00:00Z",
              started_at: "2026-03-06T10:00:01Z",
              finished_at: "2026-03-06T10:00:03Z",
              updated_at: "2026-03-06T10:00:03Z",
              analysis_ready: true,
              detected_language: "en",
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      if (url.endsWith("/api/v1/public/cv-parsing-jobs/33333333-3333-4333-8333-333333333333/analysis")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              candidate_id: "11111111-1111-1111-1111-111111111111",
              document_id: "22222222-2222-2222-2222-222222222222",
              detected_language: "en",
              parsed_at: "2026-03-06T10:00:03Z",
              parsed_profile: {
                personal: { full_name: "John Doe" },
                skills: ["python"],
              },
              evidence: [
                {
                  field: "skills.python",
                  snippet: "Python experience in backend projects",
                  start_offset: 10,
                  end_offset: 45,
                  page: null,
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

    renderCandidatePage(
      "/candidate?vacancyId=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa&vacancyTitle=Backend%20Engineer",
    );

    fireEvent.change(screen.getByLabelText(/^имя$/i), {
      target: { value: "John" },
    });
    fireEvent.change(screen.getByLabelText(/фамилия/i), {
      target: { value: "Doe" },
    });
    fireEvent.change(screen.getByLabelText(/^email$/i), {
      target: { value: "john@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/телефон/i), {
      target: { value: "+375291112233" },
    });

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement | null;
    expect(fileInput).not.toBeNull();
    fireEvent.change(fileInput!, {
      target: {
        files: [
          new File(["candidate-cv"], "cv.pdf", {
            type: "application/pdf",
          }),
        ],
      },
    });

    const submitButton = screen.getByRole("button", { name: /отправить отклик/i });
    const submitForm = submitButton.closest("form");
    expect(submitForm).not.toBeNull();
    fireEvent.submit(submitForm!);

    expect(
      await screen.findByText(/отклик отправлен|application submitted/i),
    ).toBeDefined();
    expect(await screen.findByText(/статус парсинга/i)).toBeDefined();
    expect(await screen.findByText(/английский/i)).toBeDefined();
    expect(await screen.findByText("skills.python")).toBeDefined();
    expect(await screen.findByText(/Python experience in backend projects/i)).toBeDefined();
    expect(
      await screen.findByText(/candidate id: 11111111-1111-1111-1111-111111111111/i),
    ).toBeDefined();

    await waitFor(() => {
      expect(window.sessionStorage.getItem("hrm_candidate_application_context")).toContain(
        "33333333-3333-4333-8333-333333333333",
      );
    });
  });

  it("renders localized duplicate submission error", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/applications")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              detail: "Duplicate submission detected for this vacancy",
            }),
            {
              status: 409,
              headers: { "Content-Type": "application/json" },
            },
          ),
        );
      }
      return Promise.resolve(new Response("not-found", { status: 404 }));
    });

    renderCandidatePage("/candidate?vacancyId=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa");

    fireEvent.change(screen.getByLabelText(/^имя$/i), {
      target: { value: "John" },
    });
    fireEvent.change(screen.getByLabelText(/фамилия/i), {
      target: { value: "Doe" },
    });
    fireEvent.change(screen.getByLabelText(/^email$/i), {
      target: { value: "john@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/телефон/i), {
      target: { value: "+375291112233" },
    });

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement | null;
    expect(fileInput).not.toBeNull();
    fireEvent.change(fileInput!, {
      target: {
        files: [
          new File(["candidate-cv"], "cv.pdf", {
            type: "application/pdf",
          }),
        ],
      },
    });

    const submitButton = screen.getByRole("button", { name: /отправить отклик/i });
    const submitForm = submitButton.closest("form");
    expect(submitForm).not.toBeNull();
    fireEvent.submit(submitForm!);

    expect(
      await screen.findByText(/уже было отправлено на выбранную вакансию/i),
    ).toBeDefined();
  });

  it("renders localized invalid-link state for mixed vacancy and interview params", async () => {
    renderCandidatePage(
      `/candidate?vacancyId=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa&interviewToken=${INTERVIEW_TOKEN}`,
    );

    expect(
      await screen.findByText(/ссылка некорректна: одновременно переданы параметры вакансии и интервью/i),
    ).toBeDefined();
  });

  it("confirms interview attendance in candidate token mode", async () => {
    installCandidateInterviewFetchMock();

    renderCandidatePage(`/candidate?interviewToken=${INTERVIEW_TOKEN}`);

    expect(await screen.findByText(/регистрация на интервью/i)).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: /подтвердить/i }));

    await waitFor(() => {
      expect(screen.getByText(/участие в интервью подтверждено/i)).toBeDefined();
      expect(screen.getAllByText(/^подтверждено$/i).length).toBeGreaterThan(0);
    });
  });

  it("requests interview reschedule and persists candidate note", async () => {
    installCandidateInterviewFetchMock();

    renderCandidatePage(`/candidate?interviewToken=${INTERVIEW_TOKEN}`);

    await screen.findByText(/регистрация на интервью/i);
    fireEvent.change(screen.getByLabelText(/комментарий/i), {
      target: { value: "Need a later slot" },
    });
    fireEvent.click(screen.getByRole("button", { name: /запросить перенос/i }));

    await waitFor(() => {
      expect(screen.getByText(/запрос на перенос отправлен/i)).toBeDefined();
      expect(screen.getByText(/последний комментарий: need a later slot/i)).toBeDefined();
    });
  });

  it("declines interview invitation in candidate token mode", async () => {
    installCandidateInterviewFetchMock();

    renderCandidatePage(`/candidate?interviewToken=${INTERVIEW_TOKEN}`);

    await screen.findByText(/регистрация на интервью/i);
    fireEvent.change(screen.getByLabelText(/комментарий/i), {
      target: { value: "Cannot attend" },
    });
    fireEvent.click(screen.getByRole("button", { name: /отклонить/i }));

    await waitFor(() => {
      expect(screen.getByText(/приглашение на интервью отклонено/i)).toBeDefined();
      expect(screen.getAllByText(/^отменено$/i).length).toBeGreaterThan(0);
    });
  });

  it.each([
    [404, "interview_registration_not_found", /ссылка на регистрацию интервью не найдена/i],
    [
      409,
      "interview_state_does_not_allow_confirmation",
      /текущее состояние интервью больше не позволяет это действие/i,
    ],
    [410, "interview_registration_token_expired", /срок действия ссылки на регистрацию интервью истёк/i],
    [422, "validation_failed", /данные ответа на интервью не прошли валидацию/i],
  ])(
    "renders localized interview token error for status %s",
    async (statusCode, detail, expectedText) => {
      installCandidateInterviewFetchMock({
        getResponse: jsonResponse({ detail }, statusCode),
      });

      renderCandidatePage(`/candidate?interviewToken=${INTERVIEW_TOKEN}`);

      expect(await screen.findByText(expectedText)).toBeDefined();
    },
  );
});
