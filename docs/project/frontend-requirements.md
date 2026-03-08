# Frontend Requirements (React.js)

## Last Updated
- Date: 2026-03-09
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
- Candidate interview registration UI is delivered as a dedicated follow-up flow after the scoring slice and a separate interview-planning pass.
- Delivery priority inside phase-1 frontend:
  1. Admin workspace,
  2. Candidate CV upload and parsing visibility,
  3. HR vacancy/pipeline workspace,
  4. shortlist review inside the existing HR workspace on `/`,
  5. interview scheduling/registration only after a dedicated planning pass.
- Interview scheduling UX with Google Calendar sync status visibility remains required, but it is not the next implementation slice.
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
| Candidate portal scope | CV upload + self information confirmation (interview registration via dedicated follow-up flow) |
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
  - `hr`, `manager`, `leader`, `accountant`, `employee` -> `/`
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

## TASK-11-08 Planning Gate
- Do not start implementation until a short planning pass defines:
  - interview entity and lifecycle rules;
  - candidate registration token/identity model;
  - reschedule and cancel semantics;
  - Google Calendar sync conflict behavior.

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
