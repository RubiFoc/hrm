# Frontend Requirements (React.js)

## Last Updated
- Date: 2026-04-06
- Updated by: architect + backend-engineer + frontend-engineer

## Fixed Technical Requirement
- Frontend must be implemented using `React.js` + `TypeScript`.

## Baseline Frontend Requirements
- Role-based UI for: HR, Candidate, Manager, Employee, Leader, Accountant.
- Public company landing page on `/` with a visible careers entry, public job-board link, and checked-in image assets.
- Secure authentication flow with protected routes and session handling.
- Departments directory on `/departments` with read access for all staff roles and edit access limited to `admin`/`leader`.
- Staff login window (`/login`) must be available for local verification and daily staff workspace entry without manual `localStorage` edits.
- Integration with backend APIs via typed/stable API client.
- Current stage target: frontend must run stably in local environment on the current device.
- Candidate self-service in v1:
  CV upload and profile information submission with confirmation.
- Candidate interview registration UI is the next planned follow-up flow after the scoring slice and now uses the decision-complete baseline in `docs/project/interview-planning-pass.md`.
- Delivery priority inside phase-1 frontend:
  1. Admin workspace,
  2. Candidate CV upload and parsing visibility,
  3. HR vacancy/pipeline workspace,
  4. shortlist review inside the dedicated HR workbench on `/hr/workbench`, with `/hr` acting as the overview page and nested routes for vacancies/pipeline/interviews/offers,
  5. interview scheduling/registration from the dedicated planning baseline in `docs/project/interview-planning-pass.md`.
- Interview scheduling UX with Google Calendar sync status visibility remains required and must now follow `docs/project/interview-planning-pass.md`.
- Consistent UI components and validation behavior across modules.
- Accessibility baseline for forms, tables, and primary workflows.
- Responsive web for desktop-first usage.
- Mobile application is out of scope.

## Frontend Non-Functional Requirements
- Predictable state handling and error boundaries.
- Performance budget for first meaningful render in critical screens.
- Structured client-side logging and error telemetry via Sentry.
- Security controls for token storage and sensitive data rendering.
- Localization support for `ru` and `en`.
- Browser support target: `Google Chrome`.

## Confirmed Frontend Decisions
| Requirement Area | Decision |
| --- | --- |
| React stack variant | React.js + TypeScript |
| UI framework/design system | Popular ready-made libraries |
| Localization | `ru` + `en` in v1 |
| Browser support | Google Chrome |
| Candidate portal scope | Public company landing on `/`, public careers board on `/careers`, shareable vacancy detail/apply on `/careers/:vacancyId`, legacy compatibility redirect on `/candidate`, public apply workspace on `/candidate/apply`, and public token-based interview registration on `/candidate/interview/:interviewToken` |
| HR route split | `/hr` is the overview route; focused HR pages live on `/hr/vacancies`, `/hr/pipeline`, `/hr/interviews`, and `/hr/offers`; `/hr/workbench` keeps the legacy consolidated shell; nested HR routes keep the canonical `workspace=hr` / `route=/hr` telemetry grouping |
| Mobile depth | No mobile app, responsive web only |
| Frontend monitoring | Sentry |

## Candidate CV Analysis UX Requirements
- Candidate upload flow supports PDF and DOCX validation feedback.
- Parsing status must surface RU/EN processing progress and failure reason.
- Match explanation UI must reference evidence snippets from source CV fragments.
- Candidate and HR views must keep clear separation of sensitive fields by role.

## ADMIN-01 Baseline
- Add `/admin` route with role guard (`admin` only).
- Redirect flow must distinguish:
  - `401`-like state (missing auth session/token) -> access-denied flow.
  - `403`-like state (authenticated non-admin role) -> access-denied flow.
- Provide RU/EN admin shell layout with operational placeholders.
- Set Sentry tags on admin route access:
  - `workspace=admin`
  - `role=<resolved_role_or_anonymous>`
  - `route=<pathname>`
- Frontend API typing must consume artifacts generated from frozen OpenAPI contract.

## ADMIN-02 Baseline
- Add `/admin/staff` route under existing admin guard.
- Deliver staff management screen with:
  - server-driven pagination (`limit`, `offset`);
  - filters (`search`, `role`, `is_active`);
  - row update action limited to `role` and `is_active`.
