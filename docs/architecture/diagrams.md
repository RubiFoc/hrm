# Architecture Diagrams

## Last Updated
- Date: 2026-03-19
- Updated by: architect + backend-engineer

This file is the canonical diagram set for the system. Update diagrams whenever architecture, data flow, or critical business flow changes.

## Diagram 1: System Context (C4-L1)

```mermaid
flowchart LR
  subgraph Users
    HR[HR]
    CAND[Candidate]
    MGR[Manager]
    EMP[Employee]
    LEAD[Leader]
    ACC[Accountant]
  end

  SYS[HRM Platform]
  OLL[Ollama]
  GCAL[Google Calendar]

  HR --> SYS
  CAND --> SYS
  MGR --> SYS
  EMP --> SYS
  LEAD --> SYS
  ACC --> SYS

  SYS --> OLL
  SYS <--> GCAL
```

## Diagram 2: Container View (C4-L2)

```mermaid
flowchart TB
  UI[React.js + TypeScript UI / Role Workspaces]
  API[API Gateway]

  subgraph Core[Core Services]
    COREPKG[Core Shared Package]
    AUTH[Auth and Access Service]
    ADMIN[Admin Governance Service]
    POLICY[Access Policy Evaluator]
    REC[Recruitment Services]
    SCOREDOM[Match Scoring Service]
    EMPDOM[Employee Services]
    NOTIFY[Notification Service]
    AUTOENG[Automation Rule Engine]
    HROPS[HR Automation Services]
    WORKERS[Background Workers]
    ANALYTICS[Reporting and KPI Services]
    AUDIT[Audit Service]
  end

  subgraph Infra[Infrastructure]
    DB[(PostgreSQL)]
    OBJ[(Object Storage)]
    QUEUE[(Queue/Event Bus)]
    REDISDNL[(Redis Denylist: jti/sid)]
  end

  subgraph Ext[External Integrations]
    OLLAMA[Ollama Adapter]
    GCALSYNC[Google Calendar Adapter]
    SENTRY[Sentry]
  end

  UI --> API
  API --> AUTH
  API --> ADMIN
  API --> POLICY
  API --> REC
  API --> SCOREDOM
  API --> EMPDOM
  API --> NOTIFY
  API --> AUTOENG
  API --> HROPS
  API --> ANALYTICS
  WORKERS --> POLICY
  AUTH --> REDISDNL
  ADMIN --> DB
  AUTH -.imports.-> COREPKG
  ADMIN -.imports.-> COREPKG
  POLICY -.imports.-> COREPKG
  REC -.imports.-> COREPKG
  SCOREDOM -.imports.-> COREPKG
  EMPDOM -.imports.-> COREPKG
  NOTIFY -.imports.-> COREPKG
  HROPS -.imports.-> COREPKG
  ANALYTICS -.imports.-> COREPKG

  REC --> DB
  SCOREDOM --> DB
  EMPDOM --> DB
  NOTIFY --> DB
  AUTOENG --> DB
  HROPS --> DB
  ANALYTICS --> DB
  AUDIT --> DB

  REC --> OBJ
  REC --> QUEUE
  SCOREDOM --> QUEUE
  HROPS --> QUEUE
  ANALYTICS --> QUEUE

  REC --> AUTOENG
  EMPDOM --> AUTOENG
  AUTOENG -.notification.emit.-> NOTIFY

  REC --> OLLAMA
  SCOREDOM --> OLLAMA
  REC <--> GCALSYNC
  API --> AUDIT
  POLICY --> AUDIT
  WORKERS --> AUDIT
  WORKERS --> SCOREDOM
  UI --> SENTRY
```

## Diagram 3: Domain Interaction

```mermaid
flowchart LR
  VAC[Vacancy Management]
  CAND[Candidate Management]
  SCORE[AI Match Scoring]
  INT[Interview Management]
  FAIR[Interview Feedback Fairness Gate]
  OFFER[Offer Lifecycle]
  HIRE[Hiring Decision]
  EMP[Employee Profile]
  ONB[Onboarding]
  AUTO[HR Automation]
  NOTIFY[Notification Service]
  KPI[KPI and Audit]

  VAC --> SCORE
  CAND --> SCORE
  SCORE --> INT
  INT --> FAIR
  FAIR --> OFFER
  OFFER --> HIRE
  HIRE --> EMP
  EMP --> ONB
  VAC --> AUTO
  INT --> AUTO
  OFFER --> AUTO
  ONB --> AUTO
  AUTO -.notification.emit.-> NOTIFY

  VAC --> KPI
  CAND --> KPI
  SCORE --> KPI
  INT --> KPI
  HIRE --> KPI
  EMP --> KPI
  ONB --> KPI
  AUTO --> KPI
```

## Diagram 4: Candidate Screening and Shortlist Review Sequence

```mermaid
sequenceDiagram
  participant HR as HR
  participant UI as React.js + TypeScript UI
  participant API as API Gateway
  participant CAND as Candidate Service
  participant SCORE as Match Scoring Service
  participant Q as Celery/Redis
  participant WORKER as Match Scoring Worker
  participant OLL as Ollama

  HR->>UI: Select vacancy + candidate on `/`
  UI->>API: GET candidate context / parsed-analysis readiness
  API->>CAND: Read active document + parsed analysis status
  CAND-->>API: Ready or not-ready state
  UI->>API: POST /api/v1/vacancies/{vacancy_id}/match-scores {candidate_id}
  API->>SCORE: Validate scoring preconditions
  alt Parsed CV analysis is not ready
    SCORE-->>API: Reject with 409
    API-->>UI: Render localized retry guidance
  else Parsed CV analysis is ready
    SCORE->>Q: Enqueue `match_scoring` job or return active/latest job
    Q->>WORKER: Deliver job_id
    SCORE-->>API: Return queued/running/succeeded/failed payload
    API-->>UI: queued/running payload
    WORKER->>OLL: Score vacancy against parsed CV evidence
    OLL-->>WORKER: score + confidence + summary + evidence
    WORKER-->>API: Persist job state + score artifact
    UI->>API: GET /api/v1/vacancies/{vacancy_id}/match-scores/{candidate_id}
    API->>SCORE: Read latest job + score artifact
    SCORE-->>API: UI-ready score/status payload
    API-->>UI: Render shortlist review block
  end
```

