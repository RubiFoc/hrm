import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import "../app/i18n";
import { HrDashboardPage } from "./HrDashboardPage";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);
const VACANCY_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const CANDIDATE_ID = "11111111-1111-1111-1111-111111111111";
const VACANCY_ITEM = {
  vacancy_id: VACANCY_ID,
  title: "Backend Engineer",
  description: "Build APIs",
  department: "Engineering",
  status: "open",
  created_at: "2026-03-06T10:00:00Z",
  updated_at: "2026-03-06T10:00:00Z",
};
const CANDIDATE_ITEM = {
  candidate_id: CANDIDATE_ID,
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
};
const SUCCESSFUL_MATCH_SCORE = {
  vacancy_id: VACANCY_ID,
  candidate_id: CANDIDATE_ID,
  status: "succeeded",
  score: 91,
  confidence: 0.84,
  summary: "Strong shortlist fit based on Python, APIs, and Docker evidence.",
  matched_requirements: ["Python", "REST APIs", "Docker"],
  missing_requirements: ["Kubernetes"],
  evidence: [
    {
      requirement: "Python",
      snippet: "5 years of Python backend engineering",
      source_field: "skills",
    },
  ],
  scored_at: "2026-03-09T12:00:00Z",
  model_name: "llama3.2",
  model_version: "latest",
};

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

function jsonResponse(payload: unknown, status = 200): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function installHrWorkspaceFetchMock({
  matchScoreGet,
  matchScorePost,
  pipelineItems = [
    {
      transition_id: "99999999-9999-4999-8999-999999999999",
      vacancy_id: VACANCY_ID,
      candidate_id: CANDIDATE_ID,
      from_stage: null,
      to_stage: "applied",
      reason: "public_application",
      changed_by_sub: "public",
      changed_by_role: "public",
      transitioned_at: "2026-03-06T10:00:00Z",
    },
  ],
}: {
  matchScoreGet?: (url: string, init?: RequestInit) => Promise<Response>;
  matchScorePost?: (url: string, init?: RequestInit) => Promise<Response>;
  pipelineItems?: Array<Record<string, unknown>>;
}) {
  fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";

    if (url.includes(`/api/v1/vacancies/${VACANCY_ID}/match-scores/${CANDIDATE_ID}`)) {
      if (method === "GET" && matchScoreGet) {
        return matchScoreGet(url, init);
      }
      return jsonResponse({ detail: "Match score not found" }, 404);
    }
    if (url.endsWith(`/api/v1/vacancies/${VACANCY_ID}/match-scores`)) {
      if (method === "POST" && matchScorePost) {
        return matchScorePost(url, init);
      }
      return jsonResponse({ items: [] });
    }
    if (url.includes("/api/v1/vacancies") && !url.includes("/applications")) {
      return jsonResponse({ items: [VACANCY_ITEM] });
    }
    if (url.includes("/api/v1/candidates")) {
      return jsonResponse({ items: [CANDIDATE_ITEM] });
    }
    if (url.includes("/api/v1/pipeline/transitions?")) {
      return jsonResponse({ items: pipelineItems });
    }
    return Promise.resolve(new Response("not-found", { status: 404 }));
  });
}

