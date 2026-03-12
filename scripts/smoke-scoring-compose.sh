#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

EXPECTED_OLLAMA_BASE_URL="${EXPECTED_OLLAMA_BASE_URL:-http://ollama:11434}"
FIXTURE_PATH="${FIXTURE_PATH:-apps/backend/tests/fixtures/candidates/sample_cv_en.pdf}"

wait_http() {
  local url="$1"
  local attempts="${2:-60}"
  local delay_seconds="${3:-2}"
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
  local attempts="${3:-30}"
  local delay_seconds="${4:-2}"
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
  local attempts="${4:-30}"
  local delay_seconds="${5:-2}"
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

container_env() {
  local service="$1"
  local variable_name="$2"

  docker compose exec -T "${service}" python -c \
    "import os; print(os.environ.get('${variable_name}', ''))"
}

if [[ ! -f "${FIXTURE_PATH}" ]]; then
  echo "fixture file does not exist: ${FIXTURE_PATH}" >&2
  exit 1
fi

echo "[ai-smoke] validating ai-local compose service status..."
COMPOSE_PS_JSON="$(docker compose ps --all --format json)"
python3 - "${COMPOSE_PS_JSON}" <<'PY'
import json
import sys

healthy_services = ("backend", "postgres", "redis", "minio", "ollama")
running_services = ("frontend", "backend-worker")
bootstrap_services = ("postgres-init", "backend-migrate", "minio-init", "ollama-init")
raw = sys.argv[1].strip()

if not raw:
    raise SystemExit("docker compose ps returned empty output")

if raw.startswith("["):
    payload = json.loads(raw)
else:
    payload = [json.loads(line) for line in raw.splitlines() if line.strip()]

services = {row.get("Service"): row for row in payload if isinstance(row, dict)}
missing = [
    service
    for service in (*healthy_services, *running_services, *bootstrap_services)
    if service not in services
]
if missing:
    raise SystemExit(
        "missing services in compose status: "
        + ", ".join(missing)
        + " (run `OLLAMA_BASE_URL=http://ollama:11434 docker compose --profile ai-local up -d --build` first)"
    )

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
    row = services[service]
    state = (row.get("State") or "").lower()
    if state not in ("exited", "stopped"):
        raise SystemExit(f"{service} must complete and exit, got state={state or 'unknown'}")

    exit_code = row.get("ExitCode")
    if str(exit_code) != "0":
        raise SystemExit(f"{service} must exit with code 0, got {exit_code!r}")
PY

echo "[ai-smoke] verifying backend and worker Ollama runtime wiring..."
BACKEND_OLLAMA_BASE_URL="$(container_env backend OLLAMA_BASE_URL)"
WORKER_OLLAMA_BASE_URL="$(container_env backend-worker OLLAMA_BASE_URL)"
if [[ "${BACKEND_OLLAMA_BASE_URL}" != "${EXPECTED_OLLAMA_BASE_URL}" ]]; then
  echo "backend OLLAMA_BASE_URL mismatch: expected ${EXPECTED_OLLAMA_BASE_URL}, got ${BACKEND_OLLAMA_BASE_URL}" >&2
  exit 1
fi
if [[ "${WORKER_OLLAMA_BASE_URL}" != "${EXPECTED_OLLAMA_BASE_URL}" ]]; then
  echo "backend-worker OLLAMA_BASE_URL mismatch: expected ${EXPECTED_OLLAMA_BASE_URL}, got ${WORKER_OLLAMA_BASE_URL}" >&2
  exit 1
fi

MATCH_SCORING_MODEL_NAME="$(container_env backend MATCH_SCORING_MODEL_NAME)"
if [[ -z "${MATCH_SCORING_MODEL_NAME}" ]]; then
  echo "backend MATCH_SCORING_MODEL_NAME is empty" >&2
  exit 1
fi

echo "[ai-smoke] verifying Ollama model bootstrap..."
OLLAMA_MODELS="$(docker compose exec -T ollama bash -lc 'OLLAMA_HOST=http://127.0.0.1:11434 ollama list')"
python3 - "${OLLAMA_MODELS}" "${MATCH_SCORING_MODEL_NAME}" <<'PY'
import sys

models_output = sys.argv[1]
expected_model = sys.argv[2]
lines = [line.strip() for line in models_output.splitlines() if line.strip()]
available_names = {line.split()[0] for line in lines[1:] if line}
if expected_model not in available_names:
    raise SystemExit(f"expected Ollama model not found: {expected_model}; available={sorted(available_names)}")
PY

echo "[ai-smoke] checking backend health endpoint..."
wait_http "http://localhost:8000/health"

echo "[ai-smoke] authenticating smoke admin..."
SMOKE_ADMIN_LOGIN="smoke-scoring-admin-$(date +%s)-$RANDOM"
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

echo "[ai-smoke] creating vacancy and candidate fixtures..."
SMOKE_VACANCY_TITLE="Compose AI Smoke Vacancy"
SMOKE_CANDIDATE_SUFFIX="$(date +%s)-$RANDOM"
VACANCY_REQUEST_BODY="$(python3 - "${SMOKE_VACANCY_TITLE}" <<'PY'
import json
import sys

print(
    json.dumps(
        {
            "title": sys.argv[1],
            "description": "Operator-facing compose AI smoke vacancy for real scoring verification.",
            "department": "QA",
            "status": "open",
        }
    )
)
PY
)"
VACANCY_PAYLOAD="$(post_json_with_auth_retry \
  "http://localhost:8000/api/v1/vacancies" \
  "${VACANCY_REQUEST_BODY}" \
  "${ACCESS_TOKEN}")"
