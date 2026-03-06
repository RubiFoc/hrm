import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import "../app/i18n";
import { CandidatePage } from "./CandidatePage";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

function renderCandidatePage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <CandidatePage />
    </QueryClientProvider>,
  );
}

describe("CandidatePage", () => {
  beforeEach(() => {
    fetchMock.mockReset();
  });

  it("renders CV analysis status, language, and evidence snippets", async () => {
    fetchMock.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/cv/parsing-status")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              candidate_id: "11111111-1111-1111-1111-111111111111",
              document_id: "22222222-2222-2222-2222-222222222222",
              job_id: "33333333-3333-3333-3333-333333333333",
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
      if (url.includes("/cv/analysis")) {
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

    renderCandidatePage();

    fireEvent.change(screen.getByLabelText(/id кандидата/i), {
      target: { value: "11111111-1111-1111-1111-111111111111" },
    });
    fireEvent.click(screen.getByRole("button", { name: /загрузить анализ/i }));

    expect(await screen.findByText(/статус парсинга/i)).toBeDefined();
    expect(await screen.findByText(/английский/i)).toBeDefined();
    expect(await screen.findByText("skills.python")).toBeDefined();
    expect(await screen.findByText(/Python experience in backend projects/i)).toBeDefined();
  });
});
