# GitHub Workflow and Branch Protection

## Last Updated
- Date: 2026-03-04
- Updated by: coordinator

## Branching Model
- `main`: protected release-ready branch.
- `develop`: integration branch for sprint work.
- `feature/TASK-xx-yy-short-name`: feature branch for one task.
- `hotfix/TASK-xx-yy-short-name`: urgent production fixes.

## Pull Request Rules
- Direct push to `main` is forbidden.
- Every change goes through PR with linked `TASK-*`.
- Minimum reviewers: 2 (tech owner + domain owner).
- Required CI checks: `docs-check`, `backend`, `frontend`.
- Squash merge by default to keep history clean.

## Protected Branch Setup (GitHub)
- Protect `main` branch.
- Require pull request before merging.
- Require approvals: at least 2.
- Dismiss stale approvals when new commits are pushed.
- Require status checks to pass before merge.
- Include administrators in branch restrictions.
- Restrict force pushes and deletions.
- Require conversation resolution before merge.
- Automation option: run `scripts/setup-github-repo.sh` with `GH_TOKEN` and repo name.
- Backlog metadata sync option: run `scripts/sync-m1-issues-metadata.sh` with `GH_TOKEN` that has `Issues: Read and write`.

## Review Responsibilities
- Backend changes: backend + architect.
- Frontend changes: frontend + architect.
- Compliance/legal-impacting changes: business-analyst + architect.
- Documentation-only changes: area owner from `docs/ownership.md`.

## Commit and PR Hygiene
- Commit scope: one concern per commit.
- Commit message style: `type(scope): summary`.
- PR description must include verification commands and risks.
