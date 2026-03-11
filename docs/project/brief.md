# Project Brief

## Last Updated
- Date: 2026-03-11
- Updated by: architect + backend-engineer

## Problem Statement
Build a general HRM platform that simplifies candidate-to-vacancy matching before interviews,
supports hiring across professions and industries, improves interview fairness, reduces HR
workload, streamlines onboarding, automates HR processes, and reduces operational load for
managers, leaders, and accountants.

## Target Users
- HR specialists
- Candidates
- Managers
- Employees
- Company leaders
- Accountants

## Business Goals
- Improve pre-interview candidate selection quality and speed.
- Increase fairness and reduce bias in interview-related workflows.
- Reduce manual HR operations through automation.
- Improve onboarding experience for new employees.
- Reduce administrative load for management and finance roles.

## Success Metrics
| Metric | Baseline | Target | Owner |
| --- | --- | --- | --- |
| Share of automated HR operations (%) | Not defined | 70% | business-analyst |

Metric formula:
`(automated_hr_operations / total_hr_operations) * 100` per calendar month.

## Scope
### In Scope
- Core HRM capabilities for first release.
- CV analysis capability for profession-agnostic resumes and employment history.
- Role-specific workflows for HR, managers, leaders, accountants, and employees.
- Broad v1 delivery with most planned functionality (preferably all planned features).
- Mandatory integrations: Ollama and Google Calendar.
- Mandatory technical stack requirement: frontend on React.js + TypeScript.
- Preferred rollout if full scope does not fit one cycle:
  1. Admin control plane (staff governance + registration key lifecycle)
  2. Candidate module (CV upload/intake/parsing baseline)
  3. HR module (vacancies/pipeline/interview operations)
  4. Managers + Employees + Accountants + Leaders

### Out of Scope
- Explicitly out-of-scope items are not yet defined.

## Delivery Roadmap
- Epic-level roadmap and dependencies are documented in `docs/project/epics.md`.
- Frontend-specific requirements are documented in `docs/project/frontend-requirements.md`.

## Constraints
- Comply with personal data storage and processing laws for Belarus and Russia.
- Compliance baseline is defined in `docs/project/legal-framework.md`.
- Protect sensitive personal data.
- Environment configuration from `.env` must be implemented through
  `pydantic BaseSettings` models.
- Canonical backend settings module: `apps/backend/src/hrm_backend/settings.py`.
- Backend logic must be covered with both unit and integration/e2e tests.
- Backend tests must be organized by domain package and by level:
  `apps/backend/tests/unit/<package>` and `apps/backend/tests/integration/<package>`.
- Frontend implementation technology: React.js + TypeScript.
- Frontend UI should use popular ready-made libraries.
- Frontend localization for v1: ru + en.
- Frontend browser support target for v1: Google Chrome.
- Frontend monitoring stack: Sentry.
- Mobile application is out of scope.
- Delivery expectation: as fast as possible, without fixed deadline.
- Current milestone target: stable end-to-end operation on the current device (local environment).
- Production rollout is out of scope for the current stage.
- CV analysis baseline:
  - input formats: PDF and DOCX,
  - bilingual processing: RU and EN,
  - profession-agnostic structured extraction of workplaces with held positions, education,
    normalized titles, normalized dates/ranges, and generic skills,
  - explainability: output must include evidence snippets from source CV fragments,
  - quality control metrics: precision/recall, NDCG/MRR, robustness checks.

## Open Questions
- No blocking product-level questions.
- Compliance article-level mapping is tracked as planned delivery scope (`EPIC-13` / `TASK-13-*`) rather than open discovery.
