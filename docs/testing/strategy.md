# Testing Strategy

## Goals
- Prevent regressions in critical business flows.
- Keep verification reproducible for humans and LLM agents.
- Ensure all backend logic is covered at unit and integration/e2e levels.

## Mandatory Coverage Policy
- Every logic module must have:
  - unit tests for isolated behavior and edge cases;
  - integration/e2e tests for boundary behavior (HTTP/API, storage adapters, external integration seams).
- Changes are not done until required tests are added or updated.

## Test Levels
| Level | Purpose | Minimum Requirement |
| --- | --- | --- |
| Unit | Validate isolated logic | Mandatory for all changed logic |
| Integration/E2E | Validate boundaries and user/system paths | Mandatory for all changed logic and interfaces |
| Infrastructure Smoke | Validate Docker Compose runtime readiness | Mandatory for container/runtime baseline changes (`TASK-12-01`) |
| Operator-Facing AI Smoke | Validate opt-in compose-local Ollama scoring lifecycle | Mandatory when `TASK-12-02` changes the `ai-local` runtime path |

## Test Package Layout (Backend)
- Keep test tree aligned with application package boundaries and split by level.
- Required structure:

```text
apps/backend/tests/
  unit/
    admin/
    auth/
    core/
    rbac/
    ...
  integration/
    admin/
    auth/
    core/
    rbac/
    ...
```

## Integration Harness Stability Rules
- Canonical HTTP integration harness: `pytest-anyio` + `httpx.AsyncClient` + `ASGITransport`.
- Do not use `starlette.testclient.TestClient` in backend integration tests.
- Keep integration runtime pinned to `anyio_backend = "asyncio"` in
  `apps/backend/tests/integration/conftest.py` or module-local fixtures for deterministic in-process
  requests.
- Keep `inline_threadpool_patch` integration-only; it exists to avoid environment-specific deadlocks in `anyio.to_thread` during in-process ASGI runs.
- Integration tests should override external adapters (Redis/object storage/auth context) through FastAPI dependency overrides to keep runs deterministic.

### Mandatory Pre-PR Smoke Gate (Security/Auth Integration)
- Run before PR-B/PR-C/PR-D style contract-sensitive backend changes:
  - `uv run --project apps/backend pytest -q apps/backend/tests/integration/security/test_audit_enforcement.py apps/backend/tests/integration/auth/test_auth_stack.py`
- The gate must pass in two consecutive runs when harness-level changes are introduced.

## OpenAPI Freeze Discipline
- Frozen backend contract source of truth: `docs/api/openapi.frozen.json`.
- Regeneration command:
  - `./scripts/generate-openapi-frozen.sh`
- Verification command:
  - `./scripts/check-openapi-freeze.sh`
- CI must fail when runtime OpenAPI differs from frozen spec.
- Frontend typed contract generation must run from frozen spec:
  - `npm --prefix apps/frontend run api:types:generate`

## Change-Based Verification Matrix
| Change Type | Required Checks |
| --- | --- |
| Bugfix | Unit regression + integration regression + adjacent behavior check |
| New feature | Unit happy/negative + integration contract path |
| Refactor | Unit non-regression + integration non-regression |
| Runtime/Platform | Compose config validation + deterministic smoke cycle (`up -> smoke`, `down -> up -> smoke`) |

## Phase 1 Baseline Merge Gate
- Use this exact acceptance set before merging the current local baseline slice:
  - `./scripts/check-docs-structure.sh`
  - `./scripts/check-openapi-freeze.sh`
  - `npm --prefix apps/frontend run api:types:check`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test -- --run`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q apps/backend/tests/integration/candidates/test_candidate_api.py apps/backend/tests/integration/candidates/test_cv_parsing_jobs.py apps/backend/tests/integration/vacancies/test_vacancy_pipeline_api.py`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest apps/backend/tests/unit/test_cors.py apps/backend/tests/unit/auth/test_auth_settings.py -q`
  - `docker compose up -d --build`
  - `./scripts/smoke-compose.sh`
- This gate applies to the cohesive baseline PR only; do not add more feature scope before it lands.

## Infrastructure Smoke Baseline (`TASK-12-01`)
- Baseline acceptance commands:
  - `docker compose config`
  - `docker compose up -d --build`
  - `./scripts/smoke-compose.sh`
  - `./scripts/check-docs-structure.sh`
- Canonical smoke command: `./scripts/smoke-compose.sh`.
- For docs/tracker-only normalization of `TASK-12-01`, this acceptance set is sufficient; do not expand to OpenAPI, frontend, or backend test suites unless runtime, API, or route behavior changed.
- The smoke script must verify:
  - compose service status and health for `backend`, `postgres`, `redis`, `minio`;
  - compose runtime state for `frontend` and `backend-worker`;
  - compose bootstrap prerequisites (`postgres-init`, `backend-migrate`, `minio-init`) complete successfully before API checks;
  - backend `GET /health`;
  - frontend HTTP response;
  - MinIO live health endpoint;
  - backend auth login response contract.
  - headless Chrome browser auth path `/login -> login -> me -> logout -> /login`;
  - browser auth requests use `VITE_API_BASE_URL` backend origin rather than relative frontend origin;
  - browser-triggered CORS preflight succeeds for auth endpoints.
  - staff API creates one deterministic open vacancy fixture for the public browser scenario;
  - headless Chrome public candidate path `/candidate?vacancyId=...&vacancyTitle=... -> POST /api/v1/vacancies/{vacancy_id}/applications -> GET /api/v1/public/cv-parsing-jobs/{job_id} -> optional GET /analysis`;
  - browser public candidate requests use `VITE_API_BASE_URL` backend origin rather than relative frontend origin;
  - smoke passes when the public tracking status reaches at least `queued`/`running`; `analysis_ready=true` is preferred but not mandatory for compose success.
  - Google Calendar and Ollama integrations are intentionally excluded from compose smoke; their reachability is not required for local compose baseline acceptance.

## Optional AI-Local Compose Verification (`TASK-12-02`)
- Canonical self-contained runtime command:
  `OLLAMA_BASE_URL=http://ollama:11434 docker compose --profile ai-local up -d --build`
- Operator-facing verification command:
  `./scripts/smoke-scoring-compose.sh`
- Required supporting checks when `ai-local` runtime behavior changes:
  - `docker compose config`
  - `uv run --project apps/backend ruff check .`
  - `uv run --project apps/backend pytest -q tests/unit/scoring tests/integration/scoring/test_match_scoring_api.py`
  - `./scripts/check-docs-structure.sh`
- Verification scope for `./scripts/smoke-scoring-compose.sh`:
  - `ollama` is `healthy` and `ollama-init` completes successfully;
  - `backend` and `backend-worker` both see `OLLAMA_BASE_URL=http://ollama:11434`;
  - one real vacancy/candidate/CV path reaches `analysis_ready=true`;
  - real scoring runs through the existing API and reaches canonical lifecycle states;
  - final score payload contains canonical keys without asserting specific score values.
- Acceptance rules:
  - Keep `./scripts/smoke-compose.sh` unchanged as the mandatory baseline smoke.
  - Do not add `./scripts/smoke-scoring-compose.sh` to required CI or browser smoke jobs.
  - Keep scoring/public API routes and payload contracts unchanged while expanding only runtime-level verification.

## Evidence Format
- Command
- Result (pass/fail)
- Artifact link/path (if available)

## Security Foundation Verification (TASK-01-03, TASK-01-04)