- Handle backend reason-code failures (`404/409/422`) with RU/EN user-readable messages.
- Keep Sentry route tagging for admin workspace and ensure `/admin/staff` emits `route=/admin/staff`.
- Keep frontend API layer typed against regenerated frozen OpenAPI artifacts.

## ADMIN-03 Baseline
- Add `/admin/employee-keys` route under existing admin guard.
- Deliver employee-key management screen with:
  - server-driven pagination (`limit`, `offset`);
  - filters (`search`, `target_role`, `status`, `created_by_staff_id`);
  - create action (`target_role`, `ttl_seconds`);
  - revoke action for active keys.
- Handle backend reason-code failures (`404/409/422`) with RU/EN user-readable messages:
  - `key_not_found`
  - `key_already_used`
  - `key_already_expired`
  - `key_already_revoked`
- Keep Sentry route tagging for admin workspace and ensure `/admin/employee-keys` emits `route=/admin/employee-keys`.
- Keep frontend API layer typed against regenerated frozen OpenAPI artifacts.

## ADMIN-04 Baseline
- Add the admin control-plane consoles under the existing admin guard:
  - `/admin/candidates`
  - `/admin/vacancies`
  - `/admin/pipeline`
  - `/admin/audit`
- Reuse existing backend contracts for the slice:
  - candidate profile list/get/create/update;
  - vacancy list/get/create/update;
  - pipeline transition list/create and ordered history;
  - audit list plus CSV/JSONL/XLSX export.
- Keep the slice non-destructive:
  - do not add hard delete flows;
  - keep archive/destructive policy outside this baseline unless separately approved.
- Preserve the current admin visual language and RU/EN support instead of cloning the HR dashboard shell.
- Keep Sentry route tagging for admin workspace and ensure each new route emits its canonical `route=/admin/*` value.
- Keep frontend API layer typed against regenerated frozen OpenAPI artifacts.

## ADMIN-05 Baseline
- Add `/admin/observability` under the existing admin guard.
- Reuse existing backend contracts only:
  - `GET /health`
  - `GET /api/v1/audit/events`
  - `GET /api/v1/candidates/{candidate_id}/cv/parsing-status`
  - `GET /api/v1/vacancies/{vacancy_id}/match-scores/{candidate_id}`
- Keep the slice read-only and non-destructive:
  - no create/update/delete actions;
  - do not add a new backend namespace for worker health or observability.
- Preserve the current admin visual language and RU/EN support instead of cloning the HR dashboard shell.
- Add Sentry route tagging for `/admin/observability` with canonical `workspace=admin` and `route=/admin/observability`.
- Keep frontend API layer typed against regenerated frozen OpenAPI artifacts.

## TASK-11-13 Baseline
- Add dedicated `/login` route/page for staff authentication UX.
- Login flow must use existing backend API contracts:
  - `POST /api/v1/auth/login` (`identifier`, `password`);
  - `GET /api/v1/auth/me` for identity/role bootstrap.
- Persist client session baseline in `localStorage`:
  - `hrm_access_token`
  - `hrm_refresh_token`
  - `hrm_user_role`
- Post-login redirect rules:
  - `admin` -> `/admin`
  - `hr` -> `/hr`
  - `manager` -> `/manager`
  - `accountant` -> `/accountant`
  - `employee` -> `/employee`
  - `leader` -> `/leader`
  - unknown role -> `/access-denied?reason=forbidden`
- `/login` behavior rules:
  - already-authenticated valid session -> redirect to role workspace;
  - broken session (`me` check fails) -> clear session and render login form.
- Login UI must expose RU/EN user-readable error states for `401`, `422`, and generic HTTP failures.

## TASK-11-07 Baseline
- Keep the HR overview on `/hr` and the legacy consolidated workbench on `/hr/workbench`.
- In `HrDashboardPage` (served on `/hr/workbench`), keep a shortlist review block that becomes active only when both a vacancy and a candidate are selected.
- Required UX elements:
  - `Run score` action;
  - `queued`, `running`, `succeeded`, and `failed` state rendering;
  - score card with `score`, `confidence`, and `summary`;
  - matched requirements, missing requirements, and evidence snippet sections.
- Frontend error handling must provide RU/EN-readable messages for `403`, `404`, `409`, `422`, and generic HTTP failures.
- Typed frontend API wrappers must consume only artifacts generated from frozen OpenAPI.
- Browser smoke must not be expanded to cover scoring; keep scoring verification on unit/integration level.

