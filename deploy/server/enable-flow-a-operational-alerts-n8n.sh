#!/usr/bin/env bash
# Enable Flow A operational-alerts webhook emission and wire n8n Error Trigger +
# evaluate/emit schedule. Run on Ubuntu server (or via SSH).
#
# Does not print secrets. Recreates the worker container after env update.
set -euo pipefail

WORKER_DIR="${WORKER_DIR:-/home/silverman/silverman-blog-linkedin-worker}"
WORKER_ENV_FILE="${WORKER_ENV_FILE:-${WORKER_DIR}/.env}"
N8N_IMPORTS_DIR="${N8N_IMPORTS_DIR:-/home/silverman/n8n-imports}"
N8N_CONTAINER="${N8N_CONTAINER:-local-ai-stack-n8n-1}"
WORKER_BASE_URL="${WORKER_BASE_URL:-http://192.168.0.194:8010}"
# Internal docker DNS to n8n (worker must join local-ai-stack_backend). Public
# gateway http://192.168.0.194:5678/webhook/* requires X-Avatares-Api-Key and is
# not usable by the worker emit path (no custom webhook headers yet).
ALERTS_WEBHOOK_URL="${ALERTS_WEBHOOK_URL:-http://n8n:5678/webhook/silverman-flow-a-operational-alerts}"

REPO_WEBHOOK_JSON="${REPO_WEBHOOK_JSON:-}"
REPO_ERROR_JSON="${REPO_ERROR_JSON:-}"
REPO_EVALUATE_JSON="${REPO_EVALUATE_JSON:-}"

pass() { echo "PASS: $*"; }
fail() { echo "FAIL: $*" >&2; exit 1; }
info() { echo "==> $*"; }

find_n8n_container() {
  local name image
  while IFS=$'\t' read -r name image; do
    [[ -z "${name}" ]] && continue
    case "${name} ${image}" in
      *n8n-gateway*|*"nginx"*) continue ;;
    esac
    case "${image}" in
      *n8nio/n8n*|*"docker.n8n.io/n8nio/n8n"*)
        echo "${name}"
        return 0
        ;;
    esac
  done < <(docker ps --format '{{.Names}}\t{{.Image}}' 2>/dev/null || true)
  return 1
}

