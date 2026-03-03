# Operations Runbook

## Last Updated
- Date: 2026-03-04
- Updated by: devops-engineer

## Local Environment (Docker Compose)
### Prerequisites
- Docker Engine 24+ with Docker Compose plugin.
- Available local ports: `5173`, `8000`, `5432`, `6379`, `9000`, `9001`.

### Bootstrap
1. Create runtime env file: `cp .env.example .env`
2. Start stack: `docker compose up -d --build`
3. Verify status: `docker compose ps`

Shortcut wrappers:
- `make up` / `just up`
- `make rebuild` / `just rebuild`
- `make clean-orphans` / `just clean-orphans`
- `make ps` / `just ps`
- `make smoke` / `just smoke`
- `make down` / `just down`

### Service Endpoints
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Backend health: `http://localhost:8000/health`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`

### Stop and Cleanup
- Stop stack: `docker compose down`
- Stop and remove volumes: `docker compose down -v`
- Wrapper cleanup: `make down-v` or `just down-v`

### Smoke Verification
1. `docker compose ps` shows `healthy` for backend/postgres/redis/minio.
2. `curl -fsS http://localhost:8000/health` returns `{"status":"ok"}`.
3. Open frontend at `http://localhost:5173` and verify route render.

## Incident Triage
1. Confirm impact and affected user segment.
2. Capture failing signal (logs/metrics/error id).
3. Apply mitigations with lowest blast radius first.
4. Record timeline and root cause candidate.

## Escalation Matrix
| Severity | Condition | Notify | Target Response |
| --- | --- | --- | --- |
| Sev-1 | Full outage or data corruption risk | coordinator + architect | 15 min |
| Sev-2 | Major degradation | coordinator | 30 min |
| Sev-3 | Minor issue | owner role | 1 business day |

## Postmortem Minimum
- Impact summary
- Root cause
- Corrective actions
- Preventive actions

## Container Incident Commands
- Recent logs by service: `docker compose logs --tail 200 <service>`
- Follow logs: `docker compose logs -f <service>`
- Restart one service: `docker compose restart <service>`
- Rebuild after dependency/image changes: `docker compose up -d --build`
- Force-recreate all services: `make rebuild` or `just rebuild`
- Remove orphan containers: `make clean-orphans` or `just clean-orphans`
