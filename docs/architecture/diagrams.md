# Architecture Diagrams

## Last Updated
- Date: 2026-03-04
- Updated by: architect

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
    REC[Recruitment Services]
    EMPDOM[Employee Services]
    HROPS[HR Automation Services]
    ANALYTICS[Reporting and KPI Services]
    AUDIT[Audit Service]
  end

  subgraph Infra[Infrastructure]
    DB[(PostgreSQL)]
    OBJ[(Object Storage)]
    QUEUE[(Queue/Event Bus)]
  end

  subgraph Ext[External Integrations]
    OLLAMA[Ollama Adapter]
    GCALSYNC[Google Calendar Adapter]
    SENTRY[Sentry]
  end

  UI --> API
  API --> REC
  API --> EMPDOM
  API --> HROPS
  API --> ANALYTICS

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

## Diagram 7: Candidate Self-Service Sequence (v1)

```mermaid
sequenceDiagram
  participant C as Candidate
  participant UI as React.js + TypeScript UI
  participant API as API Gateway
  participant CAND as Candidate Service
  participant INT as Interview Service

  C->>UI: Register and fill profile information
  UI->>API: Submit profile + confirmation flag
  API->>CAND: Save candidate profile
  C->>UI: Upload CV
  UI->>API: Upload CV metadata/file reference
  API->>CAND: Persist CV attachment
  C->>UI: Register for interview slot
  UI->>API: Send interview registration request
  API->>INT: Reserve candidate interview slot
  INT-->>API: Registration status
  API-->>UI: Confirmation to candidate
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
  end

  CI --> DOCS
  CI --> BE
  CI --> FE

  DOCS --> MERGE[Squash Merge]
  BE --> MERGE
  FE --> MERGE
  MERGE --> MAIN[Protected main]
```