Current implementation persists lifecycle state in `match_scoring_jobs` and UI-ready explainable
artifacts in `match_score_artifacts`. The parsed CV payload now remains profession-agnostic and
includes workplace history with held positions, education entries, normalized titles/dates, and
generic skills before scoring.

## Diagram 5: Interview Scheduling Sequence

```mermaid
sequenceDiagram
  participant HR as HR
  participant REV as Assigned Interviewer
  participant UI as React.js + TypeScript UI
  participant API as API Gateway
  participant INT as Interview Service
  participant PIPE as Pipeline Service
  participant EMP as Employee Domain
  participant GCA as Calendar Sync Service
  participant GCAL as Google Calendar
  participant C as Candidate

  HR->>UI: Propose interview slot
  UI->>API: POST /api/v1/vacancies/{vacancy_id}/interviews
  API->>INT: Validate stage, one-active-interview rule, and staff participants
  INT->>GCA: Enqueue calendar sync
  GCA->>GCAL: Create/Update event in calendars manually shared with the service account
  GCAL-->>GCA: synced | conflict | failed
  GCA-->>INT: Persist sync result
  INT-->>API: status + calendar_sync_status + invite metadata
  API-->>UI: Show sync state in HR workspace on /
  UI-->>HR: Copy candidate_invite_url after sync success
  HR->>C: Share invite link manually
  C->>UI: Open /candidate?interviewToken=...
  UI->>API: GET /api/v1/public/interview-registrations/{token}
  API-->>UI: Current invitation payload
  C->>UI: Confirm / Request reschedule / Decline
  UI->>API: POST public interview action
  API->>INT: Apply token-bound action
  INT-->>API: Updated interview state
  API-->>UI: Updated candidate-facing status
  REV->>UI: Open feedback block on `/` after interview end
  UI->>API: GET /api/v1/vacancies/{vacancy_id}/interviews/{interview_id}/feedback
  API->>INT: Read current-version panel summary
  INT-->>API: Summary + gate state
  REV->>UI: Submit PUT feedback/me
  UI->>API: PUT /api/v1/vacancies/{vacancy_id}/interviews/{interview_id}/feedback/me
  API->>INT: Upsert current interviewer feedback
  HR->>UI: Attempt interview -> offer transition
  UI->>API: POST /api/v1/pipeline/transitions
  API->>PIPE: Evaluate canonical transition
  PIPE->>INT: Read fairness-gate state for active interview
  INT-->>PIPE: passed | 409 reason code
  PIPE->>INT: Auto-provision offer draft on successful move to offer
  PIPE-->>API: transition created | blocked
  API-->>UI: Offer transition success or localized blocker
  HR->>UI: Maintain offer draft / mark sent
  UI->>API: GET/PUT /api/v1/vacancies/{vacancy_id}/offers/{candidate_id}
  API->>INT: Read or upsert persisted offer row
  INT-->>API: offer payload (`draft`/`sent`/`accepted`/`declined`)
  API-->>UI: Render offer lifecycle block on `/`
  HR->>UI: Record accepted or declined
  UI->>API: POST /api/v1/vacancies/{vacancy_id}/offers/{candidate_id}/accept|decline
  API->>INT: Validate `sent` state and persist decision metadata
  HR->>UI: Attempt offer -> hired or offer -> rejected transition
  UI->>API: POST /api/v1/pipeline/transitions
  API->>PIPE: Validate canonical transition + required offer status
  PIPE->>EMP: On `hired`, persist `hire_conversion` handoff from accepted offer + candidate snapshot
  EMP-->>PIPE: ready handoff persisted
  PIPE-->>API: transition created | 409 offer_not_accepted | 409 offer_not_declined
  API-->>UI: Terminal offer transition success or localized blocker
  HR->>UI: Bootstrap employee profile after successful hire
  UI->>API: POST /api/v1/employees
  API->>EMP: Resolve ready `hire_conversion` by vacancy_id + candidate_id
  EMP->>EMP: Validate frozen snapshots + resolve active onboarding template
  EMP->>EMP: Insert `employee_profiles + onboarding_runs(status=started)` in the same transaction
  EMP->>EMP: Materialize ordered `onboarding_tasks(status=pending)` from the active template
  EMP-->>API: employee profile payload + onboarding metadata | 404/409/422
  API-->>UI: Employee bootstrap success or localized blocker
```

