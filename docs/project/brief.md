# Project Brief

## Last Updated
- Date: 2026-03-03
- Updated by: architect

## Problem Statement
Build an HRM platform that simplifies candidate-to-vacancy matching before interviews, improves interview fairness, reduces HR workload, streamlines onboarding, automates HR processes, and reduces operational load for managers, leaders, and accountants.

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
- CV analysis capability.
- Role-specific workflows for HR, managers, leaders, accountants, and employees.
- Broad v1 delivery with most planned functionality (preferably all planned features).
- Mandatory integrations: Ollama and Google Calendar.
- Mandatory technical stack requirement: frontend on React.js + TypeScript.
- Preferred rollout if full scope does not fit one cycle:
  1. HR + Candidates
  2. Managers + Employees + Accountants + Leaders

### Out of Scope
- Explicitly out-of-scope items are not yet defined.

## Delivery Roadmap
- Epic-level roadmap and dependencies are documented in `docs/project/epics.md`.
- Frontend-specific requirements are documented in `docs/project/frontend-requirements.md`.

## Constraints
- Comply with personal data storage and processing laws for Belarus and Russia.
- Compliance baseline is defined in `docs/project/legal-framework.md`.
- Protect sensitive personal data.
- Frontend implementation technology: React.js + TypeScript.
- Frontend UI should use popular ready-made libraries.
- Frontend localization for v1: ru + en.
- Frontend browser support target for v1: Google Chrome.
- Frontend monitoring stack: Sentry.
- Mobile application is out of scope.
- Delivery expectation: as fast as possible, without fixed deadline.

## Open Questions
- No blocking product-level questions at this stage.
