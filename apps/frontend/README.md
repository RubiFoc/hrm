# Frontend (React + TypeScript)

## Setup
- Install: `npm install`
- Run dev: `npm run dev`
- Lint: `npm run lint`
- Test: `npm run test -- --run`

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