VACANCY_ID="$(python3 - "${VACANCY_PAYLOAD}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
required_keys = {"vacancy_id", "title", "status"}
missing = sorted(required_keys - payload.keys())
if missing:
    raise SystemExit(f"vacancy create response missing keys: {', '.join(missing)}")
if payload.get("status") != "open":
    raise SystemExit(f"unexpected vacancy status: {payload.get('status')}")
print(payload["vacancy_id"])
PY
)"

CANDIDATE_REQUEST_BODY="$(python3 - "${SMOKE_CANDIDATE_SUFFIX}" <<'PY'
import json
import sys

suffix = sys.argv[1]
print(
    json.dumps(
        {
            "first_name": "AI",
            "last_name": "Smoke",
            "email": f"ai-smoke-{suffix}@example.com",
            "phone": "+375291112233",
            "location": "Minsk",
            "current_title": "Backend Engineer",
            "extra_data": {},
        }
    )
)
PY
)"
CANDIDATE_PAYLOAD="$(post_json_with_auth_retry \
  "http://localhost:8000/api/v1/candidates" \
  "${CANDIDATE_REQUEST_BODY}" \
  "${ACCESS_TOKEN}")"
CANDIDATE_ID="$(python3 - "${CANDIDATE_PAYLOAD}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
required_keys = {"candidate_id", "email", "first_name", "last_name"}
missing = sorted(required_keys - payload.keys())
if missing:
    raise SystemExit(f"candidate create response missing keys: {', '.join(missing)}")
print(payload["candidate_id"])
PY
)"

FILE_CHECKSUM="$(python3 - "${FIXTURE_PATH}" <<'PY'
import hashlib
import pathlib
import sys

print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())
PY
)"
UPLOAD_PAYLOAD="$(curl -fsS -X POST \
  "http://localhost:8000/api/v1/candidates/${CANDIDATE_ID}/cv" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -F "checksum_sha256=${FILE_CHECKSUM}" \
  -F "file=@${FIXTURE_PATH};type=application/pdf")"
python3 - "${UPLOAD_PAYLOAD}" "${CANDIDATE_ID}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
expected_candidate_id = sys.argv[2]
required_keys = {
    "document_id",
    "candidate_id",
    "filename",
    "mime_type",
    "size_bytes",
    "checksum_sha256",
    "uploaded_at",
}
missing = sorted(required_keys - payload.keys())
if missing:
    raise SystemExit(f"CV upload response missing keys: {', '.join(missing)}")
if payload.get("candidate_id") != expected_candidate_id:
    raise SystemExit(
        f"unexpected candidate_id in upload response: {payload.get('candidate_id')}"
    )
PY

echo "[ai-smoke] waiting for parsed CV analysis readiness..."
PARSING_STATUS=""
for _ in $(seq 1 90); do
  PARSING_STATUS="$(curl -fsS "http://localhost:8000/api/v1/candidates/${CANDIDATE_ID}/cv/parsing-status" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}")"
  status_outcome="$(python3 - "${PARSING_STATUS}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
status = payload.get("status")
analysis_ready = payload.get("analysis_ready")
last_error = payload.get("last_error")

if status == "failed":
    raise SystemExit(f"failed:{last_error or 'unknown'}")
if analysis_ready is True:
    print("ready")
else:
    print("waiting")
PY
)" || {
    echo "CV parsing failed: ${PARSING_STATUS}" >&2
    exit 1
  }
  if [[ "${status_outcome}" == "ready" ]]; then
    break
  fi
  sleep 2
done

python3 - "${PARSING_STATUS}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
required_keys = {
    "candidate_id",
    "document_id",
    "job_id",
    "status",
    "attempt_count",
    "queued_at",
    "updated_at",
    "analysis_ready",
    "detected_language",
}
missing = sorted(required_keys - payload.keys())
if missing:
    raise SystemExit(f"parsing status missing keys: {', '.join(missing)}")
if payload.get("analysis_ready") is not True:
    raise SystemExit(f"parsed profile did not become ready: {payload}")
