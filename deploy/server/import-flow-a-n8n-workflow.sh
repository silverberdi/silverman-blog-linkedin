#!/usr/bin/env bash
# Import Flow A n8n workflow into the real n8n container (not the nginx gateway).
# Prepares workflow JSON with stable id, worker config, and import-safe fields.
# Does not print secrets, activate the workflow, or call LinkedIn API.
set -euo pipefail

WORKFLOW_SOURCE_JSON="${WORKFLOW_SOURCE_JSON:-/home/silverman/n8n-imports/silverman-blog-linkedin-flow-a-publish.source.json}"
WORKFLOW_PREPARED_JSON="${WORKFLOW_PREPARED_JSON:-/home/silverman/n8n-imports/silverman-blog-linkedin-flow-a-publish.prepared.json}"
WORKER_ENV_FILE="${WORKER_ENV_FILE:-/home/silverman/silverman-blog-linkedin-worker/.env}"
WORKER_BASE_URL="${WORKER_BASE_URL:-http://192.168.0.194:8010}"

WORKFLOW_NAME="Silverman Blog LinkedIn Flow A Publish"
WORKFLOW_ID="silvermanFlowAPublish01"
EXPECTED_NODE_COUNT=26

N8N_IMAGE_MARKERS=(
  "n8nio/n8n"
  "docker.n8n.io/n8nio/n8n"
)

GATEWAY_MARKERS=(
  "n8n-gateway"
  "nginx"
)

pass() {
  echo "PASS: $*"
}

fail() {
  echo "FAIL: $*" >&2
}

info() {
  echo "==> $*"
}

is_gateway_container() {
  local name="$1"
  local image="$2"
  local combined="${name} ${image}"
  local marker
  for marker in "${GATEWAY_MARKERS[@]}"; do
    if [[ "${combined}" == *"${marker}"* ]]; then
      return 0
    fi
  done
  return 1
}

is_n8n_app_image() {
  local image="$1"
  local marker
  for marker in "${N8N_IMAGE_MARKERS[@]}"; do
    if [[ "${image}" == *"${marker}"* ]]; then
      return 0
    fi
  done
  return 1
}

find_n8n_container() {
  local line name image
  while IFS=$'\t' read -r name image; do
    [[ -z "${name}" ]] && continue
    if is_gateway_container "${name}" "${image}"; then
      continue
    fi
    if ! is_n8n_app_image "${image}"; then
      continue
    fi
    echo "${name}"
    return 0
  done < <(docker ps --format '{{.Names}}\t{{.Image}}' 2>/dev/null || true)
  return 1
}