| Capability | Unit Coverage | Integration Coverage | Required Evidence |
| --- | --- | --- | --- |
| Centralized policy evaluator | `tests/unit/rbac/test_rbac.py` (`evaluate_permission`, background deny path) | API allow/deny in `tests/integration/security/test_audit_enforcement.py` | `uv run --project apps/backend pytest -q` |
| API and background enforcement parity | `tests/unit/rbac/test_rbac.py` | `test_api_permission_decisions_are_audited`, `test_background_enforcement_writes_job_audit_event` | Audit records with `source=api` and `source=job` |
| Immutable audit storage writes | Audit service and payload validation via unit imports | `tests/integration/security/test_audit_enforcement.py` | Alembic migration + inserted `audit_events` rows |
| Auth sensitive audit hooks | N/A | `test_auth_login_is_audited` (+ auth regression suite) | `auth.login` audit event with `correlation_id` |

## Staff Auth Extension Verification

| Capability | Unit Coverage | Integration Coverage | Required Evidence |
| --- | --- | --- | --- |
| Password policy and hashing (`argon2`) | `tests/unit/auth/*` | `tests/integration/auth/test_auth_stack.py` | `register/login` happy and negative scenarios |
| Employee key lifecycle (`valid/expired/used/revoked`) | `tests/unit/auth/*` | `tests/integration/auth/test_auth_stack.py` | `422` on invalid key paths |
| UUID claims and token contract | `tests/unit/auth/test_auth_services.py` | auth integration suite | `sub/sid/jti` are UUID-backed |
| Login contract (`identifier + password` only) | `tests/unit/auth/test_auth_services.py` | `tests/integration/security/test_audit_enforcement.py` (`test_auth_login_is_audited`) | Login accepts canonical identifier/password payload |
| Swagger bearer security scheme | N/A | OpenAPI contract check in auth integration suite | Swagger UI contains `Authorize` flow |
| Admin APIs and audit hooks | `tests/unit/rbac/test_rbac.py` | `tests/integration/security/test_audit_enforcement.py` | `admin.staff:create` and `admin.employee_key:create` success/failure events |

## Recruitment Domain Verification (TASK-03-01, TASK-03-02, TASK-02-01, TASK-02-02, TASK-03-03, TASK-03-04)

| Capability | Unit Coverage | Integration Coverage | Required Evidence |
| --- | --- | --- | --- |
| Candidate profile schema and ownership guards | `tests/unit/candidates/test_cv_validation.py` + role checks in `tests/unit/rbac/test_rbac.py` | `tests/integration/candidates/test_candidate_api.py` | `uv run --project apps/backend pytest -q` |
| UUID boundary validation for candidate/vacancy/pipeline contracts | Candidate/vacancy schema parsing via unit-level model validation | `tests/integration/candidates/test_candidate_api.py` + `tests/integration/vacancies/test_vacancy_pipeline_api.py` (invalid UUID -> `422`) | OpenAPI IDs expose `format: uuid` and boundary negatives are covered |
| CV upload validation (mime/size/checksum) | `tests/unit/candidates/test_cv_validation.py` | `test_cv_upload_download_status_and_validation_failures` | Validation negative paths return `415/422/413` |
| Public vacancy apply flow (anonymous) | `tests/unit/vacancies/test_pipeline_validator.py` + candidate validation units | `tests/integration/vacancies/test_vacancy_pipeline_api.py` | Apply creates candidate/doc/transition/parsing job and returns `parsing_job_id` for browser tracking |
| Vacancy lifecycle and canonical pipeline transitions | `tests/unit/vacancies/test_pipeline_validator.py` | `tests/integration/vacancies/test_vacancy_pipeline_api.py` | Valid chain passes, invalid chain returns `422`, and ordered history read returns append-only timeline |
| Async CV parsing lifecycle and retry-safe behavior (Celery executor) | `tests/unit/candidates/test_cv_parsing_worker.py` | `tests/integration/candidates/test_cv_parsing_jobs.py` | `queued/running/succeeded/failed` with bounded retries and public tracking-by-job-id contract |
| Native PDF/DOCX text extraction before normalization (`TASK-03-07`) | `tests/unit/candidates/test_cv_text_extraction.py` + `tests/unit/candidates/test_cv_parsing_normalization.py` | `tests/integration/candidates/test_cv_parsing_jobs.py` + `tests/integration/scoring/test_match_scoring_api.py` | Real PDF/DOCX fixtures are extracted before normalization, broken/empty documents fail closed, and scoring preconditions stay unchanged |
| Profession-agnostic parsed-profile enrichment (`TASK-03-08`) | `tests/unit/candidates/test_cv_profile_enrichment.py` + `tests/unit/candidates/test_cv_parsing_normalization.py` | `tests/integration/candidates/test_cv_parsing_jobs.py` + `tests/integration/scoring/test_match_scoring_api.py` | Parsed CV profile includes workplace history with held positions, education, normalized titles/dates, generic skills, indexed evidence, and scoring stays compatible with the richer payload |
| Candidate search/filter list contract (`TASK-03-04`) | `tests/unit/candidates/test_candidate_search.py` | `tests/integration/candidates/test_candidate_api.py` | `GET /api/v1/candidates` supports recruiter-facing search, `analysis_ready`, skill/experience filters, pagination, vacancy-context latest stage enrichment, `in_pipeline_only`, and `422` for vacancy-scoped filters without `vacancy_id` |
| RU/EN CV normalization and language detection (`TASK-03-05`) | `tests/unit/candidates/test_cv_parsing_normalization.py` | `tests/integration/candidates/test_cv_parsing_jobs.py` | `detected_language` and canonical profile fields are persisted after worker success |
| Evidence traceability + analysis read contract (`TASK-03-06`) | `tests/unit/candidates/test_cv_parsing_normalization.py` (field-level evidence snippets/offsets) | `tests/integration/candidates/test_candidate_api.py` + `tests/integration/candidates/test_cv_parsing_jobs.py` | `GET /api/v1/candidates/{candidate_id}/cv/analysis` and `GET /api/v1/public/cv-parsing-jobs/{job_id}/analysis` return structured profile + evidence; pre-ready path returns `409` |
| RBAC + audit coverage for recruitment endpoints | `tests/unit/rbac/test_rbac.py` | `tests/integration/security/test_audit_enforcement.py` + recruitment integration suites | `allowed/denied/success/failure` audit records in `audit_events` |

## Reporting KPI Snapshot Verification (TASK-10-01)

| Capability | Unit Coverage | Integration Coverage | Required Evidence |
| --- | --- | --- | --- |
| KPI aggregation per source table | `tests/unit/reporting/test_kpi_snapshot_service.py` | `tests/integration/reporting/test_kpi_snapshot_api.py` | `uv run --project apps/backend pytest -q` |
| Zero-fill semantics + idempotent rebuild | `tests/unit/reporting/test_kpi_snapshot_service.py` | `tests/integration/reporting/test_kpi_snapshot_api.py` | snapshot rows remain deterministic across rebuilds |
| Read API returns empty payload when snapshot is missing | N/A | `tests/integration/reporting/test_kpi_snapshot_api.py` | `metrics=[]` for missing months |
| RBAC fail-closed access for KPI endpoints | N/A | `tests/integration/reporting/test_kpi_snapshot_api.py` | `403` for non-admin roles |

