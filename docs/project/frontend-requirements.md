# Frontend Requirements (React.js)

## Last Updated
- Date: 2026-03-11
- Updated by: architect + frontend-engineer

## Fixed Technical Requirement
- Frontend must be implemented using `React.js` + `TypeScript`.

## Baseline Frontend Requirements
- Role-based UI for: HR, Candidate, Manager, Employee, Leader, Accountant.
- Secure authentication flow with protected routes and session handling.
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
  4. shortlist review inside the existing HR workspace on `/`,
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
| Candidate portal scope | CV upload + self information confirmation + public token-based interview registration on `/candidate` |
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
  - `employee` -> `/employee`
  - `hr`, `manager`, `leader`, `accountant` -> `/`
  - unknown role -> `/access-denied?reason=forbidden`
- `/login` behavior rules:
  - already-authenticated valid session -> redirect to role workspace;
  - broken session (`me` check fails) -> clear session and render login form.
- Login UI must expose RU/EN user-readable error states for `401`, `422`, and generic HTTP failures.

## TASK-11-07 Baseline
- Do not add a new route. Extend the current HR workspace on `/`.
- In `HrDashboardPage`, add a shortlist review block that becomes active only when both a vacancy and a candidate are selected.
- Required UX elements:
  - `Run score` action;
  - `queued`, `running`, `succeeded`, and `failed` state rendering;
  - score card with `score`, `confidence`, and `summary`;
  - matched requirements, missing requirements, and evidence snippet sections.
- Frontend error handling must provide RU/EN-readable messages for `403`, `404`, `409`, `422`, and generic HTTP failures.
- Typed frontend API wrappers must consume only artifacts generated from frozen OpenAPI.
- Browser smoke must not be expanded to cover scoring; keep scoring verification on unit/integration level.

## TASK-11-10 Baseline
- Do not add or restructure routes. Keep the current topology:
  - `/`
  - `/employee`
  - `/candidate`
  - `/login`
  - `/admin`
  - `/admin/staff`
  - `/admin/employee-keys`
- Emit canonical Sentry tags on critical-route access:
  - `workspace`
  - `role`
  - `route`
- Required route/workspace mapping:
  - `/` -> `workspace=hr`, `route=/` for `admin`, `hr`, and `leader`
  - `/` -> `workspace=manager`, `route=/` for `manager`
  - `/` -> `workspace=accountant`, `route=/` for `accountant`
  - `/employee` -> `workspace=employee`, `route=/employee`
  - `/candidate` -> `workspace=candidate`, `route=/candidate`
  - `/login` -> `workspace=auth`, `route=/login`
  - `/admin`, `/admin/staff`, `/admin/employee-keys` -> `workspace=admin` with the matching canonical route
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
  - HR scheduling stays on `/`;
  - candidate interview registration stays on `/candidate?interviewToken=<token>`.
- HR workspace requirements:
  - do not add a new HR route;
  - add interview scheduling controls only when vacancy and candidate are selected;
  - show both business `status` and `calendar_sync_status`;
  - expose `candidate_invite_url` only to authorized staff users;
  - support `reschedule`, `cancel`, and `resend invite`.
- Candidate route requirements:
  - keep public access anonymous and token-based;
  - support `Confirm`, `Request reschedule`, and `Decline`;
  - render localized `404`, `409`, `410`, `422`, and generic HTTP errors;
  - reject mixed `vacancyId` and `interviewToken` modes with a localized invalid-link state.
- Do not introduce candidate auth, new CORS rules, or a new routing tree in this slice.
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
- Keep the current route tree intact; do not add a new manager dashboard path.
- Use the existing `/` route for both staff workspaces:
  - `hr`/`admin` keep the current recruitment workspace and render onboarding progress as an embedded block;
  - `manager` uses `/` as a standalone onboarding dashboard.
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
- Emit canonical Sentry tags for `/` based on resolved role:
  - `workspace=hr` for HR/admin-style workspace
  - `workspace=manager` for manager dashboard
- Keep auth, CORS, public candidate transport, employee portal contracts, and onboarding task mutation routes unchanged in this slice.

## TASK-09-03 Baseline
- Keep the existing route topology intact; do not add a new accountant-only path.
- Use the existing `/` route for accountant users:
  - `accountant` resolves to a dedicated accountant workspace page;
  - `hr`/`admin`/`leader` keep the HR workspace on `/`;
  - `manager` keeps the manager workspace on `/`.
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
- Emit canonical Sentry tags for `/` based on resolved role:
  - `workspace=accountant` for accountant workspace.
- Keep auth, CORS, employee self-service routes, HR/manager route topology, and generic reporting/export infrastructure unchanged in this slice.

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