The interview flow is now implemented from `docs/project/interview-planning-pass.md` and `docs/project/interview-feedback-fairness-pass.md`, and the downstream offer flow now stays on the same vacancy route tree without adding candidate auth or a new top-level route tree. In the current free-mode runtime, Google Calendar access is service-account based, each interviewer calendar is shared manually with that service account, candidate delivery still uses `candidate_invite_url` instead of Google guest invitations, the fairness guard stays on the existing `interview -> offer` transition, offer acceptance/decline remains staff-recorded in `/`, successful `offer -> hired` persists one durable `hire_conversion` handoff, the follow-on staff employee bootstrap runs on `POST /api/v1/employees` where `employee_profiles`, `onboarding_runs`, and materialized `onboarding_tasks` commit atomically against the current active template, the employee self-service portal stays on `/employee` plus `/api/v1/employees/me/onboarding*`, and HR/admin plus managers now observe onboarding progress on the existing `/` route through `GET /api/v1/onboarding/runs*`.

## Diagram 6: Onboarding Template Management Sequence

```mermaid
sequenceDiagram
  participant HR as HR/Admin
  participant UI as React.js + TypeScript UI
  participant API as API Gateway
  participant EMP as Employee Domain
  participant DB as PostgreSQL

  HR->>UI: Create or update onboarding checklist template
  UI->>API: POST/GET/PUT /api/v1/onboarding/templates
  API->>EMP: Validate staff permission + template payload
  EMP->>DB: Persist `onboarding_templates` + `onboarding_template_items`
  alt Name conflict or invalid checklist items
    EMP-->>API: 409 name_conflict | 422 template_invalid
    API-->>UI: Localized staff-facing blocker
  else Success
    EMP->>DB: Deactivate previous active template when new template is active
    EMP-->>API: Template payload with ordered checklist items
    API-->>UI: Current template state for later onboarding-task generation
  end
```

## Diagram 7: Onboarding Task Materialization and Backfill Sequence

```mermaid
sequenceDiagram
  participant HR as HR/Admin
  participant UI as React.js + TypeScript UI
  participant API as API Gateway
  participant EMP as Employee Domain
  participant DB as PostgreSQL

  HR->>UI: Bootstrap employee after successful hire or backfill legacy onboarding run
  alt New employee bootstrap
    UI->>API: POST /api/v1/employees
    API->>EMP: Resolve ready hire conversion + active template
    EMP->>DB: Persist `employee_profiles + onboarding_runs + onboarding_tasks`
    alt No active template
      EMP-->>API: 422 onboarding_template_not_configured
      API-->>UI: Localized blocker with no partial bootstrap rows
    else Success
      EMP-->>API: employee payload + onboarding metadata
      API-->>UI: Bootstrap success
    end
  else Legacy onboarding run backfill
    UI->>API: POST /api/v1/onboarding/runs/{onboarding_id}/tasks/backfill
    API->>EMP: Validate run exists and currently has zero tasks
    EMP->>DB: Insert ordered `onboarding_tasks` from active template snapshot
    EMP-->>API: task list | 404 run_not_found | 409 tasks_already_exist | 422 template_not_configured
    API-->>UI: Staff-facing backfill result
  end
  HR->>UI: Update assignment or SLA state
  UI->>API: PATCH /api/v1/onboarding/runs/{onboarding_id}/tasks/{task_id}
  API->>EMP: Validate task ownership and patch workflow fields
  EMP->>DB: Persist status/assignment/due_at and manage `completed_at`
  EMP-->>API: updated task payload
  API-->>UI: Current task state
```

## Diagram 8: Employee Self-Service Onboarding Portal Sequence

```mermaid
sequenceDiagram
  participant EMPU as Employee
  participant UI as React.js + TypeScript UI
  participant API as API Gateway
  participant EMP as Employee Domain
  participant DB as PostgreSQL

  EMPU->>UI: Open `/employee`
  UI->>API: GET /api/v1/employees/me/onboarding
  API->>EMP: Validate `employee_portal:read`
  EMP->>DB: Resolve `employee_profiles.staff_account_id`
  alt No direct link yet
    EMP->>DB: Reconcile exact `staff_accounts.email -> employee_profiles.email`
    alt No unique match
      EMP-->>API: 404 employee_profile_not_found | 409 employee_profile_identity_conflict
      API-->>UI: Localized employee-facing error state
    else Unique match
      EMP->>DB: Persist durable `staff_account_id` link
      EMP->>DB: Load onboarding run + ordered tasks
      EMP-->>API: portal payload + `can_update`
      API-->>UI: Render employee onboarding workspace
    end
  else Existing direct link
    EMP->>DB: Load onboarding run + ordered tasks
    EMP-->>API: portal payload + `can_update`
    API-->>UI: Render employee onboarding workspace
  end
  EMPU->>UI: Complete or reopen self-actionable task
  UI->>API: PATCH /api/v1/employees/me/onboarding/tasks/{task_id}
  API->>EMP: Validate employee ownership + self-actionable task rules
  alt Task is staff-managed or assigned to another actor
    EMP-->>API: 409 onboarding_task_not_actionable_by_employee
    API-->>UI: Localized employee-facing blocker
  else Task is actionable
    EMP->>DB: Persist `status` and manage `completed_at`
    EMP-->>API: updated task payload
    API-->>UI: Refresh task card state
  end
```

## Diagram 9: Onboarding Progress Dashboard Sequence