## Frontend Login UX Verification (TASK-11-13)

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Typed API client honors `VITE_API_BASE_URL` and trims trailing slash | `apps/frontend/src/api/typedClient.test.ts` | N/A | browser auth requests target backend origin instead of relative frontend origin |
| Session storage contract (`access/refresh/role`) and admin-guard compatibility | `apps/frontend/src/app/auth/session.test.ts` | N/A | write/read/clear behavior and invalid role handling |
| Auth API client request shape and `ApiError` mapping | `apps/frontend/src/api/auth.test.ts` | N/A | login/me/logout request contract and `401/422/http_*` handling |
| Login page submit flow (`login -> me -> redirect`) | `apps/frontend/src/pages/LoginPage.test.tsx` | `./scripts/smoke-compose.sh` | session is persisted and redirect follows resolved role |
| Login error states (`401`, `422`, generic) with RU/EN-readable messaging | `apps/frontend/src/pages/LoginPage.test.tsx` | Manual smoke on `/login` with locale toggle | localized error messaging for all required states |
| Router behavior for `/login` and pre-authenticated bootstrap redirect | `apps/frontend/src/app/router.auth.test.tsx` | `./scripts/smoke-compose.sh` | login route render, authenticated redirect, broken session cleanup |
| Admin guard non-regression | `apps/frontend/src/app/router.admin.test.tsx` | `./scripts/smoke-compose.sh` | unauthorized/forbidden redirects continue to work unchanged |
| Browser login/logout roundtrip against compose stack | N/A | `scripts/browser_auth_smoke.py` via `./scripts/smoke-compose.sh` and CI `browser-smoke` job | browser reaches `/admin`, persists session, calls backend auth origin, logs out, and returns to `/login` |
| Backend CORS preflight allows local Vite dev origin | `apps/backend/tests/unit/test_cors.py` + `apps/backend/tests/unit/auth/test_auth_settings.py` | `./scripts/smoke-compose.sh` | `OPTIONS /api/v1/auth/login` returns `200` with expected `Access-Control-Allow-*` headers |

## Frontend Candidate Workspace Verification (`TASK-11-06`, `TASK-11-09`, `TASK-11-11`)

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Deep-link candidate route contract (`/candidate?vacancyId=...&vacancyTitle=...`) and diagnostic fallback | `apps/frontend/src/pages/CandidatePage.test.tsx` | `./scripts/smoke-compose.sh` | candidate page accepts deep link, falls back to manual vacancy ID only when query param is absent |
| Browser SHA-256 checksum + multipart public apply submission | `apps/frontend/src/pages/CandidatePage.test.tsx` + `apps/frontend/src/api/typedClient.test.ts` | `./scripts/smoke-compose.sh` | browser submit uses a real PDF fixture, hits `POST /api/v1/vacancies/{vacancy_id}/applications`, and persists returned tracking context |
| Session storage tracking contract (`hrm_candidate_application_context`) | `apps/frontend/src/pages/CandidatePage.test.tsx` | `./scripts/smoke-compose.sh` | stored payload contains `vacancyId`, `candidateId`, and `parsingJobId` |
| Public tracking and analysis polling by `parsing_job_id` | `apps/frontend/src/pages/CandidatePage.test.tsx` | `./scripts/smoke-compose.sh` | browser reaches at least `queued/running`; analysis/evidence render when ready |
| Localized candidate apply/tracking errors (`409`, `429`, `422`, generic) | `apps/frontend/src/pages/CandidatePage.test.tsx` | manual smoke or compose browser smoke with fixture variations | localized RU/EN mapping for duplicate/cooldown/validation/network failures |
| Browser origin correctness for public candidate requests | N/A | `scripts/browser_candidate_apply_smoke.py` via `./scripts/smoke-compose.sh` and CI `browser-smoke` job | apply/tracking requests target backend origin instead of relative frontend origin |

## Frontend HR Workspace Verification (`TASK-11-05`, `TASK-11-09`)

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Vacancy list/create/edit UI on `/` | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | `./scripts/smoke-compose.sh` creates vacancy through staff API for downstream browser use | staff user can create and update vacancy through typed API wrappers |
| Server-filtered candidate selector, apply/reset filters, and pagination on `/` (`TASK-03-04`) | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | backend integration: `apps/backend/tests/integration/candidates/test_candidate_api.py` | HR candidate selector uses server query params (`search`, `analysis_ready`, vacancy-scoped filters, `limit/offset`) and preserves selected-candidate context across pagination |
| Candidate selection and pipeline transition append | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | backend integration: `apps/backend/tests/integration/vacancies/test_vacancy_pipeline_api.py` | valid transition appends and invalid transition returns localized `422` |
| Ordered transition history/timeline render | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | backend integration: `apps/backend/tests/integration/vacancies/test_vacancy_pipeline_api.py` | timeline reflects append-only transition history for selected vacancy + candidate |
| Offer lifecycle block on `/` | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | backend offer/pipeline integration below | HR can save draft, mark sent, record accepted/declined, and see localized blockers in the existing workspace |
| Localized HR workspace errors (`403`, `404`, `422`, generic) | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | manual role smoke with expired/forbidden session variants | recruiter-facing failures remain readable in RU/EN |

## Scoring and Shortlist Review Verification (`TASK-04-01/02/03`, `TASK-04-06`, `TASK-11-07`)

### Backend
| Capability | Unit Coverage | Integration Coverage | Required Evidence |
| --- | --- | --- | --- |
| Ollama adapter mapping and score schema validation | `apps/backend/tests/unit/scoring/test_ollama_adapter.py` | N/A | model response mapping is deterministic and score payload validates against schema |
| Worker/job state transitions and retry behavior | `apps/backend/tests/unit/scoring/test_match_scoring_worker.py` | `apps/backend/tests/integration/scoring/test_match_scoring_api.py` | `queued/running/succeeded/failed` lifecycle is persisted correctly |
| Prompt compatibility with enriched parsed CV profile | `apps/backend/tests/unit/scoring/test_prompt.py` | `apps/backend/tests/integration/scoring/test_match_scoring_api.py` | scoring prompt/build flow stays stable when parsed CV JSON includes workplaces, education, titles, dates, and generic skills |
| Reject scoring when parsed CV analysis is not ready | N/A | `apps/backend/tests/integration/scoring/test_match_scoring_api.py` | `POST /api/v1/vacancies/{vacancy_id}/match-scores` returns `409` without silent fallback |
| Score payload shape and evidence propagation | `apps/backend/tests/unit/scoring/test_ollama_adapter.py` | `apps/backend/tests/integration/scoring/test_match_scoring_api.py` | latest score response includes `score`, `confidence`, `summary`, requirements, evidence, model metadata, and `scored_at` |
| Low-confidence fallback policy and threshold boundary (`TASK-04-04`) | `apps/backend/tests/unit/scoring/test_manual_review_policy.py` | `apps/backend/tests/integration/scoring/test_match_scoring_api.py` | succeeded scores below threshold return `requires_manual_review=true`, `manual_review_reason="low_confidence"`, and echoed `confidence_threshold`, while `confidence == threshold`, non-succeeded states, and missing confidence do not fallback |
| Quality harness metrics, dataset validation, and deterministic reporting (`TASK-04-06`) | `apps/backend/tests/unit/scoring/test_quality_metrics.py` + `apps/backend/tests/unit/scoring/test_quality_dataset.py` + `apps/backend/tests/unit/scoring/test_quality_runner.py` | `apps/backend/tests/integration/scoring/test_quality_harness_cli.py` | fixture-mode CLI validates dataset shape, computes `precision`/`recall` + `NDCG`/`MRR`, emits machine-readable `ranking_metrics` / `requirement_metrics` / `paraphrase_robustness`, and keeps optional Ollama mode outside the required verification path |

### Frontend
| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Run score -> polling -> success render | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | backend integration above | shortlist review block renders state transitions and final score card |
| Failed scoring job render | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | backend integration above | failed state is visible and recoverable in UI |
| Localized `409` when CV analysis is not ready | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | backend integration above | RU/EN-readable not-ready error is rendered |
| Confidence/explanation rendering | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | backend integration above | confidence, summary, matched requirements, missing requirements, and evidence sections are rendered |
| Low-confidence manual-review warning (`TASK-04-04`) | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | backend integration above | localized RU/EN warning renders for low-confidence succeeded scores without hiding score cards, while high-confidence responses do not show the warning |

