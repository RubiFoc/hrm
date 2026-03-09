# hrm

Project skeleton prepared for long-term maintenance with LLM-assisted workflows.

## Start Here
- Human/agent operating rules: `AGENTS.md`
- Documentation index: `docs/README.md`
- Agent team workflow: `.ai/team/workflow.md`
- Reusable skills: `.ai/skills/*`

## Primary Goal
Keep project knowledge explicit, versioned, and easy to consume by both humans and LLM agents.

## Maintenance Principle
Every behavior change must update code and documentation in the same task.

## Engineering Bootstrap
- Backend (`uv`): `cd apps/backend && uv sync && uv run uvicorn hrm_backend.main:app --reload`
- Frontend (React + TS): `cd apps/frontend && npm install && npm run dev`
- Docs check: `./scripts/check-docs-structure.sh`

## Docker Bootstrap
1. `cp .env.example .env`
2. `docker compose up -d --build`
3. Frontend: `http://localhost:5173`, Backend health: `http://localhost:8000/health`

Shortcut commands:
- `make up`, `make rebuild`, `make clean-orphans`, `make down`, `make ps`, `make logs`, `make smoke`
- `just up`, `just rebuild`, `just clean-orphans`, `just down`, `just ps`, `just logs`, `just smoke`

## Delivery Process
- Git/GitHub flow and protected branch policy: `docs/operations/github-workflow.md`
- PR Definition of Done: `.github/PULL_REQUEST_TEMPLATE.md`
- Approved M1 sprint ownership: `docs/project/sprint-m1-plan.md`
- Legal mapping (NPA -> controls): `docs/project/legal-controls-matrix.md`
- Compliance evidence ownership: `docs/project/evidence-registry.md`
- Interview planning baseline: `docs/project/interview-planning-pass.md`
