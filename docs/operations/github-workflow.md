# GitHub Workflow and Branch Protection

## Last Updated
- Date: 2026-03-12
- Updated by: coordinator + architect

## Branching Model
- `main`: protected release-ready branch.
- `develop`: integration branch for sprint work.
- `feature/TASK-xx-yy-short-name`: feature branch for one task.
- `hotfix/TASK-xx-yy-short-name`: urgent production fixes.

## Pull Request Rules
- Direct push to `main` is forbidden.
- Every change goes through PR with linked `TASK-*`.
- Current repository mode: solo delivery (`0` required approving reviews).
- Team-target policy (when multiple maintainers are active): minimum 2 reviewers (tech owner + domain owner).
- Required CI checks: `docs-check`, `backend`, `frontend`, `browser-smoke`.
- Squash merge by default to keep history clean.

## Protected Branch Setup (GitHub)
- Protect `main` branch.
- Require pull request before merging.
- Current repo setting: `required_approving_review_count = 0` (solo mode).
- Team-target setting: require approvals at least 2.
- Dismiss stale approvals when new commits are pushed.
- Require status checks to pass before merge.
- Include administrators in branch restrictions.
- Restrict force pushes and deletions.
- Require conversation resolution before merge.
- Automation option: run `scripts/setup-github-repo.sh` with `GH_TOKEN` and repo name.
- Backlog metadata sync option: run `scripts/sync-m1-issues-metadata.sh` with `GH_TOKEN` that has `Issues: Read and write`.

## Review Responsibilities
- Solo mode default: self-review + required CI checks.
- If collaborators are available:
  - Backend changes: backend + architect.
  - Frontend changes: frontend + architect.
  - Compliance/legal-impacting changes: business-analyst + architect.
  - Documentation-only changes: area owner from `docs/ownership.md`.

## Commit and PR Hygiene
- Commit scope: one concern per commit.
- Commit message style: `type(scope): summary`.
- PR description must include verification commands and risks.

## Post-Merge Closeout
- After merge, review all GitHub issues linked to the task/PR.
- Close only the issues that are actually resolved by the merged change.
- If the merge changes backlog status, update `docs/project/tasks.md` in the same closeout step.
- After the PR is closed, delete branches that are no longer needed locally and on GitHub to keep
  the branch list clean.
- Task delivery is not complete until issue closeout and `docs/project/tasks.md` synchronization are finished.

## GitHub CLI Operations (`gh`)
- Always check auth state before PR automation: `gh auth status`.
- If you see `error connecting to api.github.com`, rerun `gh` commands in network-enabled mode for the agent environment.
- If `gh auth status` shows `token ... is invalid`, re-authenticate with `gh auth login -h github.com`.
- Device login can fail with temporary `HTTP 503`; retry login instead of rotating workflow or branches.
- Do not trust only CLI success text (`Logged in as ...`); re-check with `gh auth status` after login.
- Preferred branch cleanup after PR close:
  `git branch -d <branch>` locally and `gh pr merge --delete-branch` or `git push origin --delete <branch>`
  for the remote branch when it is no longer needed.

## Chained PR Creation Order
- Use this order for split delivery: `PR-A -> PR-B -> PR-C -> Stage4 -> PR-D`.
- Use explicit `--base` and `--head` for each PR to keep review diffs clean.
- Recommended mapping:
  - `PR-A`: `feature/pr-a-auth-breaking -> main`
  - `PR-B`: `feature/pr-b-public-apply-hardening -> feature/pr-a-auth-breaking`
  - `PR-C`: `feature/pr-c-uuid-normalization -> feature/pr-b-public-apply-hardening`
  - `Stage4`: `feature/stage4-openapi-freeze -> feature/pr-c-uuid-normalization`
  - `PR-D`: `feature/pr-d-admin-01 -> feature/stage4-openapi-freeze`

## `gh pr create` Body Safety
- Avoid shell interpolation in PR body text (`$`, backticks, command substitution).
- If body contains markdown code spans, prefer one of:
  - Single-quoted plain text without backticks.
  - `--body-file` with a prepared markdown file.
  - Post-create patch via `gh api repos/<org>/<repo>/pulls/<n> -X PATCH -f body=...`.