```mermaid
sequenceDiagram
  participant STAFF as HR/Admin or Manager
  participant UI as React.js + TypeScript UI
  participant API as API Gateway
  participant EMP as Employee Domain
  participant DB as PostgreSQL

  STAFF->>UI: Open `/` and load the onboarding visibility block
  UI->>API: GET /api/v1/onboarding/runs?search&task_status&overdue_only
  API->>EMP: Validate `onboarding_dashboard:read`
  EMP->>DB: Load onboarding runs + employee profiles + materialized tasks
  alt Manager actor
    EMP->>EMP: Keep only runs with `assigned_role=manager` or `assigned_staff_id=<actor>` for the embedded manager block
  else HR/Admin actor
    EMP->>EMP: Keep full run set for the embedded HR workspace panel
  end
  EMP->>EMP: Build summary counters, progress percentages, and filtered list rows
  EMP-->>API: dashboard list payload
  API-->>UI: Render summary chips + run table inside the current workspace
  STAFF->>UI: Select onboarding run
  UI->>API: GET /api/v1/onboarding/runs/{onboarding_id}
  API->>EMP: Re-validate visibility for requested run
  alt Run is missing or not visible to actor
    EMP-->>API: 404 onboarding_run_not_found
    API-->>UI: Localized dashboard error
  else Run is visible
    EMP->>DB: Load ordered onboarding tasks for selected run
    EMP-->>API: detail payload with employee summary + tasks
    API-->>UI: Render detail panel on the same `/` route
  end
```

## Diagram 9A: Manager Workspace Sequence

```mermaid
sequenceDiagram
  participant MGR as Manager
  participant UI as React.js + TypeScript UI
  participant API as API Gateway
  participant VAC as Recruitment Domain
  participant EMP as Employee Domain
  participant DB as PostgreSQL

  MGR->>UI: Open `/`
  UI->>API: GET /api/v1/vacancies/manager-workspace
  API->>VAC: Validate `manager_workspace:read`
  VAC->>DB: Load vacancies where `hiring_manager_staff_id=<actor>`
  VAC->>DB: Load latest transitions, active interviews, and candidate profiles for visible vacancies
  VAC->>VAC: Build hiring summary + ordered vacancy list
  VAC-->>API: overview payload
  API-->>UI: Render hiring summary + vacancy list

  UI->>API: GET /api/v1/vacancies/{vacancy_id}/manager-workspace/candidates
  API->>VAC: Re-validate vacancy ownership scope
  alt Vacancy is missing or outside manager scope
    VAC-->>API: 404 manager_workspace_vacancy_not_found
    API-->>UI: Localized manager workspace error
  else Vacancy is visible
    VAC->>DB: Load latest pipeline rows, candidate profiles, and active interviews
    VAC-->>API: candidate snapshot payload
    API-->>UI: Render read-only candidate/pipeline snapshot
    UI->>API: GET /api/v1/onboarding/runs?search&task_status&overdue_only
    API->>EMP: Validate `onboarding_dashboard:read`
    EMP->>DB: Load manager-scoped onboarding runs
    EMP-->>API: onboarding dashboard payload
    API-->>UI: Render embedded onboarding visibility block
  end
```

## Diagram 9B: Accountant Workspace Sequence

```mermaid
sequenceDiagram
  participant ACC as Accountant
  participant UI as React.js + TypeScript UI
  participant API as API Gateway
  participant FIN as Finance Adapter
  participant EMP as Employee Domain Tables
  participant AUD as Audit Service

  ACC->>UI: Open `/`
  UI->>API: GET /api/v1/accounting/workspace?search&limit&offset
  API->>FIN: Validate `accounting:read`
  FIN->>EMP: Load `employee_profiles + onboarding_runs + onboarding_tasks`
  FIN->>FIN: Keep only rows with `assigned_role=accountant` or `assigned_staff_id=<actor>`
  FIN->>FIN: Build deterministic ordered row model
  FIN->>AUD: accounting_workspace:read success
  FIN-->>API: paginated accountant workspace payload
  API-->>UI: Render read-only table and export actions

  ACC->>UI: Export current filtered scope
  UI->>API: GET /api/v1/accounting/workspace/export?format=csv|xlsx&search
  API->>FIN: Re-validate `accounting:read`
  FIN->>EMP: Reuse the same filtered row model
  FIN->>FIN: Render CSV or XLSX with identical columns
  FIN->>AUD: accounting_export:download success
  FIN-->>API: Attachment bytes + filename
  API-->>UI: Browser download starts
```

## Diagram 9C: Role-Specific Notification Sequence

```mermaid
sequenceDiagram
  participant STAFF as HR/Admin
  participant API as API Gateway
  participant VAC as Vacancy Service
  participant EMP as Onboarding Task Service
  participant NOTIFY as Notification Service
  participant DB as PostgreSQL
  participant USER as Manager or Accountant
  participant UI as React.js + TypeScript UI

  alt Vacancy ownership change
    STAFF->>API: PATCH /api/v1/vacancies/{vacancy_id}
    API->>VAC: Apply `hiring_manager_staff_id` update
    VAC->>NOTIFY: Emit manager notification when owner changed
  else Onboarding assignment change
    STAFF->>API: PATCH /api/v1/onboarding/runs/{onboarding_id}/tasks/{task_id}
    API->>EMP: Apply assignment/status/SLA patch
    EMP->>NOTIFY: Emit manager/accountant notification when recipients changed
  end
  NOTIFY->>DB: Persist deduped `notifications` rows in the same transaction

  USER->>UI: Open `/`
  UI->>API: GET /api/v1/notifications/digest
  API->>NOTIFY: Validate recipient scope + compute digest on demand
  NOTIFY->>DB: Load unread rows + current vacancy/task counters
  NOTIFY-->>API: digest payload
  API-->>UI: Render summary chips

  UI->>API: GET /api/v1/notifications?status=unread&limit&offset
  API->>NOTIFY: Validate recipient scope + list unread items
  NOTIFY-->>API: recipient-owned notifications only
  API-->>UI: Render unread notifications

  USER->>UI: Mark one notification as read
  UI->>API: POST /api/v1/notifications/{notification_id}/read
  API->>NOTIFY: Re-validate `recipient_staff_id=<actor>`
  NOTIFY->>DB: Set `read_at` for that recipient row
  API-->>UI: Updated read state
```

