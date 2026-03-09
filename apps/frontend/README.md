# Frontend (React + TypeScript)

## Setup
- Install: `npm install`
- Run dev: `npm run dev`
- Lint: `npm run lint`
- Test: `npm run test -- --run`
- Generate API types: `npm run api:types:generate`
- Check API types generation: `npm run api:types:check`

## Docker
- Built by root compose stack using `docker/frontend.Dockerfile`.
- Exposed by compose on `http://localhost:5173`.

## Baseline Libraries
- UI: MUI
- Routing: React Router
- Data fetching/cache: TanStack Query
- Forms/validation: React Hook Form + Zod
- Localization: i18next (RU/EN)
- Error tracking: Sentry (`VITE_SENTRY_DSN`)

## Observability Environment
- `VITE_SENTRY_DSN`: enable browser telemetry when set.
- `VITE_SENTRY_ENVIRONMENT`: Sentry environment tag (`local-compose` by default in compose).
- `VITE_SENTRY_RELEASE`: release marker attached to frontend Sentry events.
- `VITE_SENTRY_TRACES_SAMPLE_RATE`: browser tracing sample rate (`0.2` default in compose).
