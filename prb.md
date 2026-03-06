# PRB: HRM Platform

## Date
2026-03-06

## Stakeholder Input
- Simplify candidate matching to vacancies before interviews.
- Increase interview fairness and reduce bias.
- Simplify HR daily operations.
- Simplify onboarding for new employees.
- Automate HR processes in the company.
- Reduce operational load for managers, leaders, and accountants.

## Primary Users
- HR
- Candidates
- Managers
- Employees
- Leaders
- Accountants

## V1 Expectations
- Include core HRM features.
- Include CV analysis.
- Include functionality for HR, managers, leaders, accountants, and employees.
- Prefer delivering all planned functionality in v1.
- Delivery priority for phase work: admin control plane first, then candidate CV upload/intake, then HR module.

## Constraints
- Must comply with personal data storage and processing laws for Belarus and Russia.
- Compliance baseline: data storage standards for Belarus and Russia.
- Sensitive personal data must be protected.
- Timeline: as fast as possible; no fixed deadline.
- Track metric: share of automated HR operations (target 70%).
- CV processing must support PDF and DOCX formats.
- CV processing must support bilingual RU/EN flow.
- Current delivery target is local runtime on the current device; production deployment is not required at this stage.

## Mandatory Integrations for v1
- Ollama
- Google Calendar

## Technical Requirements Extracted from CV Analysis Article
- Build an NLP/LLM pipeline for CV parsing into a canonical structured candidate profile.
- Preserve traceability from extracted facts to source text fragments (sentences/paragraphs).
- Provide explainable ranking with matched requirements, uncovered gaps, and supporting evidence snippets.
- Apply bilingual normalization (ru/en) with language-aware parsing and skill normalization.
- Support quality control metrics:
  - extraction quality (precision/recall),
  - ranking quality (NDCG, MRR),
  - robustness checks for small paraphrasing changes.
- Enforce secure processing:
  - strict access control to CVs and AI analysis outputs,
  - audit trail of user actions,
  - data minimization by workflow stage.

## Legal Mapping (Open Question Resolved)
- Belarus:
  - Law No. 99-З (07.05.2021) "On Personal Data Protection",
  - Law No. 455-З (10.11.2008) "On Information, Informatization and Information Protection",
  - OAC Order No. 195 (12.11.2021) on technical and cryptographic protection of personal data,
  - NCPD guidance on legal basis for personal data processing.
- Russia:
  - Federal Law No. 152-ФЗ (27.07.2006) "On Personal Data",
  - Federal Law No. 149-ФЗ (27.07.2006) "On Information, Information Technologies and Information Protection",
  - Federal Law No. 242-ФЗ (21.07.2014) on localization requirements,
  - Government Decree No. 1119 (01.11.2012) on personal data protection requirements in information systems.

## Open Questions
- No blocking open questions for current local-delivery stage.
- Article-level legal mapping is moved to planned delivery scope (`EPIC-13` / `TASK-13-*`) and remains a hard gate before first production release.