## Frontend Observability Baseline
- Keep the route topology stable and track changes in explicit task baselines. Current topology:
  - `/`
  - `/careers`
  - `/careers/:vacancyId`
  - `/hr`
  - `/hr/vacancies`
  - `/hr/pipeline`
  - `/hr/interviews`
  - `/hr/offers`
  - `/hr/workbench`
  - `/manager`
  - `/accountant`
  - `/leader`
  - `/employee`
  - `/departments`
  - `/candidate`
  - `/candidate/apply`
  - `/candidate/interview/:interviewToken`
  - `/login`
  - `/admin`
  - `/admin/staff`
  - `/admin/employee-keys`
  - `/admin/candidates`
  - `/admin/vacancies`
  - `/admin/pipeline`
  - `/admin/audit`
  - `/admin/observability`
- Emit canonical Sentry tags on critical-route access:
  - `workspace`
  - `role`
  - `route`
- Required route/workspace mapping:
  - `/` -> `workspace=company`, `route=/`
  - `/careers` -> `workspace=careers`, `route=/careers`
  - `/careers/:vacancyId` -> `workspace=careers`, `route=/careers`
  - `/hr` -> `workspace=hr`, `route=/hr` for `admin` and `hr`
  - `/hr/vacancies`, `/hr/pipeline`, `/hr/interviews`, `/hr/offers`, `/hr/workbench` -> `workspace=hr`, `route=/hr` so the split HR screens keep grouped telemetry and the legacy workbench stays aligned with existing route tags
  - `/manager` -> `workspace=manager`, `route=/manager`
  - `/accountant` -> `workspace=accountant`, `route=/accountant`
  - `/leader` -> `workspace=leader`, `route=/leader` for `leader` and `admin`
  - `/employee` -> `workspace=employee`, `route=/employee`
  - `/departments` -> `workspace=departments`, `route=/departments`
  - `/candidate/apply` -> `workspace=candidate`, `route=/candidate/apply`
  - `/candidate/interview/:interviewToken` -> `workspace=candidate`, `route=/candidate/interview`
  - `/candidate` -> `workspace=candidate`, `route=/candidate`
  - `/login` -> `workspace=auth`, `route=/login`
  - `/admin`, `/admin/staff`, `/admin/employee-keys`, `/admin/candidates`, `/admin/vacancies`, `/admin/pipeline`, `/admin/audit`, `/admin/observability` -> `workspace=admin` with the matching canonical route
- Capture frontend HTTP failures in the shared HTTP client with current route tags plus request metadata (`http_method`, `http_status`, request path).
- Wrap the app shell in a localized render-failure boundary that reports the exception to Sentry and shows RU/EN fallback UI.
- Configure release/environment/tracing through frontend env variables:
  - `VITE_SENTRY_DSN`
  - `VITE_SENTRY_ENVIRONMENT`
  - `VITE_SENTRY_RELEASE`
  - `VITE_SENTRY_TRACES_SAMPLE_RATE`
- Do not change typed API wrappers, OpenAPI artifacts, auth flow, or CORS behavior in this slice.

## TASK-11-08 Planned Slice
- Planning baseline source of truth: `docs/project/interview-planning-pass.md`.
- Keep the current route model:
  - HR scheduling lives on `/hr/interviews`, while `/hr/workbench` remains the compatibility path for the consolidated workbench;
  - candidate apply/tracking lives on `/candidate/apply`;
  - candidate interview registration lives on `/candidate/interview/<token>`;
  - `/candidate` remains the compatibility redirect shell for legacy query links.
- HR workspace requirements:
  - add interview scheduling controls only when vacancy and candidate are selected;
  - show both business `status` and `calendar_sync_status`;
  - expose `candidate_invite_url` only to authorized staff users;
  - support `reschedule`, `cancel`, and `resend invite`.
- Candidate route requirements:
  - keep public access anonymous and token-based on `/candidate/interview/:interviewToken`;
  - support `Confirm`, `Request reschedule`, and `Decline`;
  - render localized `404`, `409`, `410`, `422`, and generic HTTP errors;
  - reject mixed `vacancyId` and `interviewToken` modes with a localized invalid-link state on the compatibility shell.