### Acceptance Rules
- Freeze OpenAPI and update generated frontend types in the same change.
- Keep the current compose smoke green.
- Do not regress auth or CORS behavior.
- Keep scoring verification at unit/integration level; do not extend compose browser smoke to scoring until runtime nondeterminism is addressed.
- Use `./scripts/smoke-scoring-compose.sh` only as an opt-in operator/runtime verification for the compose-local Ollama profile.
- Shortlist review must work against the real backend scoring contract, not mock-only placeholder data.
- Required local quality-harness verification command:
  `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend python -m hrm_backend.scoring.cli.quality_harness --dataset tests/fixtures/scoring_quality/baseline.json --mode fixture --format json`
- Optional local real-model follow-up for the same harness:
  rerun the same command with `--mode ollama`.
- Keep the quality harness outside runtime request handling and public scoring contracts; do not
  regenerate OpenAPI or frontend types unless a separate change modifies the public API.

## Interview Scheduling and Candidate Registration Verification (`TASK-11-08`, `TASK-05-01`, `TASK-05-02`)

Implementation source of truth:
- `docs/project/interview-planning-pass.md`

Current implementation coverage must stay green at minimum:

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Interview lifecycle validation (`pending_sync`, `awaiting_candidate_confirmation`, `confirmed`, `reschedule_requested`, `cancelled`) | `apps/backend/tests/unit/interviews/test_lifecycle.py` | `apps/backend/tests/integration/interviews/test_interview_api.py` | invalid transitions return `409`; terminal interviews cannot be mutated |
| Calendar sync lifecycle (`queued`, `running`, `synced`, `conflict`, `failed`) | `apps/backend/tests/unit/interviews/test_google_calendar_adapter.py` | `apps/backend/tests/integration/interviews/test_interview_api.py` | sync result persists correct interview and calendar statuses |
| One-active-interview rule per `vacancy_id + candidate_id` | `apps/backend/tests/unit/interviews/test_lifecycle.py` | `apps/backend/tests/integration/interviews/test_interview_api.py` | duplicate active interview returns `409` |
| Candidate invitation token hashing, expiry, and schedule-version invalidation | `apps/backend/tests/unit/interviews/test_token_manager.py` | `apps/backend/tests/integration/interviews/test_interview_api.py` | revoked/rescheduled tokens return `404`; expired token returns `410` |
| Candidate public actions (`confirm`, `request-reschedule`, `cancel`) | `apps/backend/tests/unit/interviews/test_lifecycle.py` + `apps/backend/tests/unit/interviews/test_token_manager.py` | `apps/backend/tests/integration/interviews/test_interview_api.py` | token-bound actions update state without candidate auth |
| HR route integration on `/` | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | backend interview integration suite | create/reschedule/cancel and sync-state render are localized and stable |
| Candidate route-mode integration on `/candidate?interviewToken=...` | `apps/frontend/src/pages/CandidatePage.test.tsx` | backend interview integration suite | candidate interview mode renders localized `404/409/410/422` errors and rejects mixed route params |

Operational assumptions for the current interview slice:
- Freeze OpenAPI and generated frontend types in the same change.
- Keep candidate transport anonymous and token-based.
- Do not add candidate auth, Vite proxy rewrites, or new CORS behavior.
- Free Google Calendar mode uses a service-account JSON key and calendars manually shared with that service account; missing calendar mapping returns `422 interviewer_calendar_not_configured`, while missing runtime calendar configuration returns `503 calendar_not_configured`.
- Keep compose smoke green without adding nondeterministic Google Calendar browser automation.

## Structured Interview Feedback and Fairness Verification (`TASK-05-03`, `TASK-05-04`)

Implementation source of truth:
- `docs/project/interview-feedback-fairness-pass.md`

Current implementation coverage includes at minimum:

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Feedback payload validation (score range, mandatory notes, recommendation enum) | `apps/backend/tests/unit/interviews/test_feedback.py` | `apps/backend/tests/integration/interviews/test_interview_api.py` | valid interviewer payload persists current-version feedback; invalid state rows remain blocked by gate logic |
| Assigned-interviewer-only submission rule | `apps/backend/tests/unit/interviews/test_feedback.py` | `apps/backend/tests/integration/interviews/test_interview_api.py` | non-interviewer submit returns `403`; interviewer can create/update only their own row |
| Reschedule invalidates old feedback for gate purposes | `apps/backend/tests/unit/interviews/test_feedback.py` | `apps/backend/tests/integration/interviews/test_interview_api.py` | previous `schedule_version` feedback is readable as history but blocks `interview -> offer` |
| Fairness gate on existing `interview -> offer` transition | `apps/backend/tests/unit/interviews/test_feedback.py` | `apps/backend/tests/integration/vacancies/test_vacancy_pipeline_api.py` | `409` detail codes for `interview_feedback_window_not_open`, `interview_feedback_missing`, `interview_feedback_incomplete`, and `interview_feedback_stale` |
| Successful `interview -> offer` after complete current-version panel feedback | N/A | pipeline transition integration suite | transition succeeds without adding a new route or pipeline stage |
| HR feedback UX on `/` | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | backend integration above | summary, current-user form, and localized fairness blocker messages render correctly |

Acceptance rules for the implementation slice:
- Freeze OpenAPI and update generated frontend types in the same change.
- Keep auth, CORS, route topology, and anonymous candidate transport unchanged.

## Hire Conversion and Employee Handoff Verification (`TASK-06-02`)

Current implementation coverage includes at minimum:

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Hire-conversion snapshot builder and accepted-offer invariant | `apps/backend/tests/unit/employee/test_hire_conversion_service.py` | N/A | candidate and accepted-offer snapshots are frozen deterministically; non-accepted offers are rejected before persistence |
| Atomic `offer -> hired` dual write (`pipeline_transitions` + `hire_conversions`) | `apps/backend/tests/unit/vacancies/test_hire_conversion_atomicity.py` | `apps/backend/tests/integration/vacancies/test_vacancy_pipeline_api.py` | no partial `hired` transition persists when handoff creation fails; successful `hired` creates one durable handoff row |
| Persisted handoff contents (`offer_id`, `hired_transition_id`, snapshots, `status=ready`) | covered by service snapshot unit test above | `apps/backend/tests/integration/vacancies/test_vacancy_pipeline_api.py` | durable row stores the expected candidate and accepted-offer payloads for employee bootstrap |
| Canonical non-regression after hire | existing vacancy pipeline validator coverage + `apps/backend/tests/unit/vacancies/test_offer_lifecycle.py` | `apps/backend/tests/integration/vacancies/test_vacancy_pipeline_api.py` | second `hired` attempt returns `422`; `offer -> rejected` still requires declined status |

Acceptance rules for the implementation slice:
- Keep `POST /api/v1/pipeline/transitions` as the only write path for `offer -> hired`.
- Do not add public employee or onboarding routes in this slice.
- Keep auth, CORS, route topology, anonymous candidate transport, and offer reason-code semantics unchanged.
- Keep OpenAPI freeze unchanged because no public request/response contract changed.
- Keep compose smoke green without adding feedback-specific browser automation.
- Minimum verification set:
  - `./scripts/check-docs-structure.sh`
  - `./scripts/check-openapi-freeze.sh`
  - `npm --prefix apps/frontend run api:types:check`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test -- --run`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q`
  - `./scripts/smoke-compose.sh`

## Employee Profile Bootstrap Verification (`TASK-06-03`)