read_worker_api_key() {
  local env_file="$1"
  local line key value
  if [[ ! -f "${env_file}" ]]; then
    fail "worker env file not found: ${env_file}"
    return 1
  fi
  while IFS= read -r line || [[ -n "${line}" ]]; do
    [[ "${line}" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line//[[:space:]]/}" ]] && continue
    if [[ "${line}" =~ ^[[:space:]]*SILVERMAN_BLOG_LINKEDIN_API_KEY[[:space:]]*=[[:space:]]*(.*)$ ]]; then
      value="${BASH_REMATCH[1]}"
      value="${value%\"}"
      value="${value#\"}"
      value="${value%\'}"
      value="${value#\'}"
      if [[ -n "${value}" ]]; then
        printf '%s' "${value}"
        return 0
      fi
    fi
  done < "${env_file}"
  fail "SILVERMAN_BLOG_LINKEDIN_API_KEY not set in ${env_file}"
  return 1
}

prepare_workflow_json() {
  local source_path="$1"
  local prepared_path="$2"
  local worker_base_url="$3"
  local worker_api_key="$4"
  local workflow_id="$5"
  local workflow_name="$6"

  python3 - "${source_path}" "${prepared_path}" "${worker_base_url}" "${worker_api_key}" \
    "${workflow_id}" "${workflow_name}" <<'PY'
import json
import sys

source_path, prepared_path, worker_base_url, worker_api_key, workflow_id, workflow_name = sys.argv[1:7]

with open(source_path, encoding="utf-8") as fh:
    workflow = json.load(fh)

workflow["id"] = workflow_id
workflow["name"] = workflow_name
workflow["active"] = False

for node in workflow.get("nodes", []):
    if node.get("name") != "Set Configuration":
        continue
    assignments = node.get("parameters", {}).get("assignments", {}).get("assignments", [])
    for item in assignments:
        name = item.get("name")
        if name == "worker_base_url":
            item["value"] = worker_base_url
        elif name == "worker_api_key":
            item["value"] = worker_api_key

for field in ("createdAt", "updatedAt", "versionId"):
    if field in workflow and workflow[field] is None:
        del workflow[field]

with open(prepared_path, "w", encoding="utf-8") as fh:
    json.dump(workflow, fh, indent=2)
    fh.write("\n")
PY
}

verify_exported_workflow() {
  local export_path="$1"
  local workflow_id="$2"
  local workflow_name="$3"
  local expected_nodes="$4"

  python3 - "${export_path}" "${workflow_id}" "${workflow_name}" "${expected_nodes}" <<'PY'
import json
import sys

export_path, workflow_id, workflow_name, expected_nodes = sys.argv[1:5]
expected_nodes = int(expected_nodes)

with open(export_path, encoding="utf-8") as fh:
    payload = json.load(fh)

candidates = payload if isinstance(payload, list) else [payload]
match = None
for item in candidates:
    if not isinstance(item, dict):
        continue
    if item.get("id") == workflow_id or item.get("name") == workflow_name:
        match = item
        break

if match is None:
    print("FAIL: exported workflow not found by id or name", file=sys.stderr)
    sys.exit(1)

if match.get("active") is not False:
    print(f"FAIL: workflow active is {match.get('active')!r}, expected false", file=sys.stderr)
    sys.exit(1)

node_count = len(match.get("nodes", []))
if node_count != expected_nodes:
    print(
        f"FAIL: workflow node count is {node_count}, expected {expected_nodes}",
        file=sys.stderr,
    )
    sys.exit(1)

print(f"PASS: workflow id={match.get('id')!r} name={match.get('name')!r}")
print(f"PASS: workflow inactive (active=false)")
print(f"PASS: workflow node count {node_count}/{expected_nodes}")
PY
}

info "Flow A n8n workflow import"
echo "    source:      ${WORKFLOW_SOURCE_JSON}"
echo "    prepared:    ${WORKFLOW_PREPARED_JSON}"
echo "    worker env:  ${WORKER_ENV_FILE}"
echo "    worker url:  ${WORKER_BASE_URL}"
echo "    workflow id: ${WORKFLOW_ID}"
echo

if [[ ! -f "${WORKFLOW_SOURCE_JSON}" ]]; then
  fail "workflow source JSON not found: ${WORKFLOW_SOURCE_JSON}"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  fail "docker not available"
  exit 1
fi

if ! N8N_CONTAINER="$(find_n8n_container)"; then
  fail "no running n8n container found (image must match n8nio/n8n; gateway containers excluded)"
  exit 1
fi

N8N_IMAGE="$(docker inspect -f '{{.Config.Image}}' "${N8N_CONTAINER}")"
pass "selected n8n container ${N8N_CONTAINER} (image ${N8N_IMAGE})"
if is_gateway_container "${N8N_CONTAINER}" "${N8N_IMAGE}"; then
  fail "refusing to use nginx gateway container ${N8N_CONTAINER}"
  exit 1
fi

WORKER_API_KEY="$(read_worker_api_key "${WORKER_ENV_FILE}")"
if [[ -n "${WORKER_API_KEY}" ]]; then
  echo "worker_api_key: configured"
else
  fail "worker_api_key not configured"
  exit 1
fi

PREPARED_DIR="$(dirname "${WORKFLOW_PREPARED_JSON}")"
mkdir -p "${PREPARED_DIR}"

info "Preparing workflow JSON"
prepare_workflow_json \
  "${WORKFLOW_SOURCE_JSON}" \
  "${WORKFLOW_PREPARED_JSON}" \
  "${WORKER_BASE_URL}" \
  "${WORKER_API_KEY}" \
  "${WORKFLOW_ID}" \
  "${WORKFLOW_NAME}"
pass "prepared ${WORKFLOW_PREPARED_JSON} (id=${WORKFLOW_ID}, active=false)"

CONTAINER_PREPARED_PATH="/tmp/silverman-flow-a-prepared.json"
docker cp "${WORKFLOW_PREPARED_JSON}" "${N8N_CONTAINER}:${CONTAINER_PREPARED_PATH}"

info "Importing workflow via n8n CLI"
docker exec "${N8N_CONTAINER}" n8n import:workflow --input="${CONTAINER_PREPARED_PATH}"
pass "import:workflow completed"

EXPORT_TMP="$(mktemp)"
trap 'rm -f "${EXPORT_TMP}"' EXIT
CONTAINER_EXPORT_PATH="/tmp/silverman-flow-a-export-verify.json"

info "Verifying imported workflow (export:workflow)"
docker exec "${N8N_CONTAINER}" n8n export:workflow --output="${CONTAINER_EXPORT_PATH}" --all
docker cp "${N8N_CONTAINER}:${CONTAINER_EXPORT_PATH}" "${EXPORT_TMP}"

if verify_exported_workflow "${EXPORT_TMP}" "${WORKFLOW_ID}" "${WORKFLOW_NAME}" "${EXPECTED_NODE_COUNT}"; then
  :
else
  exit 1
fi

echo
echo "OVERALL: PASS (Flow A workflow imported; remains inactive)"
echo "NOTE: workflow was not activated; no cron/webhook/schedule triggers were added."
