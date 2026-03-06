# Release Checklist

## Pre-Release
- [ ] Acceptance criteria are satisfied.
- [ ] Required tests passed and evidence attached.
- [ ] OpenAPI frozen contract check passed (`./scripts/check-openapi-freeze.sh`).
- [ ] PostgreSQL migrations verified (`alembic upgrade head` / rollback check as needed).
- [ ] Rollback strategy is documented.
- [ ] `docs/` updates are complete.

## Release
- [ ] Deploy steps executed in order.
- [ ] Smoke checks passed.
- [ ] Browser auth smoke verified (`/login -> login -> me -> logout -> /login` against compose stack).
- [ ] Monitoring and alerts verified.
- [ ] Container baseline check passed (`docker compose config` + service health checks).
- [ ] Public apply anti-abuse checks verified (`409/429` paths, rate-limit headers, audit reason codes).
- [ ] Admin route guard smoke verified (`/admin` allow for admin, deny for non-admin).
- [ ] Admin staff management smoke verified (`GET/PATCH /api/v1/admin/staff*`, `409` strict-guard paths, RU/EN UI errors).
- [ ] Admin employee-key lifecycle smoke verified (`POST/GET /api/v1/admin/employee-keys*`, revoke `404/409` reason-codes, RU/EN UI errors on `/admin/employee-keys`).

## Post-Release
- [ ] No critical regressions within observation window.
- [ ] Changelog entry updated.
- [ ] Follow-up tasks created for known gaps.