Current implementation coverage includes at minimum:

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Employee-profile payload builder maps frozen `hire_conversion` snapshots deterministically | `apps/backend/tests/unit/employee/test_employee_profile_service.py` | N/A | candidate and accepted-offer snapshot fields are copied into the employee bootstrap payload without reading mutable candidate/offer tables |
| Invalid handoff snapshots fail closed before persistence | `apps/backend/tests/unit/employee/test_employee_profile_service.py` | `apps/backend/tests/integration/employee/test_employee_profile_api.py` | malformed snapshot data returns `422 hire_conversion_invalid` and no `employee_profiles` row is inserted |
| Staff bootstrap API creates and reads employee profiles from existing handoffs | N/A | `apps/backend/tests/integration/employee/test_employee_profile_api.py` | `POST /api/v1/employees` and `GET /api/v1/employees/{employee_id}` return the persisted profile created from `hire_conversions` |
| Duplicate bootstrap and missing-handoff contracts remain stable | N/A | `apps/backend/tests/integration/employee/test_employee_profile_api.py` | duplicate create returns `409 employee_profile_already_exists`; missing handoff returns `404 hire_conversion_not_found` |
| RBAC deny path for non-HR/admin employee-profile access | `apps/backend/tests/unit/rbac/test_rbac.py` | `apps/backend/tests/integration/employee/test_employee_profile_api.py` | manager access returns `403` and writes a denied audit event |

Acceptance rules for the implementation slice:
- Keep employee profile creation explicit and staff-only; do not auto-create profiles during `offer -> hired`.
- Keep onboarding trigger/execution out of this slice.
- Freeze OpenAPI and update generated frontend types in the same change because a new staff API contract is introduced.
- Keep auth, CORS, anonymous candidate transport, and existing `offer -> hired` reason-code semantics unchanged.
- Minimum verification set:
  - `./scripts/check-docs-structure.sh`
  - `./scripts/check-openapi-freeze.sh`
  - `npm --prefix apps/frontend run api:types:check`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test -- --run`
- `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q`
- `./scripts/smoke-compose.sh`

## Onboarding Trigger Verification (`TASK-06-04`)

Current implementation coverage includes at minimum:

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Onboarding-start payload builder maps employee profile state deterministically | `apps/backend/tests/unit/employee/test_onboarding_run_service.py` | N/A | `employee_id`, copied `hire_conversion_id`, `status=started`, and `started_by_staff_id` are derived deterministically from the bootstrapped employee profile |
| Atomic employee bootstrap (`employee_profiles` + `onboarding_runs`) | `apps/backend/tests/unit/employee/test_employee_profile_atomicity.py` | `apps/backend/tests/integration/employee/test_employee_profile_api.py` | onboarding persistence failure leaves no partial `employee_profiles` row; successful bootstrap commits both rows once |
| One onboarding run per employee profile rule | `apps/backend/tests/unit/employee/test_onboarding_run_service.py` | `apps/backend/tests/integration/employee/test_employee_profile_api.py` | duplicate onboarding persistence for the same employee is rejected by storage constraints and API duplicate bootstrap still returns `409 employee_profile_already_exists` |
| Employee API exposes additive onboarding metadata | N/A | `apps/backend/tests/integration/employee/test_employee_profile_api.py` | `POST /api/v1/employees` and `GET /api/v1/employees/{employee_id}` include `onboarding_id` and `onboarding_status=started` when bootstrap succeeds |

Acceptance rules for the implementation slice:
- Keep `POST /api/v1/employees` as the only write path; do not add a separate onboarding-start command.
- Keep auth, CORS, route topology, and anonymous candidate transport unchanged.
- Freeze OpenAPI and update generated frontend types in the same change because the existing employee response contract was extended additively.
- Defer onboarding checklist templates, task assignment, portal/dashboard UX, and notifications.
- Minimum verification set:
  - `./scripts/generate-openapi-frozen.sh`
  - `./scripts/check-openapi-freeze.sh`
  - `npm --prefix apps/frontend run api:types:generate`
  - `npm --prefix apps/frontend run api:types:check`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test -- --run`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend ruff check .`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q`
  - `./scripts/check-docs-structure.sh`

## Onboarding Template Management Verification (`TASK-07-01`)

Current implementation coverage includes at minimum:

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Template payload builder normalizes checklist items deterministically | `apps/backend/tests/unit/employee/test_onboarding_template_service.py` | N/A | names/item strings are trimmed, items are ordered by `sort_order`, and duplicate codes/sort orders fail closed before persistence |
| Staff template API creates, reads, lists, and replaces checklist templates | N/A | `apps/backend/tests/integration/employee/test_onboarding_template_api.py` | `POST/GET/PUT /api/v1/onboarding/templates` persist one template plus ordered child items and return the current checklist state |
| Active template switch keeps one active default for later task generation | N/A | `apps/backend/tests/integration/employee/test_onboarding_template_api.py` | making one template active deactivates the previously active template and `active_only=true` returns only the new default |
| Conflict, validation, and RBAC deny contracts remain stable | `apps/backend/tests/unit/rbac/test_rbac.py` | `apps/backend/tests/integration/employee/test_onboarding_template_api.py` | duplicate name returns `409 onboarding_template_name_conflict`; invalid checklist payload returns `422 onboarding_template_invalid`; non-HR/admin access returns `403` and writes denied audit events |

Acceptance rules for the implementation slice:
- Keep template management staff-only and separate from employee bootstrap.
- Freeze OpenAPI and update generated frontend types in the same change because a new onboarding template API contract is introduced.
- Keep auth, CORS, anonymous candidate transport, and employee bootstrap contracts unchanged.
- Defer onboarding task generation/SLA logic, employee portal/dashboard UX, and notifications.
- Minimum verification set:
  - `./scripts/generate-openapi-frozen.sh`
  - `./scripts/check-openapi-freeze.sh`
  - `npm --prefix apps/frontend run api:types:generate`
  - `npm --prefix apps/frontend run api:types:check`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test -- --run`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend ruff check .`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q`
  - `./scripts/check-docs-structure.sh`

## Onboarding Task Generation and Staff Operations Verification (`TASK-07-02`)

Current implementation coverage includes at minimum:

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Task payload builder maps one onboarding run plus active template bundle deterministically | `apps/backend/tests/unit/employee/test_onboarding_task_service.py` | N/A | template items are ordered by `sort_order`, provenance ids are copied, and generated tasks default to `status=pending` |
| Employee bootstrap now atomically persists `employee_profiles + onboarding_runs + onboarding_tasks` | `apps/backend/tests/unit/employee/test_employee_profile_atomicity.py` | `apps/backend/tests/integration/employee/test_employee_profile_api.py` | task-generation failure leaves no partial employee/onboarding rows; successful bootstrap commits both onboarding run and ordered tasks |
| One-time task materialization per onboarding run | `apps/backend/tests/unit/employee/test_onboarding_task_service.py` | `apps/backend/tests/integration/employee/test_onboarding_task_api.py` | duplicate generation/backfill for the same onboarding run fails closed via storage constraints or `409 onboarding_tasks_already_exist` |
| Staff onboarding task API reads, patches, and backfills tasks | `apps/backend/tests/unit/employee/test_onboarding_task_service.py` | `apps/backend/tests/integration/employee/test_onboarding_task_api.py` | `GET/PATCH/POST /api/v1/onboarding/runs/{onboarding_id}/tasks*` return ordered tasks, update status/assignment/SLA fields, and manage `completed_at` server-side |
| Missing active template and RBAC deny contracts stay stable | `apps/backend/tests/unit/rbac/test_rbac.py` | `apps/backend/tests/integration/employee/test_employee_profile_api.py`, `apps/backend/tests/integration/employee/test_onboarding_task_api.py` | missing active template returns `422 onboarding_template_not_configured`; manager access returns `403` and writes denied audit events |

Acceptance rules for the implementation slice:
- Keep `POST /api/v1/employees` as the employee bootstrap command surface; do not add a separate onboarding-start or task-generation bootstrap endpoint.
- Keep onboarding task operations staff-only under the existing `/api/v1/onboarding/...` namespace.
- Freeze OpenAPI and update generated frontend types in the same change because new onboarding task APIs are introduced.
- Keep auth, CORS, anonymous candidate transport, and employee/template contracts unchanged aside from the new bootstrap fail-closed behavior when no active template exists.
- Defer employee portal/dashboard UX, notifications, and template-driven due-date automation.
- Minimum verification set:
  - `./scripts/generate-openapi-frozen.sh`
  - `./scripts/check-openapi-freeze.sh`
  - `npm --prefix apps/frontend run api:types:generate`
  - `npm --prefix apps/frontend run api:types:check`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test -- --run`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend ruff check .`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q`
  - `./scripts/check-docs-structure.sh`