## Diagram 10: Deployment and Trust Boundaries

```mermaid
flowchart TB
  subgraph ClientZone[Client Zone]
    BROWSER[Browser]
  end

  subgraph AppZone[Application Zone]
    WEB[React.js + TypeScript Web App]
    APIGW[API Gateway]
    SERVICES[Domain Services + Workers]
  end

  subgraph DataZone[Data Zone]
    PSQL[(PostgreSQL)]
    STORE[(Object Storage)]
    BUS[(Queue/Event Bus)]
  end

  subgraph ExternalZone[External Zone]
    OLLX[Ollama]
    GCALX[Google Calendar]
    SENTRYX[Sentry]
  end

  BROWSER --> WEB
  WEB --> APIGW
  APIGW --> SERVICES
  SERVICES --> PSQL
  SERVICES --> STORE
  SERVICES --> BUS
  SERVICES --> OLLX
  SERVICES <--> GCALX
  WEB --> SENTRYX
```

## Diagram 11: Public Vacancy Application Sequence (v1)

```mermaid
sequenceDiagram
  participant C as Candidate
  participant UI as React.js + TypeScript UI
  participant API as API Gateway
  participant VAC as Vacancy Application Service
  participant RL as Redis Rate Limiter
  participant DB as PostgreSQL
  participant OBJ as MinIO
  participant Q as Celery/Redis
  participant AUD as Audit/Monitoring

  C->>UI: Fill contacts + upload CV
  UI->>API: POST /api/v1/vacancies/{vacancy_id}/applications
  API->>VAC: validate anti-abuse + vacancy + cv payload
  VAC->>RL: check buckets (ip, ip+vacancy, email+vacancy)
  RL-->>VAC: allow / reject(429)
  VAC->>DB: check honeypot + dedup + cooldown guards
  DB-->>VAC: allow / reject(409|422)
  VAC->>AUD: write success/failure reason code + counters
  VAC->>DB: upsert candidate_profiles
  VAC->>OBJ: put CV object (SSE-S3)
  VAC->>DB: insert candidate_documents + pipeline_transitions (None->applied) + cv_parsing_jobs(queued)
  VAC->>Q: enqueue process_cv_parsing_job(job_id)
  API-->>UI: 200/201 with candidate_id + parsing_job_id or 409/422/429 with diagnostics
  UI->>UI: persist sessionStorage tracking context
  UI->>API: GET /api/v1/public/cv-parsing-jobs/{job_id}
  API-->>UI: status (queued/running/succeeded/failed)
  UI->>API: GET /api/v1/public/cv-parsing-jobs/{job_id}/analysis (when ready)
  API-->>UI: parsed profile + evidence snippets
```

## Diagram 12: Delivery Pipeline (GitHub + CI)

```mermaid
flowchart LR
  DEV[Developer Branch\nfeature/TASK-*] --> PR[Pull Request to main]
  PR --> REV[Solo: self-review\nTeam: peer approvals]
  REV --> CI[GitHub Actions CI]

  subgraph Checks
    DOCS[docs-check]
    BE[backend lint+test via uv]
    FE[frontend lint+test]
    OAPI[openapi freeze check]
    FECG[frontend api typegen check]
    BSMOKE[compose browser smoke]
  end

  CI --> DOCS
  CI --> BE
  CI --> FE
  CI --> OAPI
  CI --> FECG
  CI --> BSMOKE

  DOCS --> MERGE[Squash Merge]
  BE --> MERGE
  FE --> MERGE
  OAPI --> MERGE
  FECG --> MERGE
  BSMOKE --> MERGE
  MERGE --> CLOSEOUT[Post-merge closeout\ncheck linked issues\nclose resolved issues\nsync docs/project/tasks.md]
  CLOSEOUT --> MAIN[Protected main]
```

## Diagram 13: Docker Compose Runtime Topology (Phase 1)

```mermaid
flowchart TB
  subgraph Compose[Docker Compose]
    FE[frontend container\nReact + Vite dev server]
    BE[backend container\nFastAPI API]
    WKR[backend-worker container\nCelery worker\ncv_parsing/match_scoring/interview_sync]
    DB[(postgres container :5432)]
    OBJ[(minio container :9000/:9001)]
    MQ[(redis container :6379)]
    DBINIT[postgres-init one-shot job]
    MIG[backend-migrate one-shot job]
    MINIT[minio-init one-shot job]
    subgraph AILOC[optional ai-local profile]
      OLL[ollama container\ninternal :11434\npersistent ollama_data]
      OINIT[ollama-init one-shot\npull MATCH_SCORING_MODEL_NAME]
    end
  end

  USER[Chrome Browser] --> FE
  FE --> BE
  DBINIT --> DB
  MIG --> DB
  MINIT --> OBJ
  BE --> DB
  BE --> OBJ
  BE --> MQ
  WKR --> DB
  WKR --> MQ
  WKR --> OBJ
  OINIT --> OLL
  BE -. ai-local only .-> OLL
  WKR -. ai-local only .-> OLL
  BE --> EXOLL[External host Ollama default\nhost.docker.internal:11434]
  WKR --> EXOLL
  BE <--> GCAL[Google Calendar]
  WKR <--> GCAL
```

Default compose startup keeps the external-host Ollama path, while the optional `ai-local`
profile switches `backend` and `backend-worker` to compose-local Ollama without publishing the
Ollama port on the host.

