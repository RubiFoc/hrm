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
});