## Employee Self-Service Onboarding Portal Verification (`TASK-07-03`)

Current implementation coverage includes at minimum:

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Employee-profile identity reconciliation is deterministic and fail-closed | `apps/backend/tests/unit/employee/test_employee_onboarding_portal_service.py` | `apps/backend/tests/integration/employee/test_employee_onboarding_portal_api.py` | first self-service read links `employee_profiles.staff_account_id` by exact e-mail when unique; missing profile returns `404 employee_profile_not_found`; duplicate/conflicting matches return `409 employee_profile_identity_conflict` |
| Employee portal read returns employee-scoped onboarding summary and task list | `apps/backend/tests/unit/employee/test_employee_onboarding_portal_service.py` | `apps/backend/tests/integration/employee/test_employee_onboarding_portal_api.py` | `GET /api/v1/employees/me/onboarding` returns the linked employee profile, current onboarding run, ordered task list, and `can_update` flags |
| Employee task updates stay limited to self-actionable tasks and server-managed completion timestamps | `apps/backend/tests/unit/employee/test_employee_onboarding_portal_service.py` | `apps/backend/tests/integration/employee/test_employee_onboarding_portal_api.py` | employee can complete/reopen own actionable task; staff-managed or mismatched task returns `409 onboarding_task_not_actionable_by_employee`; `completed_at` is set/cleared server-side |
| RBAC denies non-employee access to self-service onboarding routes | `apps/backend/tests/unit/rbac/test_rbac.py` | `apps/backend/tests/integration/employee/test_employee_onboarding_portal_api.py` | HR access returns `403` and writes denied audit events; admin/HR continue to use staff onboarding task routes |
| Frontend employee route guard, redirect, Sentry tags, and portal UX stay consistent | `apps/frontend/src/app/auth/session.test.ts`, `apps/frontend/src/app/router.auth.test.tsx`, `apps/frontend/src/app/router.employee.test.tsx`, `apps/frontend/src/app/router.observability.test.tsx`, `apps/frontend/src/pages/EmployeeOnboardingPage.test.tsx` | N/A | employee login redirects to `/employee`, employee guard blocks unauthorized/forbidden sessions, `/employee` emits canonical Sentry tags, and the page renders/upgrades localized task state via the typed API client |

Acceptance rules for the implementation slice:
- Keep employee self-service on the existing employee route tree; do not add new public onboarding routes or reopen auth/CORS behavior.
- Keep staff assignment/backfill/SLA operations on `/api/v1/onboarding/runs/{onboarding_id}/tasks*`; employee updates stay limited to task `status`.
- Freeze OpenAPI and update generated frontend types in the same change because new employee-facing onboarding APIs are introduced.
- Keep candidate/public transport, onboarding template data model, and staff onboarding task contracts unchanged.
- Minimum verification set:
  - `./scripts/generate-openapi-frozen.sh`
  - `./scripts/check-openapi-freeze.sh`
  - `npm --prefix apps/frontend run api:types:generate`
  - `npm --prefix apps/frontend run api:types:check`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test -- --run`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend ruff check .`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q`
  - `./scripts/check-docs-structure.sh`

## HR/Manager Onboarding Dashboard Verification (`TASK-07-04`)

Current implementation coverage includes at minimum:

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Dashboard aggregation and manager-scope filtering are deterministic | `apps/backend/tests/unit/employee/test_onboarding_dashboard_service.py` | N/A | summary counters, progress percent, overdue counts, and manager-visible run set are stable for the same onboarding/task input set |
| Dashboard list/detail APIs return read-only onboarding progress views with stable filter semantics | N/A | `apps/backend/tests/integration/employee/test_onboarding_dashboard_api.py` | `GET /api/v1/onboarding/runs` and `GET /api/v1/onboarding/runs/{onboarding_id}` honor search, task-status, overdue, and visibility filters |
| RBAC allows `admin/hr/manager` read access and denies `employee` role | `apps/backend/tests/unit/rbac/test_rbac.py` | `apps/backend/tests/integration/employee/test_onboarding_dashboard_api.py` | denied roles receive `403` and audit writes; manager reads stay limited to assignment-scoped runs |
| HR workspace embeds onboarding progress without regressing the existing recruitment flow on `/` | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | N/A | HR page still renders vacancy/pipeline controls and the embedded onboarding dashboard block with localized summary/detail state |
| Manager-facing onboarding visibility remains reusable inside the full manager workspace on `/` | `apps/frontend/src/pages/ManagerWorkspacePage.test.tsx`, `apps/frontend/src/app/router.auth.test.tsx`, `apps/frontend/src/app/router.observability.test.tsx` | N/A | manager login redirects to `/`, the manager page renders the embedded onboarding visibility block, and Sentry emits `workspace=manager`, `role=manager`, `route=/` |

Acceptance rules for the implementation slice:
- Keep the current route tree; do not add a separate manager dashboard path.
- Keep dashboard APIs read-only; manager users must not gain task patch/backfill permissions in this slice.
- Freeze OpenAPI and update generated frontend types in the same change because new onboarding dashboard APIs are introduced.
- Keep auth, CORS, employee self-service routes, and public candidate transport unchanged.
- Minimum verification set:
  - `./scripts/generate-openapi-frozen.sh`
  - `./scripts/check-openapi-freeze.sh`
  - `npm --prefix apps/frontend run api:types:generate`
  - `npm --prefix apps/frontend run api:types:check`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test -- --run`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend ruff check .`
- `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q`
- `./scripts/check-docs-structure.sh`

## Manager Workspace Verification (`TASK-09-01`)

Current implementation coverage includes at minimum:

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Vacancy-scoped hiring summary and candidate snapshot ordering are deterministic | `apps/backend/tests/unit/vacancies/test_manager_workspace_service.py` | N/A | overview vacancies sort by latest activity, candidate snapshot rows sort by latest stage activity, and aggregate counts remain stable for the same visible vacancy set |
| Manager workspace APIs stay fail-closed outside explicit vacancy ownership scope | `apps/backend/tests/unit/rbac/test_rbac.py` | `apps/backend/tests/integration/vacancies/test_manager_workspace_api.py` | `manager_workspace:read` is allowed, legacy HR vacancy list access stays `403`, and out-of-scope vacancy snapshot reads return `404 manager_workspace_vacancy_not_found` |
| Vacancy assignment to a hiring manager is explicit and validated on create/update | N/A | `apps/backend/tests/integration/vacancies/test_manager_workspace_api.py` | HR/admin can set or clear `hiring_manager_login`, while missing, inactive, or wrong-role managers fail closed with stable reason codes |
| Manager `/` route renders loading, empty, error, and success states for the full workspace | `apps/frontend/src/pages/ManagerWorkspacePage.test.tsx` | N/A | the page renders hiring summary, vacancy list, localized error mapping, selected-vacancy snapshot, and embedded onboarding visibility without exposing mutation controls |
| HR/admin `/` workspace stays unchanged while manager route observability remains canonical | `apps/frontend/src/pages/HrDashboardPage.test.tsx`, `apps/frontend/src/app/router.auth.test.tsx`, `apps/frontend/src/app/router.observability.test.tsx` | N/A | HR/admin continue to land on the existing recruitment workspace, manager login still redirects to `/`, and Sentry tags remain `workspace=manager`, `route=/` |

Acceptance rules for the implementation slice:
- Keep the existing `/` route split by role; do not add a separate manager-only path.
- Keep manager APIs read-only and scoped by explicit vacancy ownership; do not widen manager access to vacancy, pipeline, candidate, onboarding-task, scoring, or offer mutations.
- Keep auth, CORS, and public candidate transport unchanged.
- Freeze OpenAPI and update generated frontend types in the same change because the vacancy contract and read surface expanded.
- Minimum verification set:
  - `./scripts/generate-openapi-frozen.sh`
  - `./scripts/check-openapi-freeze.sh`
  - `npm --prefix apps/frontend run api:types:generate`
  - `npm --prefix apps/frontend run api:types:check`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test -- --run`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend ruff check .`
- `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q`
- `./scripts/check-docs-structure.sh`

## Accountant Workspace Verification (`TASK-09-03`)

Current implementation coverage includes at minimum:

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Accountant visibility predicate, deterministic ordering, and row counters stay stable | `apps/backend/tests/unit/finance/test_accounting_workspace_service.py` | N/A | only accountant-assigned runs are visible, counters remain deterministic, and non-accountant/unassigned runs stay excluded |
| CSV and XLSX exports reuse one shared column contract and row values | `apps/backend/tests/unit/finance/test_accounting_workspace_service.py` | `apps/backend/tests/integration/finance/test_accounting_workspace_api.py` | header order matches across formats, XLSX sheet name stays `accounting_workspace`, and exported values match the same filtered row set |
| Accountant workspace APIs stay fail-closed outside accountant/admin RBAC scope | `apps/backend/tests/unit/rbac/test_rbac.py` | `apps/backend/tests/integration/finance/test_accounting_workspace_api.py` | `accountant` and `admin` can read/export, `hr/manager/leader/employee` receive `403`, and denied reads are audited |
| Accountant `/` route renders loading, empty, error, and success states with dual export actions | `apps/frontend/src/pages/AccountantWorkspacePage.test.tsx` | N/A | page renders search, paginated read-only table, localized errors, and both `Export CSV` / `Export Excel` actions |
| Route dispatch and observability stay canonical on `/` for accountant role | `apps/frontend/src/app/router.auth.test.tsx`, `apps/frontend/src/app/router.observability.test.tsx`, `apps/frontend/src/api/httpClient.test.ts` | N/A | accountant login redirects to `/`, `/` emits `workspace=accountant`, and binary download failures are captured with accountant route tags |

Acceptance rules for the implementation slice:
- Keep the existing `/` route split by role; do not add a separate accountant-only path.
- Keep accountant APIs read-only and assignment-scoped; do not widen accountant access to HR vacancy, pipeline, onboarding-task mutation, payroll, or generic reporting controls.
- Freeze OpenAPI and update generated frontend types in the same change because a new finance API surface is introduced.
- Keep auth, CORS, employee self-service routes, manager workspace rules, and public candidate transport unchanged.
- Minimum verification set:
  - `./scripts/generate-openapi-frozen.sh`
  - `./scripts/check-openapi-freeze.sh`
  - `npm --prefix apps/frontend run api:types:generate`
  - `npm --prefix apps/frontend run api:types:check`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test -- --run`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend ruff check .`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q`
  - `./scripts/check-docs-structure.sh`