## Diagram 14: Authentication and Session Lifecycle Sequence

```mermaid
sequenceDiagram
  participant U as Staff User
  participant A as Admin/HR
  participant UI as React.js + TypeScript UI
  participant API as API Gateway
  participant AUTH as Auth and Access Service
  participant DNL as Redis Denylist
  participant DB as PostgreSQL
  participant AUD as Audit Service

  A->>API: POST /api/v1/admin/employee-keys
  API->>DB: issue one-time employee_key (ttl=7d)
  API->>AUD: admin.employee_key:create

  U->>UI: Register account
  UI->>API: POST /api/v1/auth/register (login, email, password, employee_key)
  API->>AUTH: Validate key + create staff account
  API->>AUD: auth.register

  U->>UI: Sign in
  UI->>API: POST /api/v1/auth/login (identifier, password)
  API->>AUTH: Issue access/refresh JWT pair (UUID sub/sid/jti)
  API->>AUD: Write auth.login (success/failure, correlation_id)
  AUTH-->>UI: access_token + refresh_token

  U->>UI: Open protected page
  UI->>API: Authorization: Bearer access_token
  API->>AUTH: Validate access token claims
  AUTH->>DNL: Check jti/sid absence
  AUTH-->>API: Auth context (subject, role, sid)
  API-->>UI: Protected resource

  U->>UI: Refresh session
  UI->>API: POST /api/v1/auth/refresh (refresh_token)
  API->>AUTH: Validate refresh token + rotate
  API->>AUD: Write auth.refresh (success/failure, correlation_id)
  AUTH->>DNL: Deny old refresh jti until exp
  AUTH-->>UI: New access_token + new refresh_token

  U->>UI: Logout
  UI->>API: POST /api/v1/auth/logout (Bearer access_token)
  API->>AUTH: Revoke token/session window
  API->>AUD: Write auth.logout (success, correlation_id)
  AUTH->>DNL: Deny access jti + session sid
  AUTH-->>UI: 204 No Content
```

## Diagram 15: Unified Access Enforcement and Audit Flow

```mermaid
flowchart LR
  subgraph APIPath[API Request Path]
    REQ[HTTP Request]
    AUTHCTX[Auth Context]
    DEP[require_permission]
    EVAL[evaluate_permission]
    APIAUD[Audit source=api]
    APIRES[Route Handler or 403]
    AUDREAD[Audit read handler\nGET /api/v1/audit/events]
    AUDWRITE[Audit business event\naudit.event:list]
  end

  subgraph JobPath[Background Job Path]
    JOB[Job Command]
    JOBROLE[Job Actor/Role]
    ENF[enforce_background_permission]
    JOBAUD[Audit source=job]
    JOBRES[Job Step or BackgroundAccessDeniedError]
  end

  STORE[(PostgreSQL audit_events)]

  REQ --> AUTHCTX --> DEP --> EVAL --> APIRES
  DEP --> APIAUD --> STORE
  APIRES --> AUDREAD
  AUDREAD -->|SELECT| STORE
  AUDREAD -.after response build.-> AUDWRITE -->|INSERT| STORE
  JOB --> JOBROLE --> ENF --> EVAL --> JOBRES
  ENF --> JOBAUD --> STORE
```

## Diagram 15B: Audit + KPI Export Attachment Flow

```mermaid
sequenceDiagram
  participant ACT as Staff Actor
  participant UI as React.js + TypeScript UI
  participant API as API Gateway
  participant AUDREAD as Audit Read Service
  participant RPT as KPI Snapshot Service
  participant DB as PostgreSQL
  participant AUD as Audit Service

  alt Audit evidence export (admin-only)
    ACT->>UI: Export audit events
    UI->>API: GET /api/v1/audit/events/export?format=csv|jsonl&filters
    API->>AUD: Validate `audit:read` (writes decision audit)
    API->>AUDREAD: Query audit events (bounded, deterministic)
    AUDREAD->>DB: SELECT audit_events
    AUDREAD-->>API: rows
    API->>API: Render CSV/JSONL bytes
    API->>AUD: Write audit.event:export (after render)
    API-->>UI: Attachment download starts
  else KPI snapshot export (leader/admin)
    ACT->>UI: Export KPI snapshot
    UI->>API: GET /api/v1/reporting/kpi-snapshots/export?period_month&format=csv|xlsx
    API->>AUD: Validate `kpi_snapshot:read` (writes decision audit)
    API->>RPT: Load stored snapshot (no live aggregation fallback)
    RPT->>DB: SELECT kpi_snapshots
    RPT-->>API: metrics
    API->>API: Render CSV/XLSX bytes
    API->>AUD: Write kpi_snapshot:export (after render)
    API-->>UI: Attachment download starts
  end
```

## Diagram 16: Candidate Profile and CV Upload Sequence

```mermaid
sequenceDiagram
  participant ACT as Staff Actor (admin/hr)
  participant API as API Gateway
  participant CAND as Candidate Service
  participant DB as PostgreSQL
  participant OBJ as MinIO
  participant Q as Celery/Redis
  participant AUD as Audit Service

  ACT->>API: POST /api/v1/candidates
  API->>CAND: validate RBAC + ownership policy
  CAND->>DB: insert candidate_profiles
  CAND->>AUD: candidate_profile:create success
  API-->>ACT: candidate profile payload

  ACT->>API: POST /api/v1/candidates/{id}/cv (multipart + checksum)
  API->>CAND: validate RBAC + ownership + mime/size/checksum
  CAND->>OBJ: put object (SSE-S3)
  CAND->>DB: candidate_documents upsert(active) + cv_parsing_jobs queued
  CAND->>Q: enqueue process_cv_parsing_job(job_id)
  CAND->>AUD: candidate_cv:upload success
  API-->>ACT: CV metadata payload
```

