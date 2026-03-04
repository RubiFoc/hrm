# Release Checklist

## Pre-Release
- [ ] Acceptance criteria are satisfied.
- [ ] Required tests passed and evidence attached.
- [ ] PostgreSQL migrations verified (`alembic upgrade head` / rollback check as needed).
- [ ] Rollback strategy is documented.
- [ ] `docs/` updates are complete.

## Release
- [ ] Deploy steps executed in order.
- [ ] Smoke checks passed.
- [ ] Monitoring and alerts verified.
- [ ] Container baseline check passed (`docker compose config` + service health checks).

## Post-Release
- [ ] No critical regressions within observation window.
- [ ] Changelog entry updated.
- [ ] Follow-up tasks created for known gaps.
