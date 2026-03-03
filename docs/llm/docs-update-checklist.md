# Documentation Update Checklist

Run this checklist for every non-trivial task.

## Always
- [ ] `docs/README.md` links remain valid.
- [ ] `docs/ownership.md` still reflects responsible roles.
- [ ] Relevant section in `docs/project/brief.md` updated if business scope changed.
- [ ] `docs/engineering/best-practices.md` requirements are applied for the task.

## If Architecture Changed
- [ ] Update `docs/architecture/overview.md`.
- [ ] Update `docs/architecture/diagrams.md`.
- [ ] Add/update entry in `docs/architecture/decisions.md`.

## If Data Flow or Critical Business Flow Changed
- [ ] Update related sequence/flow diagrams in `docs/architecture/diagrams.md`.
- [ ] Confirm diagram consistency with current interfaces and modules.

## If Operations Changed
- [ ] Update `docs/operations/runbook.md`.
- [ ] Update `docs/operations/release-checklist.md` if release path changed.

## If Test Expectations Changed
- [ ] Update `docs/testing/strategy.md`.

## If Code Was Added/Changed
- [ ] Public modules/classes/functions include detailed docstrings.
- [ ] Inline comments are minimal and only for non-obvious logic.

## If Frontend Scope Changed
- [ ] Update `docs/project/frontend-requirements.md`.
- [ ] Update frontend-relevant diagrams in `docs/architecture/diagrams.md`.
- [ ] Confirm React.js requirement is preserved and documented.

## Final Check
- [ ] Last-updated date/editor refreshed in touched docs.
- [ ] Architect sign-off completed for architecture-level changes.