## Diagram 17: Pipeline Transition Validator Flow

```mermaid
flowchart LR
  REQ[POST /api/v1/pipeline/transitions] --> RBAC[require_permission pipeline:transition]
  RBAC --> LOAD[Load vacancy + candidate + latest transition]
  LOAD --> CURR[Resolve from_stage from append-only history]
  CURR --> VAL{Canonical transition allowed?}
  VAL -->|No| ERR[422 Unprocessable Entity]
  VAL -->|Yes| TARGET{Target stage}
  TARGET -->|offer| FAIR{Fairness gate passed?}
  FAIR -->|No| ERR409A[409 Fairness reason code]
  FAIR -->|Yes| OFFERBUNDLE[Atomically insert pipeline_transitions row + ensure offer draft]
  TARGET -->|hired/rejected| OFFERCHK{Offer status compatible?}
  OFFERCHK -->|No| ERR409B[409 offer_not_accepted / offer_not_declined]
  OFFERCHK -->|Yes| RESOLVE{Target is hired?}
  RESOLVE -->|Yes| HIREBUNDLE[Atomically insert hired transition + hire_conversion handoff]
  RESOLVE -->|No, rejected| APPEND[Insert pipeline_transitions row]
  TARGET -->|other| APPEND
  OFFERBUNDLE --> AUD[Audit pipeline:transition success]
  HIREBUNDLE --> AUD
  APPEND --> AUD[Audit pipeline:transition success]
  AUD --> RES[200 Transition response]
```

## Diagram 18: Async CV Parsing Worker Lifecycle

```mermaid
flowchart LR
  Q[queued job] --> R[running claim]
  R --> L[load candidate document from object storage]
  L --> T{mime type}
  T -->|application/pdf| PDF[extract native PDF text]
  T -->|application/vnd.openxmlformats-officedocument.wordprocessingml.document| DOCX[extract native DOCX text]
  PDF --> N[RU/EN normalization + profession-agnostic profile enrichment + evidence mapping]
  DOCX --> N
  N --> P[persist parsed_profile_json + evidence_json + detected_language + parsed_at]
  P --> S[succeeded]
  L --> F[failed]
  PDF -->|broken or empty text| F
  DOCX -->|broken or empty text| F
  F --> RET{attempt_count < max_attempts}
  RET -->|yes| R
  RET -->|no| TF[terminal failed]
```

Current implementation keeps evidence offsets anchored to the extracted text used for normalization,
persists profession-agnostic workplaces with held positions plus education/title/date/skills
artifacts inside `parsed_profile_json`, and populates PDF `page` numbers when the extractor can
resolve the matched range.

## Diagram 19: Admin Route Guard and Redirect Flow (ADMIN-01)

```mermaid
flowchart LR
  USER[User opens /admin] --> GUARD[Frontend AdminGuard]
  GUARD --> TOKEN{Access token present?}
  TOKEN -->|No| R401[Redirect /access-denied?reason=unauthorized]
  TOKEN -->|Yes| ROLE{Role == admin?}
  ROLE -->|No| R403[Redirect /access-denied?reason=forbidden]
  ROLE -->|Yes| ADMIN[Render Admin Shell with staff, key, candidate, vacancy, pipeline, and audit consoles]

  GUARD --> TAGS[Sentry tags: workspace=admin, role, route]
  TAGS --> SENTRY[Sentry]
```

## Diagram 20: Admin Staff Management Flow (ADMIN-02)

```mermaid
sequenceDiagram
  participant ADM as Admin User
  participant UI as React Admin Staff Screen (/admin/staff)
  participant API as Admin Router
  participant SRV as Admin Service
  participant DAO as AdminStaffAccountDAO
  participant AUD as Audit Service

  ADM->>UI: Open /admin/staff
  UI->>API: GET /api/v1/admin/staff?limit&offset&search&role&is_active
  API->>SRV: list_staff_accounts(...)
  SRV->>DAO: list_accounts + count_accounts
  DAO-->>SRV: items + total
  SRV-->>API: AdminStaffListResponse
  API->>AUD: admin.staff:list success/failure
  API-->>UI: 200 list payload or 422

  ADM->>UI: Update row role/is_active
  UI->>API: PATCH /api/v1/admin/staff/{staff_id}
  API->>SRV: update_staff_account(...)
  SRV->>DAO: get_by_id + count_active_admins + update_account_fields
  SRV-->>API: StaffResponse or 404/409/422
  API->>AUD: admin.staff:update success/failure + reason_code
  API-->>UI: updated row or localized error message

  Note over SRV: Strict guard:\n- self-demotion/self-disable forbidden\n- last-active-admin demotion/disable forbidden
```

## Diagram 21: Employee Key Lifecycle Management Flow (ADMIN-03)

