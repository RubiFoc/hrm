# Frontend Requirements (React.js)

## Last Updated
- Date: 2026-03-03
- Updated by: architect

## Fixed Technical Requirement
- Frontend must be implemented using `React.js` + `TypeScript`.

## Baseline Frontend Requirements
- Role-based UI for: HR, Candidate, Manager, Employee, Leader, Accountant.
- Secure authentication flow with protected routes and session handling.
- Integration with backend APIs via typed/stable API client.
- Candidate self-service in v1:
  CV upload, profile information submission with confirmation, interview registration.
- Interview scheduling UX with Google Calendar sync status visibility.
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
| Candidate portal scope | CV upload + self information confirmation + interview registration |
| Mobile depth | No mobile app, responsive web only |
| Frontend monitoring | Sentry |

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

## Library Baseline (Popular Ready-Made Stack)
- UI components: Material UI (MUI).
- Routing: React Router.
- Data fetching/cache: TanStack Query.
- Forms and validation: React Hook Form + Zod.
- i18n: i18next + react-i18next.
- Monitoring: @sentry/react.

## Acceptance Gate for Frontend Work
- React.js + TypeScript architecture and folder conventions documented.
- Core role journeys implemented for current phase.
- API errors and validation failures handled with user-readable feedback.
- Accessibility and responsive checks completed for critical screens.
- RU/EN localization verified in critical user flows.
- Chrome support verified for critical user flows.
- Sentry integration configured and verified.
- Frontend-related diagrams updated in `docs/architecture/diagrams.md`.
