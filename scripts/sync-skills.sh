#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${PROJECT_ROOT}/.ai/skills"
DEST_BASE="${CODEX_HOME:-$HOME/.codex}/skills"
PREFIX="${1:-$(basename "${PROJECT_ROOT}")}"

if [[ ! -d "${SRC_DIR}" ]]; then
  echo "Skills source directory not found: ${SRC_DIR}" >&2
  exit 1
fi

mkdir -p "${DEST_BASE}"

synced=0
for skill_dir in "${SRC_DIR}"/*; do
  [[ -d "${skill_dir}" ]] || continue

  skill_name="$(basename "${skill_dir}")"
  dest_dir="${DEST_BASE}/${PREFIX}-${skill_name}"

  rm -rf "${dest_dir}"
  cp -R "${skill_dir}" "${dest_dir}"
  echo "Synced ${skill_name} -> ${dest_dir}"
  synced=$((synced + 1))
done

if [[ ${synced} -eq 0 ]]; then
  echo "No skills found in ${SRC_DIR}" >&2
  exit 1
fi

echo "Done. Synced ${synced} skill(s) with prefix '${PREFIX}'."