## Role-Specific Notifications Verification (`TASK-09-04`)

Current implementation coverage includes at minimum:

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Notification emitters fan out to manager/accountant recipients and dedupe repeated writes | `apps/backend/tests/unit/notifications/test_notification_service.py` | `apps/backend/tests/integration/notifications/test_notification_api.py` | vacancy ownership and onboarding assignment changes create one recipient-scoped in-app row per newly visible recipient, while repeated writes do not duplicate rows |
| Notification reads and mark-read writes stay fail-closed on `recipient_staff_id=<current subject>` | `apps/backend/tests/unit/notifications/test_notification_service.py`, `apps/backend/tests/unit/rbac/test_rbac.py` | `apps/backend/tests/integration/notifications/test_notification_api.py` | out-of-scope roles get `403`, wrong recipients get `404 notification_not_found`, and only recipient-owned rows change to `read` |
| Digest counters stay role-specific and server-computed on demand | `apps/backend/tests/unit/notifications/test_notification_service.py` | `apps/backend/tests/integration/notifications/test_notification_api.py` | manager digests include owned-open-vacancy counts, accountant digests do not, and task counters reflect current assignment scope |
| Embedded manager/accountant notifications UI renders loading, empty, success, and mark-read paths | `apps/frontend/src/components/NotificationsPanel.test.tsx`, `apps/frontend/src/pages/ManagerWorkspacePage.test.tsx`, `apps/frontend/src/pages/AccountantWorkspacePage.test.tsx` | N/A | both `/` workspaces render the shared notifications block, localized summary chips, unread items, and `Mark as read` without route changes |
| OpenAPI freeze and generated frontend types stay synced with the notification contract | `npm --prefix apps/frontend run api:types:check` | `./scripts/check-openapi-freeze.sh` | notification endpoints and schemas exist in `docs/api/openapi.frozen.json` and `apps/frontend/src/api/generated/openapi-types.ts` |

