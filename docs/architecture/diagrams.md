# Architecture Diagrams

## Last Updated
- Date: 2026-03-05
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
    POLICY[Access Policy Evaluator]
    REC[Recruitment Services]
    EMPDOM[Employee Services]
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
  API --> POLICY
  API --> REC
  API --> EMPDOM
  API --> HROPS
  API --> ANALYTICS
  WORKERS --> POLICY
  AUTH --> REDISDNL
  AUTH -.imports.-> COREPKG
  POLICY -.imports.-> COREPKG
  REC -.imports.-> COREPKG
  EMPDOM -.imports.-> COREPKG
  HROPS -.imports.-> COREPKG
  ANALYTICS -.imports.-> COREPKG

  REC --> DB
  EMPDOM --> DB
  HROPS --> DB
  ANALYTICS --> DB
  AUDIT --> DB

  REC --> OBJ
  REC --> QUEUE
  HROPS --> QUEUE
  ANALYTICS --> QUEUE

  REC --> OLLAMA
  REC <--> GCALSYNC
  API --> AUDIT
  POLICY --> AUDIT
  WORKERS --> AUDIT
  UI --> SENTRY
```

## Diagram 3: Domain Interaction

```mermaid
flowchart LR
  VAC[Vacancy Management]
  CAND[Candidate Management]
  SCORE[AI Match Scoring]
  INT[Interview Management]
  HIRE[Hiring Decision]
  EMP[Employee Profile]
  ONB[Onboarding]
  AUTO[HR Automation]
  KPI[KPI and Audit]

  VAC --> SCORE
  CAND --> SCORE
  SCORE --> INT
  INT --> HIRE
  HIRE --> EMP
  EMP --> ONB
  VAC --> AUTO
  INT --> AUTO
  ONB --> AUTO

  VAC --> KPI
  CAND --> KPI
  SCORE --> KPI
  INT --> KPI
  HIRE --> KPI
  EMP --> KPI
  ONB --> KPI
  AUTO --> KPI
```

## Diagram 4: Candidate Screening Sequence

```mermaid
sequenceDiagram
  participant HR as HR
  participant UI as React.js + TypeScript UI
  participant API as API Gateway
  participant CAND as Candidate Service
  participant CV as CV Processing Worker
  participant SCORE as Match Scoring Worker
  participant OLL as Ollama

  HR->>UI: Upload CV and assign vacancy
  UI->>API: Create/Update candidate profile
  API->>CAND: Persist candidate and CV metadata
  CAND-->>CV: Emit cv_parsing_requested
  CV-->>CAND: Store parsed CV structure
  CAND-->>SCORE: Emit match_scoring_requested
  SCORE->>OLL: Request score and explanation
  OLL-->>SCORE: Return match result
  SCORE-->>CAND: Save score + confidence
  CAND-->>API: Candidate ready for review
  API-->>UI: Show shortlist recommendation
```

## Diagram 5: Interview Scheduling Sequence

```mermaid
sequenceDiagram
  participant HR as HR
  participant UI as React.js + TypeScript UI
  participant API as API Gateway
  participant INT as Interview Service
  participant GCA as Calendar Sync Service
  participant GCAL as Google Calendar

  HR->>UI: Propose interview slot
  UI->>API: Create interview request
  API->>INT: Validate stage and participants
  INT->>GCA: Sync interview event
  GCA->>GCAL: Create/Update calendar event
  GCAL-->>GCA: Event id and status
  GCA-->>INT: Reconciliation result
  INT-->>API: Interview scheduled
  API-->>UI: Confirm schedule and invitations
```

## Diagram 6: Deployment and Trust Boundaries

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

## Diagram 7: Public Vacancy Application Sequence (v1)

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
  API-->>UI: 201 Created or 409/422/429 with diagnostics
```

## Diagram 8: Delivery Pipeline (GitHub + CI)

```mermaid
flowchart LR
  DEV[Developer Branch\nfeature/TASK-*] --> PR[Pull Request to main]
  PR --> REV[2 Reviewers Required]
  REV --> CI[GitHub Actions CI]

  subgraph Checks
    DOCS[docs-check]
    BE[backend lint+test via uv]
    FE[frontend lint+test]
    OAPI[openapi freeze check]
    FECG[frontend api typegen check]
  end

  CI --> DOCS
  CI --> BE
  CI --> FE
  CI --> OAPI
  CI --> FECG

  DOCS --> MERGE[Squash Merge]
  BE --> MERGE
  FE --> MERGE
  OAPI --> MERGE
  FECG --> MERGE
  MERGE --> MAIN[Protected main]
```

## Diagram 9: Docker Compose Runtime Topology (Phase 1)

```mermaid
flowchart TB
  subgraph Compose[Docker Compose]
    FE[frontend container\nReact + Vite preview]
    BE[backend container\nFastAPI API]
    WKR[backend-worker container\nCelery worker]
    DB[(postgres container :5432)]
    OBJ[(minio container :9000/:9001)]
    MQ[(redis container :6379)]
    INIT[minio-init one-shot job]
  end

  USER[Chrome Browser] --> FE
  FE --> BE
  BE --> DB
  BE --> OBJ
  BE --> MQ
  WKR --> DB
  WKR --> MQ
  WKR --> OBJ
  INIT --> OBJ
  BE --> OLL[Ollama]
  BE <--> GCAL[Google Calendar]
```

## Diagram 10: Authentication and Session Lifecycle Sequence

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

## Diagram 11: Unified Access Enforcement and Audit Flow

```mermaid
flowchart LR
  subgraph APIPath[API Request Path]
    REQ[HTTP Request]
    AUTHCTX[Auth Context]
    DEP[require_permission]
    EVAL[evaluate_permission]
    APIAUD[Audit source=api]
    APIRES[Route Handler or 403]
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
  JOB --> JOBROLE --> ENF --> EVAL --> JOBRES
  ENF --> JOBAUD --> STORE
```

## Diagram 12: Candidate Profile and CV Upload Sequence

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

## Diagram 13: Pipeline Transition Validator Flow

```mermaid
flowchart LR
  REQ[POST /api/v1/pipeline/transitions] --> RBAC[require_permission pipeline:transition]
  RBAC --> LOAD[Load vacancy + candidate + latest transition]
  LOAD --> CURR[Resolve from_stage from append-only history]
  CURR --> VAL{Canonical transition allowed?}
  VAL -->|No| ERR[422 Unprocessable Entity]
  VAL -->|Yes| APPEND[Insert pipeline_transitions row]
  APPEND --> AUD[Audit pipeline:transition success]
  AUD --> RES[200 Transition response]
```

## Diagram 14: Async CV Parsing Worker Lifecycle

```mermaid
stateDiagram-v2
  [*] --> queued
  queued --> running: celery task claims job
  running --> succeeded: parse + persist success
  running --> failed: parser/storage error
  failed --> running: retry if attempt_count < max_attempts
  failed --> [*]: terminal when attempts exhausted
  succeeded --> [*]
```

## Diagram 15: Admin Route Guard and Redirect Flow (ADMIN-01)

```mermaid
flowchart LR
  USER[User opens /admin] --> GUARD[Frontend AdminGuard]
  GUARD --> TOKEN{Access token present?}
  TOKEN -->|No| R401[Redirect /access-denied?reason=unauthorized]
  TOKEN -->|Yes| ROLE{Role == admin?}
  ROLE -->|No| R403[Redirect /access-denied?reason=forbidden]
  ROLE -->|Yes| ADMIN[Render Admin Shell]

  GUARD --> TAGS[Sentry tags: workspace=admin, role, route]
  TAGS --> SENTRY[Sentry]
```
