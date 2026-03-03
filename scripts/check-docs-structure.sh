#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

required_files=(
  "README.md"
  "AGENTS.md"
  "docs/README.md"
  "docs/ownership.md"
  "docs/project/brief.md"
  "docs/project/frontend-requirements.md"
  "docs/project/legal-framework.md"
  "docs/project/legal-controls-matrix.md"
  "docs/project/rbac-matrix.md"
  "docs/project/auth-session-lifecycle.md"
  "docs/project/sprint-m1-plan.md"
  "docs/architecture/overview.md"
  "docs/architecture/diagrams.md"
  "docs/architecture/decisions.md"
  "docs/engineering/best-practices.md"
  "docs/operations/runbook.md"
  "docs/operations/github-workflow.md"
  "docs/testing/strategy.md"
  "docs/llm/context-map.md"
  "docs/llm/docs-update-checklist.md"
)

missing=0
for rel in "${required_files[@]}"; do
  path="${PROJECT_ROOT}/${rel}"
  if [[ -f "${path}" ]]; then
    echo "OK   ${rel}"
  else
    echo "MISS ${rel}"
    missing=$((missing + 1))
  fi
done

if [[ ${missing} -gt 0 ]]; then
  echo "Documentation structure check failed: ${missing} file(s) missing." >&2
  exit 1
fi

echo "Documentation structure check passed."
