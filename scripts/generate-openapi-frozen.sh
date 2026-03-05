#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_PATH="${1:-$ROOT_DIR/docs/api/openapi.frozen.json}"

mkdir -p "$(dirname "$OUTPUT_PATH")"
UV_CACHE_DIR=/tmp/uv-cache uv run --project "$ROOT_DIR/apps/backend" python - <<'PY' > "$OUTPUT_PATH"
import json
from hrm_backend.main import app

spec = app.openapi()
print(json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True))
PY

echo "OpenAPI frozen spec generated at: $OUTPUT_PATH"
