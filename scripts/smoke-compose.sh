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

post_json_with_auth_retry() {
  local url="$1"
  local body="$2"
  local bearer_token="$3"
  local attempts="${4:-20}"
  local delay_seconds="${5:-1}"
  local try

  for try in $(seq 1 "${attempts}"); do
    if response="$(curl -fsS -X POST "${url}" \
      -H 'Content-Type: application/json' \
      -H "Authorization: Bearer ${bearer_token}" \
      -d "${body}" 2>/dev/null)"; then
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

load_first_interviewer_staff_id() {
  python3 - <<'PY'
import json
from pathlib import Path

for line in Path(".env").read_text(encoding="utf-8").splitlines():
    if line.startswith("INTERVIEW_STAFF_CALENDAR_MAP_JSON="):
        raw = line.split("=", 1)[1].strip()
        mapping = json.loads(raw)
        if not isinstance(mapping, dict) or not mapping:
            raise SystemExit("INTERVIEW_STAFF_CALENDAR_MAP_JSON must contain at least one entry")
        print(next(iter(mapping)))
        raise SystemExit(0)

raise SystemExit("INTERVIEW_STAFF_CALENDAR_MAP_JSON not found in .env")
PY
}

create_smoke_interview_token() {
  local apply_result_file="$1"
  local vacancy_id="$2"
  local bearer_token="$3"
  local interviewer_staff_id="$4"

  python3 - "${apply_result_file}" "${vacancy_id}" "${bearer_token}" "${interviewer_staff_id}" <<'PY'
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

apply_result_file = Path(sys.argv[1])
vacancy_id = sys.argv[2]
bearer_token = sys.argv[3]
interviewer_staff_id = sys.argv[4]
base_url = "http://localhost:8000"

payload = json.loads(apply_result_file.read_text(encoding="utf-8"))
candidate_id = payload["candidate_id"]
candidate_seed = int(candidate_id.replace("-", "")[:8], 16)


def request_json(method: str, url: str, body: dict[str, object] | None = None) -> dict[str, object]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Authorization": f"Bearer {bearer_token}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30.0) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"{method} {url} failed with {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"{method} {url} failed: {exc}") from exc


history = request_json(
    "GET",
    f"{base_url}/api/v1/pipeline/transitions?vacancy_id={vacancy_id}&candidate_id={candidate_id}",
)
items = history.get("items", [])
current_stage = items[-1]["to_stage"] if items else None
stage_order = ["applied", "screening", "shortlist"]
if current_stage is not None and current_stage not in stage_order:
    raise SystemExit(f"unexpected candidate stage before interview: {current_stage}")

pending_stages = stage_order if current_stage is None else stage_order[stage_order.index(current_stage) + 1 :]
for stage in pending_stages:
    request_json(
        "POST",
        f"{base_url}/api/v1/pipeline/transitions",
        {
            "vacancy_id": vacancy_id,
            "candidate_id": candidate_id,
            "to_stage": stage,
            "reason": f"move_to_{stage}",
        },
    )

future_date = (
    datetime.now(UTC).date() + timedelta(days=1 + (candidate_seed % 21))
).isoformat()
interview_payload = request_json(
    "POST",
    f"{base_url}/api/v1/vacancies/{vacancy_id}/interviews",
    {
        "candidate_id": candidate_id,
        "scheduled_start_local": f"{future_date}T03:00:00",
        "scheduled_end_local": f"{future_date}T04:00:00",
        "timezone": "Europe/Minsk",
        "location_kind": "google_meet",
        "location_details": None,
        "interviewer_staff_ids": [interviewer_staff_id],
    },
)
interview_id = interview_payload["interview_id"]

deadline = time.monotonic() + 180.0
while time.monotonic() < deadline:
    current = request_json(
        "GET",
        f"{base_url}/api/v1/vacancies/{vacancy_id}/interviews/{interview_id}",
    )
    invite_url = current.get("candidate_invite_url")
    if current.get("calendar_sync_status") == "synced" and invite_url:
        token = urllib.parse.parse_qs(urllib.parse.urlparse(str(invite_url)).query)["interviewToken"][0]
        print(token)
        raise SystemExit(0)
    if current.get("calendar_sync_status") == "conflict":
        raise SystemExit(
            "interview sync conflicted: "
            f"{current.get('calendar_sync_reason_code')} | {current.get('calendar_sync_error_detail')}"
        )
    if current.get("calendar_sync_status") == "failed":
        raise SystemExit(
            "interview sync failed: "
            f"{current.get('calendar_sync_reason_code')} | {current.get('calendar_sync_error_detail')}"
        )
    time.sleep(2.0)

raise SystemExit("interview sync did not finish before the timeout elapsed")
PY
}