- Do not introduce candidate auth or new CORS rules; keep the compatibility shell thin and redirect-only.
- Invitation delivery remains manual in the next slice; do not add notification-service scope here.

## TASK-07-03 Baseline
- Add `/employee` route under an employee-only guard.
- Keep the existing route tree intact; do not move HR, candidate, or admin workspaces.
- Read employee onboarding state through the existing auth session and:
  - `GET /api/v1/employees/me/onboarding`
  - `PATCH /api/v1/employees/me/onboarding/tasks/{task_id}`
- Render employee-facing onboarding summary and checklist state:
  - onboarding status;
  - current title, location, start date, and accepted-offer summary;
  - required/optional task markers;
  - assignment and due-date visibility;
  - localized actionable vs staff-managed task state.
- Employee updates are limited to self-actionable task status changes; staff assignment/SLA controls remain outside this workspace.
- Frontend error handling must provide RU/EN-readable messages for:
  - `404 employee_profile_not_found`
  - `404 employee_onboarding_not_found`
  - `409 employee_profile_identity_conflict`
  - `409 onboarding_task_not_actionable_by_employee`
  - generic HTTP failures
- Emit canonical Sentry tags for the employee workspace:
  - `workspace=employee`
  - `route=/employee`
- Keep auth, CORS, public candidate transport, and the staff onboarding route tree unchanged in this slice.

## TASK-07-04 Baseline
- Keep the dedicated role route topology intact:
  - `hr`/`admin` use `/hr` for the overview plus embedded onboarding progress, and `/hr/workbench` for the legacy consolidated recruitment workspace;
  - `manager` uses `/manager` as the standalone onboarding dashboard.
- Read onboarding progress through the new read-only onboarding endpoints:
  - `GET /api/v1/onboarding/runs`
  - `GET /api/v1/onboarding/runs/{onboarding_id}`
- Dashboard UX requirements:
  - summary chips for run/task counts and overdue work;
  - filters for employee search, task status, and overdue-only mode;
  - ordered run list with progress/task counters;
  - detail panel with employee summary and materialized task state.
- Visibility rules:
  - `admin`/`hr` can read all onboarding runs;
  - `manager` can read only runs where at least one task is assigned to `assigned_role=manager` or `assigned_staff_id=<current manager subject>`.
- Manager access is read-only in this slice; task assignment, status patching, and backfill remain on the existing admin/HR staff routes.
- Emit canonical Sentry tags for dedicated role pages:
  - `workspace=hr`, `route=/hr` for HR/admin-style workspace
  - `workspace=manager`, `route=/manager` for manager dashboard
- Keep auth, CORS, public candidate transport, employee portal contracts, and onboarding task mutation routes unchanged in this slice.

## TASK-02-04 Baseline
- Use the dedicated `/manager` route for the manager workspace.
- Read manager hiring visibility through the dedicated manager-scoped vacancy APIs:
  - `GET /api/v1/vacancies/manager-workspace`
  - `GET /api/v1/vacancies/{vacancy_id}/manager-workspace/candidates`
- Vacancy scope is fail-closed:
  only vacancies where `vacancies.hiring_manager_staff_id=<current manager subject>` are visible.
- Candidate visibility rules for manager workspace (read-only, fail-closed):
  - do not render candidate PII (name, email, phone) in the manager workspace;
  - do not render CV analysis artifacts (skills, experience summary, parsed profile);
  - minimum candidate snapshot fields: `stage`, `stage_updated_at`, active interview status + schedule times, `offer_status`.
- Workspace UX requirements:
  - summary chips for visible vacancy/candidate/interview counts;
  - vacancy list ordered by latest activity (deterministic);
  - candidate snapshot table ordered by latest stage activity (deterministic);
  - localized `loading`, `empty`, `401/403/404`, and generic error states.
- Keep the embedded onboarding visibility block and notifications panel inside the manager workspace unchanged in this slice.
- Emit canonical Sentry tags for `/manager`:
  - `workspace=manager`
  - `route=/manager`
- Keep auth, CORS, public candidate transport, and HR route semantics unchanged in this slice.

## TASK-09-02 Baseline
- Add dedicated `/leader` route under a leader/admin guard.
- Leader workspace goal: show stored monthly KPI snapshots and a minimal operational overview.
- Read-only data sources:
  - `GET /api/v1/reporting/kpi-snapshots?period_month=<YYYY-MM-01>`
  - `GET /api/v1/reporting/kpi-snapshots/export?format=csv|xlsx&period_month=<YYYY-MM-01>`
