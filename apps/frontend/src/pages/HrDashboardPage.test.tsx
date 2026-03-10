import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import "../app/i18n";
import type {
  HRInterviewResponse,
  InterviewFeedbackPanelSummaryResponse,
  OfferResponse,
} from "../api";
import { HrDashboardPage } from "./HrDashboardPage";

const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);
const VACANCY_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const CANDIDATE_ID = "11111111-1111-1111-1111-111111111111";
const CURRENT_USER_ID = "33333333-3333-4333-8333-333333333333";
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
const INTERVIEW_ID = "77777777-7777-4777-8777-777777777777";
const BASE_INTERVIEW = {
  interview_id: INTERVIEW_ID,
  vacancy_id: VACANCY_ID,
  candidate_id: CANDIDATE_ID,
  status: "awaiting_candidate_confirmation",
  calendar_sync_status: "synced",
  schedule_version: 1,
  scheduled_start_at: "2026-03-12T07:00:00Z",
  scheduled_end_at: "2026-03-12T08:00:00Z",
  timezone: "Europe/Minsk",
  location_kind: "google_meet",
  location_details: "https://meet.google.com/test-room",
  interviewer_staff_ids: ["33333333-3333-4333-8333-333333333333"],
  candidate_response_status: "pending",
  candidate_response_note: null,
  candidate_token_expires_at: "2026-03-12T20:00:00Z",
  candidate_invite_url: "https://frontend.example/candidate?interviewToken=token-1",
  calendar_event_id: "evt-1",
  last_synced_at: "2026-03-09T12:10:00Z",
  cancelled_by: null,
  cancel_reason_code: null,
  created_at: "2026-03-09T12:00:00Z",
  updated_at: "2026-03-09T12:10:00Z",
};
const BASE_ME = {
  subject_id: CURRENT_USER_ID,
  role: "hr",
  session_id: "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
  access_token_expires_at: 9999999999,
};
const BASE_FEEDBACK_SUMMARY = {
  interview_id: INTERVIEW_ID,
  vacancy_id: VACANCY_ID,
  candidate_id: CANDIDATE_ID,
  schedule_version: 1,
  required_interviewer_ids: [CURRENT_USER_ID],
  submitted_interviewer_ids: [],
  missing_interviewer_ids: [CURRENT_USER_ID],
  required_interviewer_count: 1,
  submitted_count: 0,
  gate_status: "blocked",
  gate_reason_codes: ["interview_feedback_window_not_open"],
  recommendation_distribution: {
    strong_yes: 0,
    yes: 0,
    mixed: 0,
    no: 0,
  },
  average_scores: {
    requirements_match_score: null,
    communication_score: null,
    problem_solving_score: null,
    collaboration_score: null,
  },
  items: [],
};
const BASE_OFFER = {
  offer_id: "99999999-1111-4999-8999-999999999999",
  vacancy_id: VACANCY_ID,
  candidate_id: CANDIDATE_ID,
  status: "draft",
  terms_summary: null,
  proposed_start_date: null,
  expires_at: null,
  note: null,
  sent_at: null,
  sent_by_staff_id: null,
  decision_at: null,
  decision_note: null,
  decision_recorded_by_staff_id: null,
  created_at: "2026-03-10T08:00:00Z",
  updated_at: "2026-03-10T08:00:00Z",
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
  meGet,
  matchScoreGet,
  matchScorePost,
  interviewsGet,
  interviewsCreate,
  feedbackSummaryGet,
  feedbackSubmit,
  interviewReschedule,
  interviewCancel,
  interviewResend,
  offerGet,
  offerPut,
  offerSend,
  offerAccept,
  offerDecline,
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
  meGet?: (url: string, init?: RequestInit) => Promise<Response>;
  matchScoreGet?: (url: string, init?: RequestInit) => Promise<Response>;
  matchScorePost?: (url: string, init?: RequestInit) => Promise<Response>;
  interviewsGet?: (url: string, init?: RequestInit) => Promise<Response>;
  interviewsCreate?: (url: string, init?: RequestInit) => Promise<Response>;
  feedbackSummaryGet?: (url: string, init?: RequestInit) => Promise<Response>;
  feedbackSubmit?: (url: string, init?: RequestInit) => Promise<Response>;
  interviewReschedule?: (url: string, init?: RequestInit) => Promise<Response>;
  interviewCancel?: (url: string, init?: RequestInit) => Promise<Response>;
  interviewResend?: (url: string, init?: RequestInit) => Promise<Response>;
  offerGet?: (url: string, init?: RequestInit) => Promise<Response>;
  offerPut?: (url: string, init?: RequestInit) => Promise<Response>;
  offerSend?: (url: string, init?: RequestInit) => Promise<Response>;
  offerAccept?: (url: string, init?: RequestInit) => Promise<Response>;
  offerDecline?: (url: string, init?: RequestInit) => Promise<Response>;
  pipelineItems?: Array<Record<string, unknown>>;
}) {
  fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";

    if (url.endsWith("/api/v1/auth/me")) {
      if (method === "GET" && meGet) {
        return meGet(url, init);
      }
      return jsonResponse(BASE_ME);
    }
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
    if (url.endsWith(`/api/v1/vacancies/${VACANCY_ID}/interviews/${INTERVIEW_ID}/reschedule`)) {
      if (method === "POST" && interviewReschedule) {
        return interviewReschedule(url, init);
      }
      return jsonResponse(BASE_INTERVIEW);
    }
    if (url.endsWith(`/api/v1/vacancies/${VACANCY_ID}/interviews/${INTERVIEW_ID}/cancel`)) {
      if (method === "POST" && interviewCancel) {
        return interviewCancel(url, init);
      }
      return jsonResponse(BASE_INTERVIEW);
    }
    if (url.endsWith(`/api/v1/vacancies/${VACANCY_ID}/interviews/${INTERVIEW_ID}/resend-invite`)) {
      if (method === "POST" && interviewResend) {
        return interviewResend(url, init);
      }
      return jsonResponse(BASE_INTERVIEW);
    }
    if (url.endsWith(`/api/v1/vacancies/${VACANCY_ID}/interviews/${INTERVIEW_ID}/feedback`)) {
      if (method === "GET" && feedbackSummaryGet) {
        return feedbackSummaryGet(url, init);
      }
      return jsonResponse(BASE_FEEDBACK_SUMMARY);
    }
    if (url.endsWith(`/api/v1/vacancies/${VACANCY_ID}/interviews/${INTERVIEW_ID}/feedback/me`)) {
      if (method === "PUT" && feedbackSubmit) {
        return feedbackSubmit(url, init);
      }
      return jsonResponse({
        feedback_id: "88888888-8888-4888-8888-888888888888",
        interview_id: INTERVIEW_ID,
        schedule_version: 1,
        interviewer_staff_id: CURRENT_USER_ID,
        requirements_match_score: 4,
        communication_score: 4,
        problem_solving_score: 4,
        collaboration_score: 4,
        recommendation: "yes",
        strengths_note: "Clear strengths",
        concerns_note: "No major concerns",
        evidence_note: "Strong examples",
        submitted_at: "2026-03-10T10:00:00Z",
        updated_at: "2026-03-10T10:00:00Z",
      });
    }
    if (url.endsWith(`/api/v1/vacancies/${VACANCY_ID}/offers/${CANDIDATE_ID}`)) {
      if (method === "GET" && offerGet) {
        return offerGet(url, init);
      }
      if (method === "PUT" && offerPut) {
        return offerPut(url, init);
      }
      return jsonResponse({ detail: "offer_stage_not_active" }, 409);
    }
    if (url.endsWith(`/api/v1/vacancies/${VACANCY_ID}/offers/${CANDIDATE_ID}/send`)) {
      if (method === "POST" && offerSend) {
        return offerSend(url, init);
      }
      return jsonResponse({ detail: "offer_stage_not_active" }, 409);
    }
    if (url.endsWith(`/api/v1/vacancies/${VACANCY_ID}/offers/${CANDIDATE_ID}/accept`)) {
      if (method === "POST" && offerAccept) {
        return offerAccept(url, init);
      }
      return jsonResponse({ detail: "offer_stage_not_active" }, 409);
    }
    if (url.endsWith(`/api/v1/vacancies/${VACANCY_ID}/offers/${CANDIDATE_ID}/decline`)) {
      if (method === "POST" && offerDecline) {
        return offerDecline(url, init);
      }
      return jsonResponse({ detail: "offer_stage_not_active" }, 409);
    }
    if (url.includes(`/api/v1/vacancies/${VACANCY_ID}/interviews`)) {
      if (method === "GET" && interviewsGet) {
        return interviewsGet(url, init);
      }
      if (method === "POST" && interviewsCreate) {
        return interviewsCreate(url, init);
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

  it("creates an interview and renders queued then synced state with invite URL", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "hr");

    let interviewGetCount = 0;
    installHrWorkspaceFetchMock({
      interviewsGet: () => {
        interviewGetCount += 1;
        if (interviewGetCount === 1) {
          return jsonResponse({ items: [] });
        }
        if (interviewGetCount === 2) {
          return jsonResponse({
            items: [
              {
                ...BASE_INTERVIEW,
                status: "pending_sync",
                calendar_sync_status: "queued",
                candidate_invite_url: null,
                candidate_token_expires_at: null,
              },
            ],
          });
        }
        return jsonResponse({ items: [BASE_INTERVIEW] });
      },
      interviewsCreate: (_url, init) => {
        expect(init?.method).toBe("POST");
        expect(init?.body).toContain(CANDIDATE_ID);
        return jsonResponse({
          ...BASE_INTERVIEW,
          status: "pending_sync",
          calendar_sync_status: "queued",
          candidate_invite_url: null,
          candidate_token_expires_at: null,
        });
      },
      pipelineItems: [
        {
          transition_id: "99999999-9999-4999-8999-999999999999",
          vacancy_id: VACANCY_ID,
          candidate_id: CANDIDATE_ID,
          from_stage: "screening",
          to_stage: "shortlist",
          reason: "shortlisted",
          changed_by_sub: "hr",
          changed_by_role: "hr",
          transitioned_at: "2026-03-06T10:00:00Z",
        },
      ],
    });

    renderHrDashboardPage();
    await selectVacancyAndCandidate();

    fireEvent.change(screen.getByLabelText(/^начало$/i), {
      target: { value: "2026-03-12T10:00" },
    });
    fireEvent.change(screen.getByLabelText(/^окончание$/i), {
      target: { value: "2026-03-12T11:00" },
    });
    fireEvent.change(screen.getByLabelText(/staff id интервьюеров/i), {
      target: { value: "33333333-3333-4333-8333-333333333333" },
    });
    fireEvent.click(screen.getByRole("button", { name: /создать интервью/i }));

    expect(await screen.findByText(/интервью создано/i)).toBeDefined();
    expect(await screen.findByText(/ожидает синхронизации с календарём/i)).toBeDefined();
    await waitFor(() => {
      expect(screen.getByText(/синхронизировано/i)).toBeDefined();
      expect(
        screen.getByDisplayValue("https://frontend.example/candidate?interviewToken=token-1"),
      ).toBeDefined();
    });
  });

  it("resends invite, reschedules, and cancels an existing interview", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "hr");
    let currentInterview = { ...BASE_INTERVIEW } as HRInterviewResponse;

    installHrWorkspaceFetchMock({
      interviewsGet: () => jsonResponse({ items: [currentInterview] }),
      interviewResend: () => {
        currentInterview = {
          ...currentInterview,
          candidate_invite_url: "https://frontend.example/candidate?interviewToken=token-2",
        };
        return jsonResponse(currentInterview);
      },
      interviewReschedule: () => {
        currentInterview = {
          ...currentInterview,
          status: "pending_sync",
          calendar_sync_status: "queued",
          schedule_version: 2,
          candidate_invite_url: null,
          candidate_token_expires_at: null,
        };
        return jsonResponse(currentInterview);
      },
      interviewCancel: () => {
        currentInterview = {
          ...currentInterview,
          status: "cancelled",
          calendar_sync_status: "queued",
          candidate_invite_url: null,
          candidate_token_expires_at: null,
          cancelled_by: "staff",
          cancel_reason_code: "cancelled_by_staff",
        };
        return jsonResponse(currentInterview);
      },
      pipelineItems: [
        {
          transition_id: "99999999-9999-4999-8999-999999999999",
          vacancy_id: VACANCY_ID,
          candidate_id: CANDIDATE_ID,
          from_stage: "shortlist",
          to_stage: "interview",
          reason: "interview_sync_success",
          changed_by_sub: "system",
          changed_by_role: "system",
          transitioned_at: "2026-03-06T10:00:00Z",
        },
      ],
    });

    renderHrDashboardPage();
    await selectVacancyAndCandidate();
    await screen.findByRole("button", { name: /перенести интервью/i });

    fireEvent.click(screen.getByRole("button", { name: /переотправить приглашение/i }));
    await waitFor(() => {
      expect(screen.getByText(/ссылка приглашения кандидата переиздана/i)).toBeDefined();
    });

    fireEvent.change(screen.getByLabelText(/^начало$/i), {
      target: { value: "2026-03-13T10:00" },
    });
    fireEvent.change(screen.getByLabelText(/^окончание$/i), {
      target: { value: "2026-03-13T11:00" },
    });
    fireEvent.click(screen.getByRole("button", { name: /перенести интервью/i }));
    await waitFor(() => {
      expect(screen.getByText(/интервью перенесено/i)).toBeDefined();
      expect(screen.getByText(/версия расписания: 2/i)).toBeDefined();
    });

    fireEvent.click(screen.getByRole("button", { name: /отменить интервью/i }));
    await waitFor(() => {
      expect(screen.getAllByText(/интервью отменено/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/^отменено$/i)).toBeDefined();
    });
  }, 10000);

  it("renders feedback summary and saves current interviewer feedback", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "hr");

    const pastInterview = {
      ...BASE_INTERVIEW,
      scheduled_start_at: "2026-03-08T07:00:00Z",
      scheduled_end_at: "2026-03-08T08:00:00Z",
    };
    let feedbackSummaryState = {
      ...BASE_FEEDBACK_SUMMARY,
      gate_reason_codes: ["interview_feedback_missing"],
      missing_interviewer_ids: [CURRENT_USER_ID],
      submitted_interviewer_ids: [],
      submitted_count: 0,
      gate_status: "blocked",
    } as InterviewFeedbackPanelSummaryResponse;

    installHrWorkspaceFetchMock({
      interviewsGet: () => jsonResponse({ items: [pastInterview] }),
      feedbackSummaryGet: () => jsonResponse(feedbackSummaryState),
      feedbackSubmit: (_url, init) => {
        expect(init?.method).toBe("PUT");
        expect(init?.body).toContain('"recommendation":"strong_yes"');
        feedbackSummaryState = {
          ...feedbackSummaryState,
          missing_interviewer_ids: [],
          submitted_interviewer_ids: [CURRENT_USER_ID],
          submitted_count: 1,
          gate_status: "passed",
          gate_reason_codes: [],
          recommendation_distribution: {
            strong_yes: 1,
            yes: 0,
            mixed: 0,
            no: 0,
          },
          average_scores: {
            requirements_match_score: 5,
            communication_score: 4,
            problem_solving_score: 4,
            collaboration_score: 5,
          },
          items: [
            {
              feedback_id: "88888888-8888-4888-8888-888888888888",
              interview_id: INTERVIEW_ID,
              schedule_version: 1,
              interviewer_staff_id: CURRENT_USER_ID,
              requirements_match_score: 5,
              communication_score: 4,
              problem_solving_score: 4,
              collaboration_score: 5,
              recommendation: "strong_yes",
              strengths_note: "Strong communication and ownership.",
              concerns_note: "No major concerns.",
              evidence_note: "Detailed architecture answers.",
              submitted_at: "2026-03-10T10:00:00Z",
              updated_at: "2026-03-10T10:00:00Z",
            },
          ],
        };
        return jsonResponse(feedbackSummaryState.items[0]);
      },
      pipelineItems: [
        {
          transition_id: "99999999-9999-4999-8999-999999999999",
          vacancy_id: VACANCY_ID,
          candidate_id: CANDIDATE_ID,
          from_stage: "shortlist",
          to_stage: "interview",
          reason: "interview_sync_success",
          changed_by_sub: "system",
          changed_by_role: "system",
          transitioned_at: "2026-03-06T10:00:00Z",
        },
      ],
    });

    renderHrDashboardPage();
    await selectVacancyAndCandidate();

    expect(await screen.findByText(/feedback интервьюеров/i)).toBeDefined();

    fireEvent.change(screen.getByRole("combobox", { name: /совпадение с требованиями/i }), {
      target: { value: "5" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: /коммуникация/i }), {
      target: { value: "4" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: /решение задач/i }), {
      target: { value: "4" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: /коллаборация/i }), {
      target: { value: "5" },
    });
    fireEvent.change(screen.getByRole("combobox", { name: /^рекомендация$/i }), {
      target: { value: "strong_yes" },
    });
    fireEvent.change(screen.getByLabelText(/сильные стороны/i), {
      target: { value: "Strong communication and ownership." },
    });
    fireEvent.change(screen.getByLabelText(/риски и сомнения/i), {
      target: { value: "No major concerns." },
    });
    fireEvent.change(screen.getByLabelText(/обоснование/i), {
      target: { value: "Detailed architecture answers." },
    });
    fireEvent.click(screen.getByRole("button", { name: /сохранить feedback/i }));

    await waitFor(() => {
      expect(screen.getByText(/feedback по интервью сохранён/i)).toBeDefined();
      expect(screen.getByText(/fairness gate пройден/i)).toBeDefined();
      expect(screen.getAllByText(/strong communication and ownership/i).length).toBeGreaterThan(0);
    });
  }, 10000);

  it("renders localized fairness blocker for interview to offer transition", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "hr");

    const pastInterview = {
      ...BASE_INTERVIEW,
      scheduled_start_at: "2026-03-08T07:00:00Z",
      scheduled_end_at: "2026-03-08T08:00:00Z",
    };

    installHrWorkspaceFetchMock({
      interviewsGet: () => jsonResponse({ items: [pastInterview] }),
      feedbackSummaryGet: () =>
        jsonResponse({
          ...BASE_FEEDBACK_SUMMARY,
          gate_reason_codes: ["interview_feedback_missing"],
          gate_status: "blocked",
          missing_interviewer_ids: [CURRENT_USER_ID],
        }),
      pipelineItems: [
        {
          transition_id: "99999999-9999-4999-8999-999999999999",
          vacancy_id: VACANCY_ID,
          candidate_id: CANDIDATE_ID,
          from_stage: "shortlist",
          to_stage: "interview",
          reason: "interview_sync_success",
          changed_by_sub: "system",
          changed_by_role: "system",
          transitioned_at: "2026-03-06T10:00:00Z",
        },
      ],
    });
    const defaultImplementation = fetchMock.getMockImplementation();
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/v1/pipeline/transitions") && init?.method === "POST") {
        return jsonResponse({ detail: "interview_feedback_missing" }, 409);
      }
      return defaultImplementation?.(input, init);
    });

    renderHrDashboardPage();
    await selectVacancyAndCandidate();

    fireEvent.change(screen.getByRole("combobox", { name: /стадия перехода/i }), {
      target: { value: "offer" },
    });
    expect(
      await screen.findByText(/переход interview -> offer заблокирован/i),
    ).toBeDefined();

    fireEvent.click(screen.getByRole("button", { name: /добавить переход/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/каждый назначенный интервьюер не отправит feedback/i),
      ).toBeDefined();
    });
  });

  it("saves, sends, and accepts an offer from the HR workspace", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "hr");

    let currentOffer = { ...BASE_OFFER } as OfferResponse;
    installHrWorkspaceFetchMock({
      interviewsGet: () => jsonResponse({ items: [] }),
      offerGet: () => jsonResponse(currentOffer),
      offerPut: (_url, init) => {
        const payload = JSON.parse(String(init?.body)) as {
          terms_summary: string;
          proposed_start_date?: string | null;
          expires_at?: string | null;
          note?: string | null;
        };
        currentOffer = {
          ...currentOffer,
          terms_summary: payload.terms_summary,
          proposed_start_date: payload.proposed_start_date ?? null,
          expires_at: payload.expires_at ?? null,
          note: payload.note ?? null,
        };
        return jsonResponse(currentOffer);
      },
      offerSend: () => {
        currentOffer = {
          ...currentOffer,
          status: "sent",
          sent_at: "2026-03-10T09:30:00Z",
          sent_by_staff_id: CURRENT_USER_ID,
        };
        return jsonResponse(currentOffer);
      },
      offerAccept: (_url, init) => {
        const payload = JSON.parse(String(init?.body)) as { note?: string | null };
        currentOffer = {
          ...currentOffer,
          status: "accepted",
          decision_note: payload.note ?? null,
          decision_at: "2026-03-10T10:30:00Z",
          decision_recorded_by_staff_id: CURRENT_USER_ID,
        };
        return jsonResponse(currentOffer);
      },
      pipelineItems: [
        {
          transition_id: "99999999-9999-4999-8999-999999999999",
          vacancy_id: VACANCY_ID,
          candidate_id: CANDIDATE_ID,
          from_stage: "interview",
          to_stage: "offer",
          reason: "ready_for_offer",
          changed_by_sub: "hr",
          changed_by_role: "hr",
          transitioned_at: "2026-03-10T09:00:00Z",
        },
      ],
    });

    renderHrDashboardPage();
    await selectVacancyAndCandidate();
    await screen.findByLabelText(/краткое содержание условий оффера/i);

    fireEvent.change(screen.getByLabelText(/краткое содержание условий оффера/i), {
      target: { value: "Base salary 5000 BYN gross with probation bonus." },
    });
    fireEvent.change(screen.getByLabelText(/предлагаемая дата выхода/i), {
      target: { value: "2026-04-01" },
    });
    fireEvent.change(screen.getByLabelText(/оффер действует до/i), {
      target: { value: "2026-03-20" },
    });
    fireEvent.change(screen.getByLabelText(/внутренняя заметка hr/i), {
      target: { value: "Manual delivery via HR email." },
    });
    fireEvent.click(screen.getByRole("button", { name: /сохранить draft/i }));

    await waitFor(() => {
      expect(screen.getByText(/draft оффера сохранён/i)).toBeDefined();
    });

    fireEvent.click(screen.getByRole("button", { name: /отметить как отправленный/i }));
    await waitFor(() => {
      expect(screen.getByText(/оффер отмечен как отправленный/i)).toBeDefined();
      expect(screen.getByText(/ожидается ответ кандидата/i)).toBeDefined();
    });

    fireEvent.change(screen.getByLabelText(/заметка по решению/i), {
      target: { value: "Candidate confirmed by phone." },
    });
    fireEvent.click(screen.getByRole("button", { name: /отметить как accepted/i }));

    await waitFor(() => {
      expect(screen.getByText(/оффер отмечен как accepted/i)).toBeDefined();
      expect(
        screen.getByText(/теперь pipeline можно перевести в hired/i),
      ).toBeDefined();
    });
  }, 10_000);

  it("renders localized blocker for offer to hired transition before acceptance", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "hr");

    installHrWorkspaceFetchMock({
      interviewsGet: () => jsonResponse({ items: [] }),
      offerGet: () =>
        jsonResponse({
          ...BASE_OFFER,
          status: "sent",
          terms_summary: "Base salary 5000 BYN gross with probation bonus.",
          sent_at: "2026-03-10T09:30:00Z",
          sent_by_staff_id: CURRENT_USER_ID,
        }),
      pipelineItems: [
        {
          transition_id: "99999999-9999-4999-8999-999999999999",
          vacancy_id: VACANCY_ID,
          candidate_id: CANDIDATE_ID,
          from_stage: "interview",
          to_stage: "offer",
          reason: "ready_for_offer",
          changed_by_sub: "hr",
          changed_by_role: "hr",
          transitioned_at: "2026-03-10T09:00:00Z",
        },
      ],
    });
    const defaultImplementation = fetchMock.getMockImplementation();
    fetchMock.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/v1/pipeline/transitions") && init?.method === "POST") {
        const payload = JSON.parse(String(init.body)) as { to_stage?: string };
        if (payload.to_stage === "hired") {
          return jsonResponse({ detail: "offer_not_accepted" }, 409);
        }
      }
      return defaultImplementation?.(input, init);
    });

    renderHrDashboardPage();
    await selectVacancyAndCandidate();
    await screen.findByLabelText(/заметка по решению/i);

    fireEvent.change(screen.getByRole("combobox", { name: /стадия перехода/i }), {
      target: { value: "hired" },
    });
    fireEvent.click(screen.getByRole("button", { name: /добавить переход/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/перед переводом pipeline в hired оффер должен быть отмечен как accepted/i),
      ).toBeDefined();
    });
  });

  it("renders localized interview calendar configuration errors", async () => {
    window.localStorage.setItem("hrm_access_token", "access-token");
    window.localStorage.setItem("hrm_user_role", "hr");

    let createCallCount = 0;
    installHrWorkspaceFetchMock({
      interviewsGet: () => jsonResponse({ items: [] }),
      interviewsCreate: () => {
        createCallCount += 1;
        if (createCallCount === 1) {
          return jsonResponse({ detail: "interviewer_calendar_not_configured" }, 422);
        }
        return jsonResponse({ detail: "calendar_not_configured" }, 503);
      },
      pipelineItems: [
        {
          transition_id: "99999999-9999-4999-8999-999999999999",
          vacancy_id: VACANCY_ID,
          candidate_id: CANDIDATE_ID,
          from_stage: "screening",
          to_stage: "shortlist",
          reason: "shortlisted",
          changed_by_sub: "hr",
          changed_by_role: "hr",
          transitioned_at: "2026-03-06T10:00:00Z",
        },
      ],
    });

    renderHrDashboardPage();
    await selectVacancyAndCandidate();
    await screen.findByText(/интервью пока не назначено/i);

    fireEvent.change(screen.getByLabelText(/^начало$/i), {
      target: { value: "2026-03-12T10:00" },
    });
    fireEvent.change(screen.getByLabelText(/^окончание$/i), {
      target: { value: "2026-03-12T11:00" },
    });
    fireEvent.change(screen.getByLabelText(/staff id интервьюеров/i), {
      target: { value: "33333333-3333-4333-8333-333333333333" },
    });

    fireEvent.click(screen.getByRole("button", { name: /создать интервью/i }));
    await waitFor(() => {
      expect(
        screen
          .getAllByRole("alert")
          .some((item) => /интервьюер|календар/i.test(item.textContent ?? "")),
      ).toBe(true);
    });

    fireEvent.click(screen.getByRole("button", { name: /создать интервью/i }));
    await waitFor(() => {
      expect(
        screen
          .getAllByRole("alert")
          .some((item) => /синхронизация календаря/i.test(item.textContent ?? "")),
      ).toBe(true);
    });
  });
});