read_worker_api_key() {
  local env_file="$1"
  local line value
  [[ -f "${env_file}" ]] || fail "worker env file not found: ${env_file}"
  while IFS= read -r line || [[ -n "${line}" ]]; do
    [[ "${line}" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line//[[:space:]]/}" ]] && continue
    if [[ "${line}" =~ ^[[:space:]]*SILVERMAN_BLOG_LINKEDIN_API_KEY[[:space:]]*=[[:space:]]*(.*)$ ]]; then
      value="${BASH_REMATCH[1]}"
      value="${value%\"}"; value="${value#\"}"
      value="${value%\'}"; value="${value#\'}"
      [[ -n "${value}" ]] || continue
      printf '%s' "${value}"
      return 0
    fi
  done < "${env_file}"
  fail "SILVERMAN_BLOG_LINKEDIN_API_KEY not set in ${env_file}"
}

upsert_env_kv() {
  local env_file="$1"
  local key="$2"
  local value="$3"
  local tmp
  tmp="$(mktemp)"
  if grep -qE "^[[:space:]]*${key}=" "${env_file}"; then
    awk -v k="${key}" -v v="${value}" '
      BEGIN { done=0 }
      $0 ~ "^[[:space:]]*"k"=" {
        print k"="v
        done=1
        next
      }
      { print }
      END { if (!done) print k"="v }
    ' "${env_file}" > "${tmp}"
  else
    cat "${env_file}" > "${tmp}"
    printf '\n%s=%s\n' "${key}" "${value}" >> "${tmp}"
  fi
  mv "${tmp}" "${env_file}"
}

prepare_set_configuration_workflow() {
  local source_path="$1"
  local prepared_path="$2"
  local worker_base_url="$3"
  local worker_api_key="$4"
  local workflow_id="$5"
  local active_flag="$6"

  python3 - "${source_path}" "${prepared_path}" "${worker_base_url}" "${worker_api_key}" \
    "${workflow_id}" "${active_flag}" <<'PY'
import json
import sys

source_path, prepared_path, worker_base_url, worker_api_key, workflow_id, active_flag = sys.argv[1:7]
with open(source_path, encoding="utf-8") as fh:
    workflow = json.load(fh)
workflow["id"] = workflow_id
workflow["active"] = active_flag.lower() in {"1", "true", "yes", "on"}
for node in workflow.get("nodes", []):
    if node.get("name") != "Set Configuration":
        continue
    assignments = (
        node.get("parameters", {})
        .get("assignments", {})
        .get("assignments", [])
    )
    for item in assignments:
        if item.get("name") == "worker_base_url":
            item["value"] = worker_base_url
        elif item.get("name") == "worker_api_key":
            item["value"] = worker_api_key
for field in ("createdAt", "updatedAt", "versionId"):
    if workflow.get(field) is None:
        workflow.pop(field, None)
with open(prepared_path, "w", encoding="utf-8") as fh:
    json.dump(workflow, fh, indent=2)
    fh.write("\n")
PY
}

import_and_publish() {
  local container="$1"
  local prepared_path="$2"
  local workflow_id="$3"
  local host_prepared="$4"

  docker cp "${host_prepared}" "${container}:/tmp/${workflow_id}.prepared.json"
  # Regular (non-queue) n8n rejects --activeState=fromJson; import then publish.
  docker exec "${container}" n8n import:workflow \
    --input="/tmp/${workflow_id}.prepared.json"
  docker exec "${container}" n8n publish:workflow --id="${workflow_id}"
}

info "Resolving n8n container"
N8N_CONTAINER="$(find_n8n_container || true)"
[[ -n "${N8N_CONTAINER}" ]] || fail "n8n app container not found"
pass "n8n container ${N8N_CONTAINER}"

info "Reading worker API key (not printed)"
API_KEY="$(read_worker_api_key "${WORKER_ENV_FILE}")"
pass "worker API key present"

mkdir -p "${N8N_IMPORTS_DIR}"

# Resolve source JSON paths (prefer explicit REPO_* overrides, else copies already synced).
WEBHOOK_SRC="${REPO_WEBHOOK_JSON:-${N8N_IMPORTS_DIR}/silverman-blog-linkedin-operational-alerts-webhook.source.json}"
ERROR_SRC="${REPO_ERROR_JSON:-${N8N_IMPORTS_DIR}/silverman-blog-linkedin-flow-a-error-report.source.json}"
EVAL_SRC="${REPO_EVALUATE_JSON:-${N8N_IMPORTS_DIR}/silverman-blog-linkedin-operational-alerts-evaluate-emit.source.json}"

for path in "${WEBHOOK_SRC}" "${ERROR_SRC}" "${EVAL_SRC}"; do
  [[ -f "${path}" ]] || fail "missing workflow source: ${path}"
done

WEBHOOK_PREP="${N8N_IMPORTS_DIR}/silverman-blog-linkedin-operational-alerts-webhook.prepared.json"
ERROR_PREP="${N8N_IMPORTS_DIR}/silverman-blog-linkedin-flow-a-error-report.prepared.json"
EVAL_PREP="${N8N_IMPORTS_DIR}/silverman-blog-linkedin-operational-alerts-evaluate-emit.prepared.json"

info "Preparing webhook receiver workflow"
python3 - "${WEBHOOK_SRC}" "${WEBHOOK_PREP}" <<'PY'
import json, sys
src, dst = sys.argv[1:3]
with open(src, encoding="utf-8") as fh:
    wf = json.load(fh)
wf["id"] = "silvermanFlowAAlertsWebhook01"
wf["active"] = True
for field in ("createdAt", "updatedAt", "versionId"):
    if wf.get(field) is None:
        wf.pop(field, None)
with open(dst, "w", encoding="utf-8") as fh:
    json.dump(wf, fh, indent=2)
    fh.write("\n")
PY
import_and_publish "${N8N_CONTAINER}" "${WEBHOOK_PREP}" "silvermanFlowAAlertsWebhook01" "${WEBHOOK_PREP}"
pass "imported+published silvermanFlowAAlertsWebhook01"

info "Preparing error-report workflow"
prepare_set_configuration_workflow \
  "${ERROR_SRC}" "${ERROR_PREP}" "${WORKER_BASE_URL}" "${API_KEY}" \
  "silvermanFlowAErrorReport01" "true"
import_and_publish "${N8N_CONTAINER}" "${ERROR_PREP}" "silvermanFlowAErrorReport01" "${ERROR_PREP}"
pass "imported+published silvermanFlowAErrorReport01"

info "Preparing evaluate/emit schedule workflow"
prepare_set_configuration_workflow \
  "${EVAL_SRC}" "${EVAL_PREP}" "${WORKER_BASE_URL}" "${API_KEY}" \
  "silvermanFlowAAlertsEvaluate01" "true"
import_and_publish "${N8N_CONTAINER}" "${EVAL_PREP}" "silvermanFlowAAlertsEvaluate01" "${EVAL_PREP}"
pass "imported+published silvermanFlowAAlertsEvaluate01"

info "Patching Flow A live export settings.errorWorkflow (preserve server config)"
docker exec "${N8N_CONTAINER}" n8n export:workflow \
  --id=silvermanFlowAPublish01 \
  --output=/tmp/silvermanFlowAPublish01.live.json
docker cp "${N8N_CONTAINER}:/tmp/silvermanFlowAPublish01.live.json" \
  "${N8N_IMPORTS_DIR}/silvermanFlowAPublish01.live.json"
python3 - "${N8N_IMPORTS_DIR}/silvermanFlowAPublish01.live.json" \
  "${N8N_IMPORTS_DIR}/silvermanFlowAPublish01.with-error-workflow.json" <<'PY'
import json, sys
src, dst = sys.argv[1:3]
with open(src, encoding="utf-8") as fh:
    payload = json.load(fh)
wf = payload[0] if isinstance(payload, list) else payload
settings = dict(wf.get("settings") or {})
settings["errorWorkflow"] = "silvermanFlowAErrorReport01"
wf["settings"] = settings
wf["active"] = True
for field in ("createdAt", "updatedAt", "versionId"):
    if wf.get(field) is None:
        wf.pop(field, None)
with open(dst, "w", encoding="utf-8") as fh:
    json.dump(wf, fh, indent=2)
    fh.write("\n")
print("errorWorkflow=", settings["errorWorkflow"])
print("nodes=", len(wf.get("nodes") or []))
PY
import_and_publish \
  "${N8N_CONTAINER}" \
  "${N8N_IMPORTS_DIR}/silvermanFlowAPublish01.with-error-workflow.json" \
  "silvermanFlowAPublish01" \
  "${N8N_IMPORTS_DIR}/silvermanFlowAPublish01.with-error-workflow.json"
pass "Flow A errorWorkflow set to silvermanFlowAErrorReport01 and republished"

info "Enabling worker operational-alerts env (fail-open for emit path)"
upsert_env_kv "${WORKER_ENV_FILE}" "SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_ENABLED" "true"
upsert_env_kv "${WORKER_ENV_FILE}" "SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_WEBHOOK_URL" "${ALERTS_WEBHOOK_URL}"
grep -E '^SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_' "${WORKER_ENV_FILE}" | sed 's/=.*/=<set>/'
pass "worker .env alerts keys set"

info "Recreating worker container to load env"
(
  cd "${WORKER_DIR}"
  export BUILD_REVISION
  BUILD_REVISION="$(cat .build_git_sha 2>/dev/null || true)"
  if [[ -z "${BUILD_REVISION}" ]]; then
    BUILD_REVISION="$(docker exec silverman-blog-linkedin-worker printenv BUILD_REVISION)"
  fi
  echo "BUILD_REVISION=${BUILD_REVISION}"
  docker compose -f silverman-worker.compose.yaml up -d --force-recreate --remove-orphans
)
sleep 4
docker exec silverman-blog-linkedin-worker printenv \
  SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_ENABLED \
  SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_WEBHOOK_URL | sed 's/=.*/=<set>/'
pass "worker recreated with alerts env"

info "OVERALL: operational alerts webhook + n8n wiring enabled"
echo "Webhook URL: ${ALERTS_WEBHOOK_URL}"
echo "Error workflow: silvermanFlowAErrorReport01 (linked from silvermanFlowAPublish01)"
echo "Evaluate/emit schedule: silvermanFlowAAlertsEvaluate01 cron 30 9 * * * UTC"