echo "[smoke] validating docker compose service status..."
COMPOSE_PS_JSON="$(docker compose ps --all --format json)"
python3 - "${COMPOSE_PS_JSON}" <<'PY'
import json
import sys

healthy_services = ("backend", "postgres", "redis", "minio")
running_services = ("frontend", "backend-worker")
bootstrap_services = ("postgres-init", "backend-migrate", "minio-init")
raw = sys.argv[1].strip()

if not raw:
    raise SystemExit("docker compose ps returned empty output")

if raw.startswith("["):
    payload = json.loads(raw)
else:
    payload = [json.loads(line) for line in raw.splitlines() if line.strip()]

services = {row.get("Service"): row for row in payload if isinstance(row, dict)}
missing = [service for service in (*healthy_services, *running_services) if service not in services]
if missing:
    raise SystemExit(f"missing services in compose status: {', '.join(missing)}")

for service in healthy_services:
    row = services[service]
    state = (row.get("State") or "").lower()
    health = (row.get("Health") or "").lower()
    if state != "running":
        raise SystemExit(f"{service} must be running, got state={state or 'unknown'}")
    if health != "healthy":
        raise SystemExit(f"{service} must be healthy, got health={health or 'unknown'}")

for service in running_services:
    row = services[service]
    state = (row.get("State") or "").lower()
    if state != "running":
        raise SystemExit(f"{service} must be running, got state={state or 'unknown'}")

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

echo "[smoke] creating deterministic open vacancy for public browser flow..."
SMOKE_VACANCY_TITLE="Browser Smoke Vacancy"
SMOKE_VACANCY_REQUEST_BODY="$(python3 - "${SMOKE_VACANCY_TITLE}" <<'PY'
import json
import sys

print(
    json.dumps(
        {
            "title": sys.argv[1],
            "description": "Compose browser smoke vacancy for public apply regression checks.",
            "department": "QA",
            "status": "open",
        }
    )
)
PY
)"
SMOKE_VACANCY_PAYLOAD="$(post_json_with_auth_retry \
  "http://localhost:8000/api/v1/vacancies" \
  "${SMOKE_VACANCY_REQUEST_BODY}" \
  "${ACCESS_TOKEN}")"
SMOKE_VACANCY_ID="$(python3 - "${SMOKE_VACANCY_PAYLOAD}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
required_keys = {
    "vacancy_id",
    "title",
    "status",
}
missing = sorted(required_keys - payload.keys())
if missing:
    raise SystemExit(f"vacancy create response missing keys: {', '.join(missing)}")
if payload.get("status") != "open":
    raise SystemExit(f"unexpected vacancy status: {payload.get('status')}")
print(payload["vacancy_id"])
PY
)"

echo "[smoke] checking browser public candidate apply flow..."
SMOKE_CANDIDATE_APPLY_RESULT_FILE="$(mktemp /tmp/hrm-browser-candidate-apply-XXXX.json)"
trap 'if [ -n "${SMOKE_CANDIDATE_APPLY_RESULT_FILE:-}" ]; then rm -f "${SMOKE_CANDIDATE_APPLY_RESULT_FILE}"; fi' EXIT
python3 scripts/browser_candidate_apply_smoke.py \
  --frontend-url "http://localhost:5173/candidate/apply" \
  --api-origin "http://localhost:8000" \
  --vacancy-id "${SMOKE_VACANCY_ID}" \
  --vacancy-title "${SMOKE_VACANCY_TITLE}" \
  --result-file "${SMOKE_CANDIDATE_APPLY_RESULT_FILE}"

SMOKE_INTERVIEWER_STAFF_ID="$(load_first_interviewer_staff_id)"
SMOKE_INTERVIEW_TOKEN="$(create_smoke_interview_token \
  "${SMOKE_CANDIDATE_APPLY_RESULT_FILE}" \
  "${SMOKE_VACANCY_ID}" \
  "${ACCESS_TOKEN}" \
  "${SMOKE_INTERVIEWER_STAFF_ID}")"

echo "[smoke] checking browser public candidate interview flow..."
python3 scripts/browser_candidate_interview_smoke.py \
  --frontend-url "http://localhost:5173/candidate/interview" \
  --api-origin "http://localhost:8000" \
  --interview-token "${SMOKE_INTERVIEW_TOKEN}"

echo "[smoke] all docker-compose smoke checks passed."
