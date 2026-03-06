# Requirements Questionnaire

## Last Updated
- Date: 2026-03-06
- Updated by: business-analyst

Use this file to collect baseline project requirements before implementation.

## 1. Product Goal
- Main problem: simplify candidate matching to vacancies before interviews.
- Additional goals: improve interview fairness, simplify HR operations, simplify onboarding, automate HR processes, reduce load for managers/leaders/accountants.

## 2. Target Users
- Primary users: HR, candidates, managers, employees, leaders, accountants.
- Top pain points: to be detailed per user role.

## 3. Scope for First Delivery
- Must-have: core HRM features, CV analysis, role-specific functionality for HR/managers/leaders/accountants/employees.
- Out of scope: not defined yet.
- Note: stakeholder prefers all planned functionality in v1.
- Fallback phased delivery:
  1. Admin control plane (staff governance + employee key lifecycle).
  2. Candidate self-service and CV intake (candidate can upload CV and pass parsing flow).
  3. HR module (vacancy and pipeline workspace).
  4. Managers + Employees + Accountants + Leaders.

## 4. Business Rules
- Must enforce personal data storage and processing laws for Belarus and Russia.
- Compliance baseline: priority NPAs listed in `docs/project/legal-framework.md`.
- Candidate data processing must apply least-privilege access and action-level auditing.
- Article-level legal control mapping is mandatory deliverable (`EPIC-13` / `TASK-13-*`) before production release.

## 5. Success Metrics
- Introduced metric: share of automated HR operations.
- Formula confirmed: `(automated_hr_operations / total_hr_operations) * 100` per calendar month.
- Target threshold: 70%.

## 6. Integrations and Data
- Mandatory integrations: Ollama and Google Calendar.
- Sensitive personal data must be protected.
- CV document formats for v1: PDF and DOCX.
- CV parsing must support Russian and English resumes in a unified comparison model.
- Extracted CV facts must preserve links to source text fragments for explainability.

## 7. Non-Functional Requirements
- Security: strong personal data protection required.
- Performance/availability targets: no additional constraints specified at this stage.
- AI quality control:
  - extraction quality metrics (precision/recall),
  - ranking metrics (NDCG/MRR),
  - robustness checks for minor reformulations of CV/vacancy text.

## 8. Delivery Constraints
- Deadline: no fixed date.
- Priority: deliver as quickly as possible.
- Current stage target: stable local runtime on the current device.
- Production rollout is out of scope for the current stage.

## 9. Frontend Technical Requirements
- Frontend technology is fixed: React.js + TypeScript.
- Use popular ready-made libraries for UI and frontend foundation.
- Localization for v1: ru + en.
- Browser target for v1: Google Chrome.
- Candidate self-service baseline in v1: CV upload and self information confirmation.
- Interview registration UI is delivered as a dedicated follow-up flow after candidate intake baseline.
- Mobile app is not required.
- Frontend monitoring: Sentry.

## 10. Acceptance Criteria
- Current stage accepted when core phase workflows run end-to-end in local environment on the current device.
- Admin-first delivery accepted: admin shell + staff governance + employee key lifecycle are operational.
- Candidate module accepted when candidate can upload PDF/DOCX CV and receive parsing status.
- Explainability accepted when ranking output contains evidence fragments from source CV.
- HR module accepted after candidate CV intake baseline is already available.
