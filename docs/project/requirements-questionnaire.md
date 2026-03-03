# Requirements Questionnaire

## Last Updated
- Date: 2026-03-03
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
  1. HR + Candidates
  2. Managers + Employees + Accountants + Leaders

## 4. Business Rules
- Must enforce personal data storage and processing laws for Belarus and Russia.
- Compliance baseline: priority NPAs listed in `docs/project/legal-framework.md`.

## 5. Success Metrics
- Introduced metric: share of automated HR operations.
- Formula confirmed: `(automated_hr_operations / total_hr_operations) * 100` per calendar month.
- Target threshold: 70%.

## 6. Integrations and Data
- Mandatory integrations: Ollama and Google Calendar.
- Sensitive personal data must be protected.

## 7. Non-Functional Requirements
- Security: strong personal data protection required.
- Performance/availability targets: no additional constraints specified at this stage.

## 8. Delivery Constraints
- Deadline: no fixed date.
- Priority: deliver as quickly as possible.

## 9. Frontend Technical Requirements
- Frontend technology is fixed: React.js + TypeScript.
- Use popular ready-made libraries for UI and frontend foundation.
- Localization for v1: ru + en.
- Browser target for v1: Google Chrome.
- Candidate self-service in v1: CV upload, self information confirmation, interview registration.
- Mobile app is not required.
- Frontend monitoring: Sentry.

## 10. Acceptance Criteria
- Pending detailed v1 acceptance criteria by role.
