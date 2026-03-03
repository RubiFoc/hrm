#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${GH_TOKEN:-}" ]]; then
  echo "GH_TOKEN is required"
  exit 1
fi

OWNER="RubiFoc"
REPO="hrm"
API="https://api.github.com/repos/${OWNER}/${REPO}"
AUTH=(-u "x-access-token:${GH_TOKEN}" -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" -H "Content-Type: application/json")

ms_number=$(curl -sS "${AUTH[@]}" "${API}/milestones?state=all&per_page=100" | jq -r '.[] | select(.title=="M1") | .number' | head -n1)
if [[ -z "${ms_number}" ]]; then
  echo "Milestone M1 not found"
  exit 1
fi

issues_json=$(curl -sS "${AUTH[@]}" "${API}/issues?state=all&per_page=100")

patch_task() {
  local task_id="$1"
  local priority="$2"
  local owner_labels_csv="$3"
  local area_label="$4"

  local issue_number
  issue_number=$(jq -r --arg task "$task_id" '.[] | select(.title | contains($task)) | .number' <<<"$issues_json" | head -n1)

  if [[ -z "${issue_number}" ]]; then
    echo "Issue for ${task_id} not found"
    return 1
  fi

  IFS=',' read -r -a owner_labels <<< "$owner_labels_csv"

  local labels='["phase:m1","type:task","status:planned","priority:'"${priority}"'","'"${area_label}"'"]'
  for label in "${owner_labels[@]}"; do
    labels=$(jq -c --arg l "$label" '. + [$l]' <<<"$labels")
  done

  local payload
  payload=$(jq -nc \
    --argjson milestone "$ms_number" \
    --argjson labels "$labels" \
    '{milestone:$milestone, labels:$labels}')

  local code
  code=$(curl -sS -o /tmp/sync_issue_out.json -w "%{http_code}" "${AUTH[@]}" -X PATCH "${API}/issues/${issue_number}" -d "$payload")

  if [[ "$code" != "200" ]]; then
    echo "Failed ${task_id} (#${issue_number}), HTTP ${code}"
    cat /tmp/sync_issue_out.json
    return 1
  fi

  echo "Synced ${task_id} (#${issue_number})"
}

while IFS='|' read -r id prio owners area; do
  [[ -z "${id}" ]] && continue
  patch_task "$id" "$prio" "$owners" "$area"
done <<'TASKS'
TASK-12-01|p0|owner:backend-engineer,owner:frontend-engineer|area:platform
TASK-01-01|p0|owner:architect,owner:backend-engineer|area:security
TASK-01-02|p0|owner:architect,owner:backend-engineer|area:security
TASK-01-03|p0|owner:architect,owner:backend-engineer|area:security
TASK-01-05|p0|owner:business-analyst,owner:architect|area:compliance
TASK-03-01|p0|owner:backend-engineer|area:candidate
TASK-02-01|p0|owner:backend-engineer|area:recruitment
TASK-02-02|p0|owner:backend-engineer|area:recruitment
TASK-03-02|p0|owner:backend-engineer,owner:data-ml-engineer|area:candidate
TASK-03-03|p0|owner:backend-engineer,owner:data-ml-engineer|area:candidate
TASK-04-01|p0|owner:data-ml-engineer,owner:backend-engineer|area:ai
TASK-04-02|p0|owner:data-ml-engineer,owner:backend-engineer|area:ai
TASK-04-03|p0|owner:data-ml-engineer,owner:backend-engineer|area:ai
TASK-02-03|p0|owner:backend-engineer|area:recruitment
TASK-05-01|p0|owner:backend-engineer|area:interview
TASK-05-02|p0|owner:backend-engineer|area:interview
TASK-05-03|p0|owner:backend-engineer|area:interview
TASK-05-04|p0|owner:backend-engineer|area:interview
TASK-08-01|p0|owner:backend-engineer|area:automation
TASK-08-02|p0|owner:backend-engineer|area:automation
TASK-08-03|p0|owner:backend-engineer|area:automation
TASK-08-04|p0|owner:backend-engineer|area:automation
TASK-10-01|p0|owner:backend-engineer|area:analytics
TASK-10-02|p0|owner:backend-engineer,owner:data-ml-engineer|area:analytics
TASK-01-04|p0|owner:architect,owner:backend-engineer|area:security
TASK-11-01|p0|owner:frontend-engineer|area:frontend
TASK-11-02|p0|owner:frontend-engineer|area:frontend
TASK-11-03|p0|owner:frontend-engineer|area:frontend
TASK-11-04|p0|owner:frontend-engineer|area:frontend
TASK-11-05|p0|owner:frontend-engineer|area:frontend
TASK-11-06|p0|owner:frontend-engineer|area:frontend
TASK-11-07|p0|owner:frontend-engineer|area:frontend
TASK-11-08|p0|owner:frontend-engineer|area:frontend
TASK-11-09|p0|owner:frontend-engineer|area:frontend
TASKS

echo "M1 metadata sync complete"
