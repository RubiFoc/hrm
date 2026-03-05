#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FROZEN_PATH="$ROOT_DIR/docs/api/openapi.frozen.json"
TMP_PATH="$(mktemp)"
trap 'rm -f "$TMP_PATH"' EXIT

if [[ ! -f "$FROZEN_PATH" ]]; then
  echo "Missing frozen OpenAPI spec: $FROZEN_PATH" >&2
  echo "Run: ./scripts/generate-openapi-frozen.sh" >&2
  exit 1
fi

UV_CACHE_DIR=/tmp/uv-cache uv run --project "$ROOT_DIR/apps/backend" python - <<'PY' > "$TMP_PATH"
import json
from hrm_backend.main import app

spec = app.openapi()
print(json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True))
PY

if ! diff -u "$FROZEN_PATH" "$TMP_PATH"; then
  echo
  echo "OpenAPI contract drift detected." >&2
  echo "Run: ./scripts/generate-openapi-frozen.sh" >&2
  exit 1
fi

echo "OpenAPI frozen spec check passed."
