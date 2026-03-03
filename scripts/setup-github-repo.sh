#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "" ]]; then
  echo "Usage: GH_TOKEN=<token> $0 <owner/repo>"
  exit 1
fi

if [[ "${GH_TOKEN:-}" == "" ]]; then
  echo "GH_TOKEN is required"
  exit 1
fi

REPO="$1"

git push -u origin main
git push -u origin develop

curl -sS -X PUT \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer ${GH_TOKEN}" \
  "https://api.github.com/repos/${REPO}/branches/main/protection" \
  -d @- <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["docs-check", "backend", "frontend"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 2,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true
}
JSON

echo "GitHub repository setup complete for ${REPO}"
