#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

wait_http() {
  local url="$1"
  local attempts="${2:-30}"
  local delay_seconds="${3:-1}"
  local try

  for try in $(seq 1 "${attempts}"); do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep "${delay_seconds}"
  done

  echo "endpoint did not become ready: ${url}" >&2
  return 1
}

post_json_with_retry() {
  local url="$1"
  local body="$2"
  local attempts="${3:-20}"
  local delay_seconds="${4:-1}"
  local try

  for try in $(seq 1 "${attempts}"); do
    if response="$(curl -fsS -X POST "${url}" -H 'Content-Type: application/json' -d "${body}" 2>/dev/null)"; then
      printf '%s' "${response}"
      return 0
    fi
    sleep "${delay_seconds}"
  done

  echo "POST endpoint did not become ready: ${url}" >&2
  return 1
}

create_smoke_admin() {
  local login="$1"
  local email="$2"
  local password="$3"

  docker compose exec -T backend \
    uv run --no-dev python -m hrm_backend.auth.cli.create_admin \
    --login "${login}" \
    --email "${email}" \
    --password "${password}" >/dev/null
}

echo "[smoke] validating docker compose service status..."
COMPOSE_PS_JSON="$(docker compose ps --all --format json)"
python3 - "${COMPOSE_PS_JSON}" <<'PY'
import json
import sys

required_services = ("backend", "postgres", "redis", "minio")
bootstrap_services = ("postgres-init", "backend-migrate")
raw = sys.argv[1].strip()

if not raw:
    raise SystemExit("docker compose ps returned empty output")

if raw.startswith("["):
    payload = json.loads(raw)
else:
    payload = [json.loads(line) for line in raw.splitlines() if line.strip()]

services = {row.get("Service"): row for row in payload if isinstance(row, dict)}
missing = [service for service in required_services if service not in services]
if missing:
    raise SystemExit(f"missing services in compose status: {', '.join(missing)}")

for service in required_services:
    row = services[service]
    state = (row.get("State") or "").lower()
    health = (row.get("Health") or "").lower()
    if state != "running":
        raise SystemExit(f"{service} must be running, got state={state or 'unknown'}")
    if health != "healthy":
        raise SystemExit(f"{service} must be healthy, got health={health or 'unknown'}")

for service in bootstrap_services:
    row = services.get(service)
    if row is None:
        raise SystemExit(f"{service} must exist in compose status output")

    state = (row.get("State") or "").lower()
    if state not in ("exited", "stopped"):
        raise SystemExit(f"{service} must complete and exit, got state={state or 'unknown'}")

    exit_code = row.get("ExitCode")
    if str(exit_code) != "0":
        raise SystemExit(f"{service} must exit with code 0, got {exit_code!r}")
PY

echo "[smoke] checking backend health endpoint..."
wait_http "http://localhost:8000/health"
BACKEND_HEALTH="$(curl -fsS http://localhost:8000/health)"
python3 - "${BACKEND_HEALTH}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
if payload.get("status") != "ok":
    raise SystemExit(f"unexpected /health payload: {payload}")
PY

echo "[smoke] checking frontend and MinIO endpoints..."
wait_http "http://localhost:5173"
wait_http "http://localhost:9000/minio/health/live"

echo "[smoke] checking auth login endpoint..."
SMOKE_ADMIN_LOGIN="smoke-admin-$(date +%s)-$RANDOM"
SMOKE_ADMIN_EMAIL="${SMOKE_ADMIN_LOGIN}@local.test"
SMOKE_ADMIN_PASSWORD="SmokePassword!123"
create_smoke_admin "${SMOKE_ADMIN_LOGIN}" "${SMOKE_ADMIN_EMAIL}" "${SMOKE_ADMIN_PASSWORD}"

LOGIN_REQUEST_BODY="$(python3 - "${SMOKE_ADMIN_LOGIN}" "${SMOKE_ADMIN_PASSWORD}" <<'PY'
import json
import sys

print(json.dumps({"identifier": sys.argv[1], "password": sys.argv[2]}))
PY
)"
LOGIN_PAYLOAD="$(post_json_with_retry \
  "http://localhost:8000/api/v1/auth/login" \
  "${LOGIN_REQUEST_BODY}")"
ACCESS_TOKEN="$(python3 - "${LOGIN_PAYLOAD}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
required_keys = {
    "access_token",
    "refresh_token",
    "token_type",
    "expires_in",
    "session_id",
}
missing = sorted(required_keys - payload.keys())
if missing:
    raise SystemExit(f"login response missing keys: {', '.join(missing)}")
if payload.get("token_type") != "bearer":
    raise SystemExit(f"unexpected token_type: {payload.get('token_type')}")
print(payload["access_token"])
PY
)"

ME_PAYLOAD="$(curl -fsS "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")"
python3 - "${ME_PAYLOAD}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
required_keys = {
    "subject_id",
    "role",
    "session_id",
    "access_token_expires_at",
}
missing = sorted(required_keys - payload.keys())
if missing:
    raise SystemExit(f"/me response missing keys: {', '.join(missing)}")
if payload.get("role") != "admin":
    raise SystemExit(f"unexpected /me role: {payload.get('role')}")
PY

echo "[smoke] checking browser auth flow..."
python3 scripts/browser_auth_smoke.py \
  --frontend-url "http://localhost:5173/login" \
  --api-origin "http://localhost:8000" \
  --login "${SMOKE_ADMIN_LOGIN}" \
  --password "${SMOKE_ADMIN_PASSWORD}"

echo "[smoke] all docker-compose smoke checks passed."
