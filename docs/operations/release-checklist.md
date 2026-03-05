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
- [ ] Monitoring and alerts verified.
- [ ] Container baseline check passed (`docker compose config` + service health checks).
- [ ] Public apply anti-abuse checks verified (`409/429` paths, rate-limit headers, audit reason codes).

## Post-Release
- [ ] No critical regressions within observation window.
- [ ] Changelog entry updated.
- [ ] Follow-up tasks created for known gaps.