- Workspace UX requirements:
  - localized title/subtitle;
  - month selector (`period_month` filter);
  - selected month resolves to the latest available stored snapshot by probing backwards from the requested month (bounded lookback, no new list endpoint) when the requested month has no snapshot rows;
  - operational overview summary cards for the known KPI key set, including automation totals and share metrics;
  - read-only metrics table (metric name, value, generated at);
  - `Export CSV` and `Export Excel` actions with binary download helper;
  - localized loading, empty, and `401/403/422/generic` error states.
- Navigation/role split:
  - `leader` default workspace is `/leader`;
  - `admin` keeps the HR workspace on `/hr` and can open `/leader` for KPI review.
- Emit canonical Sentry tags on `/leader` access:
  - `workspace=leader`
  - `route=/leader`
- Scope restriction:
  - do not expose rebuild controls (`POST /api/v1/reporting/kpi-snapshots/rebuild` remains admin-only).

## TASK-09-03 Baseline
- Use the dedicated `/accountant` route for accountant users.
- Read accountant workspace data through dedicated read-only finance adapter endpoints:
  - `GET /api/v1/accounting/workspace`
  - `GET /api/v1/accounting/workspace/export?format=csv|xlsx`
- Workspace UX requirements:
  - localized title/subtitle;
  - employee search field;
  - paginated read-only table;
  - separate `Export CSV` and `Export Excel` actions;
  - localized loading, empty, and `401/403/422/generic` error states.
- Visibility rules stay fail-closed:
  - accountant rows are visible only when at least one onboarding task has
    `assigned_role=accountant` or `assigned_staff_id=<current accountant subject>`;
  - rows outside this assignment scope must stay invisible in both UI and exports.
- Export rules:
  - support both RFC4180-style UTF-8 CSV and native `.xlsx`;
  - both formats must contain the same filtered full result set and the same ordered columns;
  - binary downloads must use a dedicated frontend helper instead of the JSON-only API wrapper.
- Emit canonical Sentry tags for `/accountant`:
  - `workspace=accountant`
  - `route=/accountant`
- Keep auth, CORS, employee self-service routes, HR/manager route topology, and generic reporting/export infrastructure unchanged in this slice.

## TASK-09-04 Baseline
- Keep notifications embedded in the dedicated `/manager` and `/accountant` workspaces; do not add a notifications-only path.
- Read in-app notifications through dedicated recipient-scoped APIs:
  - `GET /api/v1/notifications?status=unread|all&limit&offset`
  - `GET /api/v1/notifications/digest`
  - `POST /api/v1/notifications/{notification_id}/read`
- Workspace UX requirements:
  - render a localized notifications block inside both manager and accountant workspaces;
  - show digest summary chips plus the latest unread notification list;
  - support `Mark as read` without page navigation;
  - render localized loading, empty, and `401/403/404/422/generic` error states.
- Scope restrictions for this slice:
  - in-app notifications only;
  - mandatory recipient roles limited to `manager` and `accountant`;
  - digest is server-computed on demand only;
  - do not add email, SMS, webhooks, outbox, scheduler, or template-editor UI.
- Keep invite delivery manual:
  `candidate_invite_url` sharing remains outside this slice and stays staff-driven.
- Keep auth, CORS, HR/accountant/manager route semantics, public candidate transport, and existing workspace pages unchanged outside the embedded notifications block.

## Library Baseline (Popular Ready-Made Stack)
- UI components: Material UI (MUI).
- Routing: React Router.
- Data fetching/cache: TanStack Query.
- Forms and validation: React Hook Form + Zod.
- i18n: i18next + react-i18next.
- Monitoring: @sentry/react.

## Acceptance Gate for Frontend Work
- Current stage local run on the current device is verified with documented startup commands.
- React.js + TypeScript architecture and folder conventions documented.
- Core role journeys implemented for current phase.
- API errors and validation failures handled with user-readable feedback.
- Accessibility and responsive checks completed for critical screens.
- RU/EN localization verified in critical user flows.
- Chrome support verified for critical user flows.
- Sentry integration configured and verified.
- Frontend-related diagrams updated in `docs/architecture/diagrams.md`.