Acceptance rules for the implementation slice:
- Keep route topology unchanged; notifications stay embedded inside the existing `/` manager/accountant workspaces.
- Keep delivery in-app only; do not add email, SMS, webhooks, outbox, scheduler, event-bus, or template-editor behavior.
- Keep reads and updates fail-closed on `recipient_staff_id=<current subject>`.
- Emit notifications only on assignment or ownership change and keep dedupe mandatory.
- Keep candidate invite delivery manual-only and do not alter interview invite transport.
- Minimum verification set:
  - `./scripts/generate-openapi-frozen.sh`
  - `./scripts/check-openapi-freeze.sh`
  - `npm --prefix apps/frontend run api:types:generate`
  - `npm --prefix apps/frontend run api:types:check`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test -- --run`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend ruff check .`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q`
  - `./scripts/check-docs-structure.sh`

## Offer Workflow Verification (`TASK-06-01`)

Current implementation coverage includes at minimum:

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Offer lifecycle state machine (`draft`, `sent`, `accepted`, `declined`) and reason-code validation | `apps/backend/tests/unit/vacancies/test_offer_lifecycle.py` | `apps/backend/tests/integration/vacancies/test_vacancy_pipeline_api.py` | invalid stage/status mutations return `409/422` with stable offer reason codes |
| Offer draft persistence on the existing vacancy route tree | `apps/backend/tests/unit/vacancies/test_offer_lifecycle.py` | `apps/backend/tests/integration/vacancies/test_vacancy_pipeline_api.py` | `GET/PUT /api/v1/vacancies/{vacancy_id}/offers/{candidate_id}` works without adding a new top-level route tree |
| Fairness-gated `interview -> offer` bootstrap | covered by `TASK-05-03/04` unit/integration suite | `apps/backend/tests/integration/vacancies/test_vacancy_pipeline_api.py` | successful `interview -> offer` still depends on the existing fairness gate and auto-provisions offer state |
| `offer -> hired` requires accepted offer; `offer -> rejected` requires declined offer | `apps/backend/tests/unit/vacancies/test_offer_lifecycle.py` | `apps/backend/tests/integration/vacancies/test_vacancy_pipeline_api.py` | pipeline transition endpoint returns `409 offer_not_accepted` / `409 offer_not_declined` before terminal conversion |
| HR offer UX on `/` | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | backend integration above | draft save, send, accept flow, and localized hired blocker render correctly in the existing HR workspace |

Acceptance rules for the implementation slice:
- Freeze OpenAPI and update generated frontend types in the same change.
- Keep auth, CORS, route topology, and anonymous candidate transport unchanged.
- Keep the fairness gate on the existing `interview -> offer` transition; do not add a candidate-facing offer decision endpoint in this slice.
- Minimum verification set:
  - `./scripts/check-docs-structure.sh`
  - `./scripts/check-openapi-freeze.sh`
  - `npm --prefix apps/frontend run api:types:check`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test -- --run`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q`
  - `./scripts/smoke-compose.sh`

## Frontend Admin Verification (ADMIN-01)

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Admin guard decision logic | `apps/frontend/src/app/auth/session.test.ts` | N/A | `npm --prefix apps/frontend run test -- --run` |
| Unauthorized/forbidden redirect flow | `apps/frontend/src/app/router.admin.test.tsx` | `/admin` route smoke in browser/CI preview | Redirects to `/access-denied` with reason query |
| RU/EN admin shell rendering | `apps/frontend/src/app/router.admin.test.tsx` + i18n keys | UI smoke for `/admin` after language toggle | Admin shell strings are present in both locales |
| Admin observability tags | N/A | Manual/automated capture in Sentry QA project | `workspace`, `role`, `route` tags set on admin route access |

## Admin Staff Management Verification (ADMIN-02)

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Staff DAO pagination/search/filter/count | `apps/backend/tests/unit/admin/test_staff_account_dao.py` | Covered indirectly by admin list integration API tests | `uv run --project apps/backend pytest -q` |
| Staff update strict guard validation | `apps/backend/tests/unit/admin/test_admin_staff_service.py` (`empty_patch`, `unsupported_role`, self/last-admin protection) | `apps/backend/tests/integration/admin/test_admin_staff_management.py` (`409` guard paths) | reason codes `self_modification_forbidden`, `last_admin_protection` |
| Admin list/update API contracts | N/A | `apps/backend/tests/integration/admin/test_admin_staff_management.py` | `GET /api/v1/admin/staff` and `PATCH /api/v1/admin/staff/{staff_id}` |
| RBAC deny path for non-admin access | `tests/unit/rbac/test_rbac.py` | `test_non_admin_gets_403_for_staff_list_and_update` | explicit `403` behavior |
| Admin audit events for list/update | N/A | `test_admin_staff_audit_events_capture_success_and_failure_reason_codes` | `admin.staff:list` and `admin.staff:update` success/failure with reason codes |
| Frontend `/admin/staff` rendering and interactions | `apps/frontend/src/pages/AdminStaffManagementPage.test.tsx` | Route guard tests in `apps/frontend/src/app/router.admin.test.tsx` | filters, PATCH action, localized `404/409/422` error mapping |
| Sentry route tag for admin staff screen | N/A | `apps/frontend/src/app/router.admin.test.tsx` + QA Sentry smoke | `route=/admin/staff` tag emitted by `AdminGuard` |

## Employee Key Lifecycle Verification (ADMIN-03)

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Employee-key DAO list/count/revoke | `apps/backend/tests/unit/admin/test_employee_registration_key_dao.py` | Covered by admin employee-key integration API tests | `uv run --project apps/backend pytest -q` |
| Employee-key service guard and status model | `apps/backend/tests/unit/admin/test_admin_employee_key_service.py` | `apps/backend/tests/integration/admin/test_admin_employee_key_management.py` (`404/409` reason-code paths) | reason codes `key_not_found`, `key_already_used`, `key_already_expired`, `key_already_revoked` |
| Admin employee-key API contracts | N/A | `apps/backend/tests/integration/admin/test_admin_employee_key_management.py` | `GET /api/v1/admin/employee-keys`, `POST /api/v1/admin/employee-keys/{key_id}/revoke` |
| RBAC for key lifecycle endpoints | `tests/unit/rbac/test_rbac.py` | `test_non_privileged_roles_get_403_for_employee_key_list_and_revoke` | `admin/hr` allowed, non-privileged roles denied |
| Auth consume path rejects revoked keys | `apps/backend/tests/unit/auth/test_auth_employee_registration_key_dao.py` | Covered by auth stack invalid-key behavior | revoked keys are not consumable |
| Frontend `/admin/employee-keys` rendering and interactions | `apps/frontend/src/pages/AdminEmployeeKeysManagementPage.test.tsx` | route guard tests in `apps/frontend/src/app/router.admin.test.tsx` | list/filter/pagination, create/revoke actions, localized errors |
| Sentry route tag for employee-key screen | N/A | `apps/frontend/src/app/router.admin.test.tsx` + QA Sentry smoke | `route=/admin/employee-keys` tag emitted by `AdminGuard` |

## Frontend Observability Verification (`TASK-11-10`)

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Canonical Sentry tags on critical routes (`/`, `/candidate`, `/login`) | `apps/frontend/src/app/router.observability.test.tsx` | Manual QA against Sentry project or local browser verification | `workspace`, `role`, `route` tags match the documented route/workspace mapping |
| Canonical Sentry tags on admin critical routes (`/admin`, `/admin/staff`, `/admin/employee-keys`) | `apps/frontend/src/app/router.admin.test.tsx` | Manual QA against Sentry project or admin route smoke | admin routes emit `workspace=admin` plus the canonical route tag |
| Shared HTTP failure capture with request metadata | `apps/frontend/src/api/httpClient.test.ts` | Manual failure injection against local backend or Sentry QA project | Sentry event includes current route tags plus `http_method`, `http_status`, and request path metadata |
| Localized render-failure fallback boundary | `apps/frontend/src/app/observability/AppErrorBoundary.test.tsx` | Manual browser smoke with a forced render exception in QA build | crashing route renders RU/EN fallback UI and the exception is captured in Sentry |
| Frontend non-regression after observability hardening | `npm --prefix apps/frontend run test -- --run` | existing compose smoke remains unchanged | no route, auth, CORS, or typed-client regression |

## Baseline Verification Commands
- `./scripts/check-docs-structure.sh`
- `./scripts/check-openapi-freeze.sh`
- `uv run --project apps/backend ruff check apps/backend/src apps/backend/tests apps/backend/alembic`
- `uv run --project apps/backend pytest -q`
- `uv run --project apps/backend pytest -q apps/backend/tests/unit/candidates/test_cv_parsing_normalization.py apps/backend/tests/integration/candidates/test_candidate_api.py apps/backend/tests/integration/candidates/test_cv_parsing_jobs.py apps/backend/tests/integration/vacancies/test_vacancy_pipeline_api.py`
- `npm --prefix apps/frontend run lint`
- `npm --prefix apps/frontend run test -- --run`
- `uv run --project apps/backend pytest apps/backend/tests/unit/test_cors.py apps/backend/tests/unit/auth/test_auth_settings.py -q`
- `python3 scripts/browser_auth_smoke.py --frontend-url http://localhost:5173/login --api-origin http://localhost:8000 --login <login> --password <password>`
- `python3 scripts/browser_candidate_apply_smoke.py --frontend-url http://localhost:5173/candidate --api-origin http://localhost:8000 --vacancy-id <vacancy_id> --vacancy-title <title>`
- `./scripts/smoke-compose.sh`
- `DATABASE_URL=sqlite+pysqlite:///tmp/hrm_alembic_security.db uv run --project apps/backend alembic upgrade head`
- `DATABASE_URL=sqlite+pysqlite:///tmp/hrm_alembic_security.db uv run --project apps/backend alembic downgrade -1`
- `DATABASE_URL=postgresql+psycopg://hrm:hrm@localhost:5432/<test_db> uv run --project apps/backend alembic upgrade head && ... downgrade -1 && ... upgrade head`
- `npm --prefix apps/frontend run lint && npm --prefix apps/frontend run test -- --run`