```mermaid
sequenceDiagram
  participant ADM as Admin/HR User
  participant UI as React Admin Employee Keys Screen (/admin/employee-keys)
  participant API as Admin Router
  participant SRV as Admin Service
  participant DAO as AdminEmployeeRegistrationKeyDAO
  participant AUTH as Auth Service (register path)
  participant AUD as Audit Service

  ADM->>UI: Open /admin/employee-keys
  UI->>API: GET /api/v1/admin/employee-keys?limit&offset&filters
  API->>SRV: list_employee_keys(...)
  SRV->>DAO: list_keys + count_keys
  DAO-->>SRV: key rows + total
  SRV-->>API: AdminEmployeeKeyListResponse (status=active|used|expired|revoked)
  API->>AUD: admin.employee_key:list success/failure
  API-->>UI: paginated list payload

  ADM->>UI: Create key
  UI->>API: POST /api/v1/admin/employee-keys
  API->>SRV: create_employee_key(...)
  SRV->>DAO: create_key(...)
  API->>AUD: admin.employee_key:create success/failure
  API-->>UI: EmployeeRegistrationKeyResponse

  ADM->>UI: Revoke active key
  UI->>API: POST /api/v1/admin/employee-keys/{key_id}/revoke
  API->>SRV: revoke_employee_key(...)
  SRV->>DAO: get_by_id + revoke_key
  SRV-->>API: 200 or 404/409 reason-code
  API->>AUD: admin.employee_key:revoke success/failure + reason
  API-->>UI: revoked row or localized error

  Note over AUTH: Register path consumes only keys where\nused_at=null, revoked_at=null, expires_at>now
```

## Diagram 22: Frontend Observability Flow (TASK-11-10)

```mermaid
flowchart LR
  USER[User opens critical route] --> ROUTE[Observed route: /, /employee, /candidate, /login, /admin, /admin/staff, /admin/employee-keys, /admin/candidates, /admin/vacancies, /admin/pipeline, /admin/audit]
  ROUTE --> TAGS[Sentry tags: workspace=hr|manager|accountant|employee|candidate|auth|admin, role, route]
  TAGS --> SENTRY[Sentry]

  ROUTE --> UI[React page and query or mutation logic]
  UI --> HTTP[Shared apiRequest wrapper]
  HTTP -->|Network error or non-2xx| CAPTURE[Capture exception with method/status/path]
  CAPTURE --> SENTRY

  UI -->|Render throws| BOUNDARY[Top-level AppErrorBoundary]
  BOUNDARY --> FALLBACK[Localized fallback UI]
  BOUNDARY --> SENTRY

  CONFIG[VITE_SENTRY_* env config] --> SENTRY
```

## Diagram 23: KPI Snapshot Aggregation Flow (TASK-10-01)

```mermaid
flowchart LR
  subgraph Domains[Transactional Domains]
    VAC[Vacancies]
    PIPE[Pipeline Transitions]
    INT[Interviews]
    OFFER[Offers]
    HIRE[Hire Conversions]
    ONB[Onboarding Runs/Tasks]
    AUTO_METRIC[(automation_metric_events)]
  end

  subgraph Reporting[Reporting]
    REBUILD[Admin Rebuild Request]
    AGG[KPI Aggregation Service]
    SNAP[(kpi_snapshots)]
  READ[Snapshot Read API (leader/admin)]
  end

  REBUILD --> AGG
  VAC --> AGG
  PIPE --> AGG
  INT --> AGG
  OFFER --> AGG
  HIRE --> AGG
  ONB --> AGG
  AUTO_METRIC --> AGG
  AGG --> SNAP
  READ --> SNAP
```

## Diagram 24: Automation Execution Logging and KPI Event Flow (TASK-08-04)

```mermaid
sequenceDiagram
  participant DOM as Domain Service
  participant EXEC as AutomationActionExecutor
  participant RUN as automation_execution_runs
  participant ACT as automation_action_executions
  participant MET as automation_metric_events
  participant NOTIF as notifications
  participant RPT as KPI Snapshot Service
  participant OPS as Ops API (admin/hr)

  DOM->>EXEC: handle_event(event, correlation_id)
  EXEC->>RUN: INSERT run(status=running, trace_id)
  EXEC->>EXEC: evaluate rules -> plan[]
  EXEC->>NOTIF: INSERT notification rows (dedupe-safe)
  EXEC->>ACT: INSERT action rows (succeeded/deduped/failed)
  EXEC->>MET: INSERT metric row(outcome, counts)
  EXEC->>RUN: UPDATE run(status, counts, error)
  OPS->>RUN: list/view runs (filters)
  OPS->>ACT: list/view actions
  RPT->>MET: aggregate counts for monthly KPI rebuild
```

Automation execution logs remain the operator-facing troubleshooting source of truth, while
`automation_metric_events` is the durable KPI event stream used by reporting to compute
`total_hr_operations_count`, `automated_hr_operations_count`, and the derived share metric.

## Diagram 25: Admin Control Plane Slice (ADMIN-04)

```mermaid
flowchart LR
  USER[Admin opens /admin] --> SHELL[Admin Shell]
  SHELL --> CANDS[/admin/candidates]
  SHELL --> VACS[/admin/vacancies]
  SHELL --> PIPE[/admin/pipeline]
  SHELL --> AUD[/admin/audit]

  CANDS --> CAPI[GET/POST/PUT /api/v1/candidates*]
  VACS --> VAPI[GET/POST/PUT /api/v1/vacancies*]
  PIPE --> PAPI[GET /api/v1/vacancies + GET/POST /api/v1/pipeline/transitions]
  AUD --> AAPI[GET /api/v1/audit/events + export csv/jsonl/xlsx]

  CANDS --> TAGS[Sentry route tags: route=/admin/candidates]
  VACS --> TAGS
  PIPE --> TAGS
  AUD --> TAGS
```

The ADMIN-04 slice stays frontend-first over the existing backend contracts. It keeps the control
plane non-destructive, avoids a new admin backend namespace, and uses the audit export endpoint for
read-only evidence downloads in CSV, JSONL, and XLSX formats.