PY

ANALYSIS_PAYLOAD="$(curl -fsS "http://localhost:8000/api/v1/candidates/${CANDIDATE_ID}/cv/analysis" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")"
python3 - "${ANALYSIS_PAYLOAD}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
required_keys = {"candidate_id", "document_id", "detected_language", "parsed_at", "parsed_profile", "evidence"}
missing = sorted(required_keys - payload.keys())
if missing:
    raise SystemExit(f"analysis response missing keys: {', '.join(missing)}")
if not isinstance(payload.get("parsed_profile"), dict):
    raise SystemExit("analysis parsed_profile must be an object")
if not isinstance(payload.get("evidence"), list):
    raise SystemExit("analysis evidence must be a list")
PY

echo "[ai-smoke] requesting real match scoring job..."
SCORING_REQUEST_BODY="$(python3 - "${CANDIDATE_ID}" <<'PY'
import json
import sys

print(json.dumps({"candidate_id": sys.argv[1]}))
PY
)"
INITIAL_SCORE_PAYLOAD="$(post_json_with_auth_retry \
  "http://localhost:8000/api/v1/vacancies/${VACANCY_ID}/match-scores" \
  "${SCORING_REQUEST_BODY}" \
  "${ACCESS_TOKEN}")"
SEEN_STATUSES="$(python3 - "${INITIAL_SCORE_PAYLOAD}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
status = payload.get("status")
if status not in {"queued", "running", "succeeded"}:
    raise SystemExit(f"unexpected initial scoring status: {status}")
print(status)
PY
)"

FINAL_SCORE_PAYLOAD="${INITIAL_SCORE_PAYLOAD}"
FINAL_SCORE_STATUS="${SEEN_STATUSES}"
for _ in $(seq 1 120); do
  FINAL_SCORE_PAYLOAD="$(curl -fsS "http://localhost:8000/api/v1/vacancies/${VACANCY_ID}/match-scores/${CANDIDATE_ID}" \
    -H "Authorization: Bearer ${ACCESS_TOKEN}")"
  CURRENT_SCORE_STATUS="$(python3 - "${FINAL_SCORE_PAYLOAD}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
status = payload.get("status")
if status not in {"queued", "running", "succeeded", "failed"}:
    raise SystemExit(f"unexpected scoring status: {status}")
print(status)
PY
)"
  case "${CURRENT_SCORE_STATUS}" in
    queued|running)
      if [[ ",${SEEN_STATUSES}," != *",${CURRENT_SCORE_STATUS},"* ]]; then
        SEEN_STATUSES="${SEEN_STATUSES},${CURRENT_SCORE_STATUS}"
      fi
      sleep 2
      ;;
    succeeded)
      if [[ ",${SEEN_STATUSES}," != *",succeeded,"* ]]; then
        SEEN_STATUSES="${SEEN_STATUSES},succeeded"
      fi
      FINAL_SCORE_STATUS="succeeded"
      break
      ;;
    failed)
      echo "match scoring failed: ${FINAL_SCORE_PAYLOAD}" >&2
      exit 1
      ;;
  esac
done

if [[ "${FINAL_SCORE_STATUS}" != "succeeded" ]]; then
  echo "match scoring did not reach succeeded state: ${FINAL_SCORE_PAYLOAD}" >&2
  exit 1
fi

python3 - "${FINAL_SCORE_PAYLOAD}" "${VACANCY_ID}" "${CANDIDATE_ID}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
expected_vacancy_id = sys.argv[2]
expected_candidate_id = sys.argv[3]
required_keys = {
    "vacancy_id",
    "candidate_id",
    "status",
    "score",
    "confidence",
    "summary",
    "matched_requirements",
    "missing_requirements",
    "evidence",
    "scored_at",
    "model_name",
    "model_version",
}
missing = sorted(required_keys - payload.keys())
if missing:
    raise SystemExit(f"score response missing keys: {', '.join(missing)}")
if payload.get("vacancy_id") != expected_vacancy_id:
    raise SystemExit(f"unexpected vacancy_id: {payload.get('vacancy_id')}")
if payload.get("candidate_id") != expected_candidate_id:
    raise SystemExit(f"unexpected candidate_id: {payload.get('candidate_id')}")
if payload.get("status") != "succeeded":
    raise SystemExit(f"unexpected final scoring status: {payload.get('status')}")
if not isinstance(payload.get("matched_requirements"), list):
    raise SystemExit("matched_requirements must be a list")
if not isinstance(payload.get("missing_requirements"), list):
    raise SystemExit("missing_requirements must be a list")
if not isinstance(payload.get("evidence"), list):
    raise SystemExit("evidence must be a list")
PY

echo "[ai-smoke] scoring lifecycle states observed: ${SEEN_STATUSES}"
echo "[ai-smoke] all ai-local compose scoring checks passed."