async function selectVacancyAndCandidate() {
  fireEvent.click(await screen.findByRole("button", { name: /^выбрать$/i }));
  fireEvent.change(screen.getByRole("combobox", { name: /^кандидат$/i }), {
    target: { value: CANDIDATE_ID },
  });
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

    installHrWorkspaceFetchMock({});

    renderHrDashboardPage();

    await selectVacancyAndCandidate();

    expect(await screen.findByText(/public_application/i)).toBeDefined();
    expect((await screen.findAllByRole("cell", { name: /отклик/i })).length).toBeGreaterThan(0);
  });

  it("renders localized invalid transition error", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "hr");

    installHrWorkspaceFetchMock({ pipelineItems: [] });
    const defaultImplementation = fetchMock.getMockImplementation();
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/v1/pipeline/transitions") && init?.method === "POST") {
        return jsonResponse(
          {
            detail: "Transition from 'applied' to 'offer' is not allowed",
          },
          422,
        );
      }
      return defaultImplementation?.(input, init);
    });

    renderHrDashboardPage();

    await selectVacancyAndCandidate();
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

  it("runs score, polls latest status, and renders confidence and explanation details", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "hr");

    let scoreGetCount = 0;
    installHrWorkspaceFetchMock({
      matchScoreGet: () => {
        scoreGetCount += 1;
        if (scoreGetCount === 1) {
          return jsonResponse({ detail: "Match score not found" }, 404);
        }
        if (scoreGetCount === 2) {
          return jsonResponse({
            ...SUCCESSFUL_MATCH_SCORE,
            status: "queued",
            score: null,
            confidence: null,
            summary: null,
            matched_requirements: [],
            missing_requirements: [],
            evidence: [],
            scored_at: null,
            model_name: null,
            model_version: null,
          });
        }
        return jsonResponse(SUCCESSFUL_MATCH_SCORE);
      },
      matchScorePost: () =>
        jsonResponse({
          vacancy_id: VACANCY_ID,
          candidate_id: CANDIDATE_ID,
          status: "queued",
          score: null,
          confidence: null,
          summary: null,
          matched_requirements: [],
          missing_requirements: [],
          evidence: [],
          scored_at: null,
          model_name: null,
          model_version: null,
        }),
    });

    renderHrDashboardPage();

    await selectVacancyAndCandidate();
    fireEvent.click(screen.getByRole("button", { name: /запустить score/i }));

    expect(await screen.findByText(/в очереди/i)).toBeDefined();
    await waitFor(
      () => {
        expect(screen.getByText("91")).toBeDefined();
        expect(screen.getByText("84%")).toBeDefined();
        expect(
          screen.getByText(/strong shortlist fit based on python, apis, and docker evidence/i),
        ).toBeDefined();
        expect(
          screen.getByText(/python: 5 years of python backend engineering/i),
        ).toBeDefined();
      },
      { timeout: 4000 },
    );
  });

  it("renders failed scoring job state", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "hr");

    installHrWorkspaceFetchMock({
      matchScoreGet: () =>
        jsonResponse({
          vacancy_id: VACANCY_ID,
          candidate_id: CANDIDATE_ID,
          status: "failed",
          score: null,
          confidence: null,
          summary: null,
          matched_requirements: [],
          missing_requirements: [],
          evidence: [],
          scored_at: null,
          model_name: null,
          model_version: null,
        }),
    });

    renderHrDashboardPage();

    await selectVacancyAndCandidate();

    expect(await screen.findByText(/ошибка/i)).toBeDefined();
    expect(
      await screen.findByText(/scoring завершился ошибкой/i),
    ).toBeDefined();
  });

  it("renders localized 409 when cv analysis is not ready for scoring", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "hr");

    installHrWorkspaceFetchMock({
      matchScoreGet: () => jsonResponse({ detail: "Match score not found" }, 404),
      matchScorePost: () => jsonResponse({ detail: "CV analysis is not ready" }, 409),
    });

    renderHrDashboardPage();

    await selectVacancyAndCandidate();
    fireEvent.click(screen.getByRole("button", { name: /запустить score/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/cv analysis ещё не готов/i),
      ).toBeDefined();
    });
  });

  it("renders confidence and explanation for an existing successful score", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "hr");

    installHrWorkspaceFetchMock({
      matchScoreGet: () => jsonResponse(SUCCESSFUL_MATCH_SCORE),
    });

    renderHrDashboardPage();

    await selectVacancyAndCandidate();

    expect(await screen.findByText("84%")).toBeDefined();
    expect(
      screen.getByText(/strong shortlist fit based on python, apis, and docker evidence/i),
    ).toBeDefined();
    expect(screen.getByText(/model: llama3.2 \(latest\)/i)).toBeDefined();
  });
});
