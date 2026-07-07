#!/usr/bin/env bash
# Collect read-only post-smoke evidence for Flow A on the Ubuntu server.
# Does not print secrets, activate n8n, call LinkedIn API, deploy, or restart.
set -euo pipefail

WORKER_BASE_URL="${WORKER_BASE_URL:-http://localhost:8010}"
WORKER_CONTAINER="${WORKER_CONTAINER:-silverman-blog-linkedin-worker}"
N8N_WORKFLOW_ID="${N8N_WORKFLOW_ID:-silvermanFlowAPublish01}"
N8N_WORKFLOW_NAME="${N8N_WORKFLOW_NAME:-Silverman Blog LinkedIn Flow A Publish}"
POST_SLUG_FRAGMENT="${POST_SLUG_FRAGMENT:-why-i-did-not-start-with-the-database}"
EXPECTED_NODE_COUNT=26

FLOW_A_OPENAPI_PATHS=(
  "/publish-blog-post"
  "/generate-linkedin-package"
  "/schedule-linkedin-distribution"
)

N8N_IMAGE_MARKERS=(
  "n8nio/n8n"
  "docker.n8n.io/n8nio/n8n"
)

GATEWAY_MARKERS=(
  "n8n-gateway"
  "nginx"
)

BASE_PATH_CANDIDATES=(
  "/home/silverman/compartido_mac/silverman-blog-linkedin"
  "/home/silverman/silverman-blog-linkedin"
  "/home/silverman/silverman-blog-linkedin-worker/data"
  "/data/silverman-blog-linkedin"
)

JSON_OUTPUT=0
if [[ "${1:-}" == "--json" ]]; then
  JSON_OUTPUT=1
fi

HEALTH_TMP=""
OPENAPI_TMP=""
N8N_EXPORT_TMP=""

cleanup_temp_files() {
  rm -f "${HEALTH_TMP}" "${OPENAPI_TMP}" "${N8N_EXPORT_TMP}"
}

# Write docker inspect JSON to a temp file; print path on success.
docker_inspect_json_tmp() {
  local container="$1"
  local tmp
  tmp="$(mktemp)"
  if ! docker inspect "${container}" > "${tmp}" 2>/dev/null; then
    rm -f "${tmp}"
    return 1
  fi
  echo "${tmp}"
}

WORKER_OK=0
N8N_OK=0
N8N_INACTIVE=0
HAS_SMOKE_ARTIFACTS=0
CAMPAIGN_STATE=""
HAS_BLOG_PUBLISH=0
HAS_LINKEDIN_PACKAGE=0
HAS_LINKEDIN_DISTRIBUTION=0
FLOW_A_COMPLETE=0
BASE_PATH_RESOLVED=0
BASE_PATH_SOURCE=""
RESOLVED_BASE_PATH=""
PUBLIC_BLOG_REPO_OK=0
PUBLIC_BLOG_REPO_SOURCE=""
PUBLIC_BLOG_HOST_MOUNT=""
PUBLIC_BLOG_CONTAINER_PATH=""
OVERALL_STATUS="FAIL"

pass() {
  echo "PASS: $*"
}

fail() {
  echo "FAIL: $*" >&2
}

info() {
  echo "==> $*"
}

section() {
  echo
  echo "=== $* ==="
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

resolve_base_path_from_container_env() {
  local container="$1"
  local inspect_tmp
  inspect_tmp="$(docker_inspect_json_tmp "${container}" 2>/dev/null)" || return 0
  python3 - "${inspect_tmp}" <<'PY' || true
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    payload = json.load(fh)
if not payload:
    sys.exit(1)
item = payload[0]
for env in item.get("Config", {}).get("Env", []):
    if env.startswith("SILVERMAN_BLOG_LINKEDIN_BASE_PATH="):
        value = env.split("=", 1)[1].strip()
        if value:
            print(value)
            sys.exit(0)
sys.exit(1)
PY
  local rc=$?
  rm -f "${inspect_tmp}"
  return $rc
}

resolve_base_path_from_container_mounts() {
  local container="$1"
  local inspect_tmp
  inspect_tmp="$(docker_inspect_json_tmp "${container}" 2>/dev/null)" || return 0
  python3 - "${inspect_tmp}" <<'PY' || true
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    payload = json.load(fh)
if not payload:
    sys.exit(1)
item = payload[0]
for mount in item.get("Mounts", []):
    dest = mount.get("Destination", "")
    if "/data/silverman-blog-linkedin" in dest:
        source = mount.get("Source", "").strip()
        if source:
            print(source)
            sys.exit(0)
sys.exit(1)
PY
  local rc=$?
  rm -f "${inspect_tmp}"
  return $rc
}

resolve_base_path_from_health() {
  local health_json="$1"
  python3 - "${health_json}" <<'PY' || true
import json
import sys

path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)
except (OSError, json.JSONDecodeError):
    sys.exit(1)
for key in ("base_path", "path", "editorial_root", "editorial_base_path"):
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        print(value.strip())
        sys.exit(0)
folders = payload.get("folders")
if isinstance(folders, dict):
    for value in folders.values():
        if isinstance(value, str) and value.strip():
            print(value.strip())
            sys.exit(0)
sys.exit(1)
PY
}

latest_file_in_dir() {
  local dir="$1"
  local pattern="${2:-*}"
  if [[ ! -d "${dir}" ]]; then
    return 1
  fi
  find "${dir}" -maxdepth 1 -type f -name "${pattern}" -printf '%T@ %p\n' 2>/dev/null \
    | sort -nr \
    | head -n 1 \
    | cut -d' ' -f2- \
    || true
}

latest_file_recursive() {
  local dir="$1"
  local pattern="${2:-*}"
  if [[ ! -d "${dir}" ]]; then
    return 1
  fi
  find "${dir}" -type f -name "${pattern}" -printf '%T@ %p\n' 2>/dev/null \
    | sort -nr \
    | head -n 1 \
    | cut -d' ' -f2- \
    || true
}

find_matching_files() {
  local dir="$1"
  local fragment="$2"
  if [[ ! -d "${dir}" ]]; then
    return 0
  fi
  find "${dir}" -type f -name "*${fragment}*" 2>/dev/null | sort || true
}

find_matching_files_in_container() {
  local container="$1"
  local dir="$2"
  local fragment="$3"
  if ! docker exec "${container}" test -d "${dir}" 2>/dev/null; then
    return 0
  fi
  docker exec "${container}" find "${dir}" -type f -name "*${fragment}*" 2>/dev/null | sort || true
}

resolve_base_path() {
  local candidate source

  if [[ -n "${BASE_PATH:-}" ]]; then
    if [[ -d "${BASE_PATH}" ]]; then
      RESOLVED_BASE_PATH="${BASE_PATH}"
      BASE_PATH_SOURCE="BASE_PATH environment override"
      BASE_PATH_RESOLVED=1
      return 0
    fi
    fail "BASE_PATH override set but directory does not exist: ${BASE_PATH}"
    return 1
  fi

  if command -v docker >/dev/null 2>&1; then
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -Fxq "${WORKER_CONTAINER}"; then
      candidate="$(resolve_base_path_from_container_env "${WORKER_CONTAINER}" || true)"
      if [[ -n "${candidate}" && -d "${candidate}" ]]; then
        RESOLVED_BASE_PATH="${candidate}"
        BASE_PATH_SOURCE="worker container env SILVERMAN_BLOG_LINKEDIN_BASE_PATH"
        BASE_PATH_RESOLVED=1
        return 0
      fi

      candidate="$(resolve_base_path_from_container_mounts "${WORKER_CONTAINER}" || true)"
      if [[ -n "${candidate}" && -d "${candidate}" ]]; then
        RESOLVED_BASE_PATH="${candidate}"
        BASE_PATH_SOURCE="worker container mount mapped to host source"
        BASE_PATH_RESOLVED=1
        return 0
      fi
    fi
  fi

  HEALTH_TMP="$(mktemp)"
  local health_code
  health_code="$(curl -sS -o "${HEALTH_TMP}" -w '%{http_code}' "${WORKER_BASE_URL}/health" 2>/dev/null || echo "000")"
  if [[ "${health_code}" == "200" ]]; then
    candidate="$(resolve_base_path_from_health "${HEALTH_TMP}" || true)"
    if [[ -n "${candidate}" && -d "${candidate}" ]]; then
      RESOLVED_BASE_PATH="${candidate}"
      BASE_PATH_SOURCE="GET /health response"
      BASE_PATH_RESOLVED=1
      return 0
    fi
  fi

  for candidate in "${BASE_PATH_CANDIDATES[@]}"; do
    if [[ -d "${candidate}" ]]; then
      RESOLVED_BASE_PATH="${candidate}"
      BASE_PATH_SOURCE="known host candidate path"
      BASE_PATH_RESOLVED=1
      return 0
    fi
  done

  fail "could not resolve editorial base path"
  echo "Remediation:" >&2
  echo "  - export BASE_PATH=/path/to/editorial/root before running this script" >&2
  echo "  - ensure worker container ${WORKER_CONTAINER} is running with SILVERMAN_BLOG_LINKEDIN_BASE_PATH or a /data/silverman-blog-linkedin mount" >&2
  echo "  - confirm GET ${WORKER_BASE_URL}/health returns base_path when available" >&2
  return 1
}

check_worker() {
  local health_code openapi_code missing_paths=() path
  local openapi_tmp

  section "Worker"
  echo "worker base url: ${WORKER_BASE_URL}"

  HEALTH_TMP="${HEALTH_TMP:-$(mktemp)}"
  health_code="$(curl -sS -o "${HEALTH_TMP}" -w '%{http_code}' "${WORKER_BASE_URL}/health" 2>/dev/null || echo "000")"
  if [[ "${health_code}" == "200" ]]; then
    pass "GET /health returned HTTP 200"
    if command -v python3 >/dev/null 2>&1; then
      python3 -m json.tool < "${HEALTH_TMP}" 2>/dev/null | sed -n '1,40p' || cat "${HEALTH_TMP}"
    else
      cat "${HEALTH_TMP}"
    fi
  else
    fail "GET /health returned HTTP ${health_code}"
    return 1
  fi

  OPENAPI_TMP="$(mktemp)"
  openapi_code="$(curl -sS -o "${OPENAPI_TMP}" -w '%{http_code}' "${WORKER_BASE_URL}/openapi.json" 2>/dev/null || echo "000")"
  if [[ "${openapi_code}" != "200" ]]; then
    fail "GET /openapi.json returned HTTP ${openapi_code}"
    return 1
  fi
  pass "GET /openapi.json returned HTTP 200"

  if ! python3 - "${OPENAPI_TMP}" "${FLOW_A_OPENAPI_PATHS[@]}" <<'PY'
import json
import sys

openapi_path = sys.argv[1]
required = sys.argv[2:]
with open(openapi_path, encoding="utf-8") as fh:
    payload = json.load(fh)
paths = payload.get("paths", {})
missing = [item for item in required if item not in paths]
if missing:
    print("FAIL: missing Flow A OpenAPI paths: " + ", ".join(missing))
    sys.exit(1)
for item in required:
    print(f"PASS: OpenAPI path present {item}")
PY
  then
    return 1
  fi

  WORKER_OK=1
}

resolve_public_blog_host_mount() {
  local container="$1"
  local inspect_tmp
  inspect_tmp="$(docker_inspect_json_tmp "${container}" 2>/dev/null)" || return 0
  python3 - "${inspect_tmp}" <<'PY' || true
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    payload = json.load(fh)
if not payload:
    sys.exit(1)
item = payload[0]
for mount in item.get("Mounts", []):
    if mount.get("Destination") == "/public-blog":
        source = mount.get("Source", "").strip()
        if source:
            print(source)
            sys.exit(0)
sys.exit(1)
PY
  local rc=$?
  rm -f "${inspect_tmp}"
  return $rc
}

check_public_blog_repo() {
  local container pages_repo_path host_mount has_posts has_images

  section "Public blog repo readiness"
  if ! command -v docker >/dev/null 2>&1; then
    fail "docker not available for public blog repo checks"
    return 1
  fi

  if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -Fxq "${WORKER_CONTAINER}"; then
    fail "worker container ${WORKER_CONTAINER} is not running"
    return 1
  fi

  container="${WORKER_CONTAINER}"
  pages_repo_path=""
  inspect_tmp=""
  if inspect_tmp="$(docker_inspect_json_tmp "${container}" 2>/dev/null)"; then
    pages_repo_path="$(
      python3 - "${inspect_tmp}" <<'PY' || true
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    payload = json.load(fh)
if not payload:
    sys.exit(1)
item = payload[0]
for env in item.get("Config", {}).get("Env", []):
    if env.startswith("SILVERMAN_GITHUB_PAGES_REPO_PATH="):
        value = env.split("=", 1)[1].strip()
        if value:
            print(value)
            sys.exit(0)
sys.exit(1)
PY
    )"
    rm -f "${inspect_tmp}"
  fi

  if [[ -z "${pages_repo_path}" ]]; then
    fail "SILVERMAN_GITHUB_PAGES_REPO_PATH not set in worker container"
    echo "Remediation:" >&2
    echo "  - redeploy worker with silverman-worker.compose.yaml public blog mount" >&2
    echo "  - ensure SILVERMAN_GITHUB_PAGES_REPO_PATH=/public-blog in container env" >&2
    echo "  - without this, publish fails with blog_publish_public_repo_not_configured" >&2
    return 1
  fi

  pass "worker container SILVERMAN_GITHUB_PAGES_REPO_PATH=${pages_repo_path}"
  PUBLIC_BLOG_REPO_SOURCE="worker container env"
  PUBLIC_BLOG_CONTAINER_PATH="${pages_repo_path}"

  if docker exec "${container}" test -d "${pages_repo_path}" 2>/dev/null; then
    pass "container path ${pages_repo_path} exists"
  else
    fail "container path ${pages_repo_path} missing (public blog repo not mounted)"
    echo "Remediation:" >&2
    echo "  - clone or sync silverberdi.github.io to the host path configured in compose" >&2
    echo "  - default host path: /home/silverman/silverberdi.github.io" >&2
    echo "  - redeploy the worker container on the Ubuntu server after syncing the checkout" >&2
    return 1
  fi

  has_posts=0
  has_images=0
  if docker exec "${container}" test -d "${pages_repo_path}/_posts" 2>/dev/null; then
    pass "container path ${pages_repo_path}/_posts exists"
    has_posts=1
  else
    fail "container path ${pages_repo_path}/_posts missing"
  fi

  if docker exec "${container}" test -d "${pages_repo_path}/assets/images" 2>/dev/null; then
    pass "container path ${pages_repo_path}/assets/images exists"
    has_images=1
  else
    fail "container path ${pages_repo_path}/assets/images missing"
  fi

  host_mount="$(resolve_public_blog_host_mount "${container}" || true)"
  if [[ -n "${host_mount}" ]]; then
    PUBLIC_BLOG_HOST_MOUNT="${host_mount}"
    pass "host mount for ${pages_repo_path}: ${host_mount}"
  else
    echo "INFO: could not resolve host mount for ${pages_repo_path}"
  fi

  if [[ "${has_posts}" -eq 1 && "${has_images}" -eq 1 ]]; then
    PUBLIC_BLOG_REPO_OK=1
    return 0
  fi

  echo "Remediation:" >&2
  echo "  - ensure the GitHub Pages checkout contains _posts/ and assets/images/" >&2
  echo "  - deploy script does not clone automatically; sync the repo manually" >&2
  return 1
}

check_editorial_artifacts() {
  local latest_run latest_campaign latest_generated

  section "Editorial artifacts"
  echo "base path: ${RESOLVED_BASE_PATH}"
  echo "resolved via: ${BASE_PATH_SOURCE}"

  latest_run="$(latest_file_in_dir "${RESOLVED_BASE_PATH}/metadata/runs" '*.json' || true)"
  if [[ -n "${latest_run}" ]]; then
    pass "latest run metadata: ${latest_run}"
  else
    echo "INFO: no metadata/runs/*.json found yet"
  fi

  latest_campaign="$(latest_file_in_dir "${RESOLVED_BASE_PATH}/metadata/campaigns" '*.json' || true)"
  if [[ -n "${latest_campaign}" ]]; then
    pass "latest campaign metadata: ${latest_campaign}"
    read_campaign_evidence "${latest_campaign}"
  else
    echo "INFO: no metadata/campaigns/*.json found yet"
    echo "campaign state: (none)"
    echo "has blog publish metadata: no"
    echo "has linkedin package: no"
    echo "has linkedin distribution: no"
  fi

  latest_generated="$(latest_file_recursive "${RESOLVED_BASE_PATH}/linkedin-posts/generated" '*' || true)"
  if [[ -n "${latest_generated}" ]]; then
    if [[ "${CAMPAIGN_STATE}" == "derivatives_generated" \
      || "${CAMPAIGN_STATE}" == "distribution_scheduled" \
      || "${CAMPAIGN_STATE}" == "distribution_complete" \
      || "${CAMPAIGN_STATE}" == "flow_a_complete" ]]; then
      pass "latest generated LinkedIn artifact: ${latest_generated}"
      HAS_SMOKE_ARTIFACTS=1
    else
      echo "INFO: generated LinkedIn artifact present but campaign state is ${CAMPAIGN_STATE:-unknown}; not counting toward PASS"
      echo "       ${latest_generated}"
    fi
  else
    echo "INFO: no files under linkedin-posts/generated yet"
  fi
}

read_campaign_evidence() {
  local campaign_path="$1"
  while IFS= read -r line; do
    case "${line}" in
      CAMPAIGN_STATE=*)
        CAMPAIGN_STATE="${line#CAMPAIGN_STATE=}"
        ;;
      HAS_BLOG_PUBLISH=*)
        HAS_BLOG_PUBLISH="${line#HAS_BLOG_PUBLISH=}"
        ;;
      HAS_LINKEDIN_PACKAGE=*)
        HAS_LINKEDIN_PACKAGE="${line#HAS_LINKEDIN_PACKAGE=}"
        ;;
      HAS_LINKEDIN_DISTRIBUTION=*)
        HAS_LINKEDIN_DISTRIBUTION="${line#HAS_LINKEDIN_DISTRIBUTION=}"
        ;;
      FLOW_A_COMPLETE=*)
        FLOW_A_COMPLETE="${line#FLOW_A_COMPLETE=}"
        ;;
      *)
        echo "${line}"
        ;;
    esac
  done < <(python3 - "${campaign_path}" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as fh:
    data = json.load(fh)

state = data.get("state") or ""
blog_publish = data.get("blog_publish") or {}
package = data.get("linkedin_package")
distribution = data.get("linkedin_distribution")

has_blog_publish = bool(
    blog_publish.get("status")
    or blog_publish.get("public_repo_path")
    or data.get("source_public_url")
)
has_package = package is not None
has_distribution = distribution is not None

print(f"campaign state: {state or '(unset)'}")
print(f"has blog publish metadata: {'yes' if has_blog_publish else 'no'}")
print(f"has linkedin package: {'yes' if has_package else 'no'}")
print(f"has linkedin distribution: {'yes' if has_distribution else 'no'}")

print(f"CAMPAIGN_STATE={state}")
print(f"HAS_BLOG_PUBLISH={1 if has_blog_publish else 0}")
print(f"HAS_LINKEDIN_PACKAGE={1 if has_package else 0}")
print(f"HAS_LINKEDIN_DISTRIBUTION={1 if has_distribution else 0}")

flow_complete = 0
if state in {
    "distribution_scheduled",
    "distribution_complete",
    "flow_a_complete",
} or has_distribution:
    flow_complete = 1
print(f"FLOW_A_COMPLETE={flow_complete}")
PY
  )

  if [[ "${FLOW_A_COMPLETE}" -eq 1 ]]; then
    HAS_SMOKE_ARTIFACTS=1
  fi
}

check_public_blog_artifacts() {
  local posts_matches images_matches posts_dir images_dir search_source

  section "Public blog artifacts"
  echo "slug fragment: ${POST_SLUG_FRAGMENT}"
  echo "note: informational only; public blog files do not affect OVERALL PASS"

  if [[ -n "${PUBLIC_BLOG_HOST_MOUNT}" ]]; then
    posts_dir="${PUBLIC_BLOG_HOST_MOUNT}/_posts"
    images_dir="${PUBLIC_BLOG_HOST_MOUNT}/assets/images"
    search_source="host mount ${PUBLIC_BLOG_HOST_MOUNT}"
    pass "searching published artifacts via ${search_source}"

    posts_matches="$(find_matching_files "${posts_dir}" "${POST_SLUG_FRAGMENT}")"
    images_matches="$(find_matching_files "${images_dir}" "${POST_SLUG_FRAGMENT}")"
  elif [[ "${PUBLIC_BLOG_REPO_OK}" -eq 1 && -n "${PUBLIC_BLOG_CONTAINER_PATH}" ]]; then
    posts_dir="${PUBLIC_BLOG_CONTAINER_PATH}/_posts"
    images_dir="${PUBLIC_BLOG_CONTAINER_PATH}/assets/images"
    search_source="container path ${PUBLIC_BLOG_CONTAINER_PATH} (host mount unavailable)"
    pass "searching published artifacts via ${search_source}"

    posts_matches="$(find_matching_files_in_container "${WORKER_CONTAINER}" "${posts_dir}" "${POST_SLUG_FRAGMENT}")"
    images_matches="$(find_matching_files_in_container "${WORKER_CONTAINER}" "${images_dir}" "${POST_SLUG_FRAGMENT}")"
  else
    echo "INFO: public blog host mount unavailable and public repo not ready; skipping published artifact search"
    return 0
  fi

  if [[ -n "${posts_matches}" ]]; then
    pass "_posts matches for slug fragment:"
    while IFS= read -r line; do
      [[ -z "${line}" ]] && continue
      echo "       ${line}"
    done <<< "${posts_matches}"
  else
    echo "INFO: no _posts files matching *${POST_SLUG_FRAGMENT}* under ${search_source}"
  fi

  if [[ -n "${images_matches}" ]]; then
    pass "assets/images matches for slug fragment:"
    while IFS= read -r line; do
      [[ -z "${line}" ]] && continue
      echo "       ${line}"
    done <<< "${images_matches}"
  else
    echo "INFO: no assets/images files matching *${POST_SLUG_FRAGMENT}* under ${search_source}"
  fi
}

check_n8n_workflow() {
  local n8n_container n8n_image export_tmp container_export

  section "n8n workflow"
  if ! command -v docker >/dev/null 2>&1; then
    fail "docker not available for n8n workflow export"
    return 1
  fi

  if ! n8n_container="$(find_n8n_container)"; then
    fail "no running n8n container found (image must match n8nio/n8n; gateway containers excluded)"
    return 1
  fi

  n8n_image="$(docker inspect -f '{{.Config.Image}}' "${n8n_container}" 2>/dev/null || echo unknown)"
  pass "selected n8n container ${n8n_container} (image ${n8n_image})"
  N8N_OK=1

  N8N_EXPORT_TMP="$(mktemp)"
  container_export="/tmp/silverman-flow-a-evidence-export.json"
  if ! docker exec "${n8n_container}" n8n export:workflow --output="${container_export}" --all >/dev/null; then
    fail "n8n export:workflow failed"
    return 1
  fi
  if ! docker cp "${n8n_container}:${container_export}" "${N8N_EXPORT_TMP}"; then
    fail "failed to copy exported workflow from n8n container"
    return 1
  fi

  if ! python3 - "${N8N_EXPORT_TMP}" "${N8N_WORKFLOW_ID}" "${N8N_WORKFLOW_NAME}" "${EXPECTED_NODE_COUNT}" <<'PY'
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
    print(f"FAIL: workflow not found by id={workflow_id!r} or name={workflow_name!r}")
    sys.exit(1)

print(f"PASS: workflow found id={match.get('id')!r} name={match.get('name')!r}")

if match.get("active") is not False:
    print(f"FAIL: workflow active is {match.get('active')!r}, expected false")
    sys.exit(1)

print("PASS: workflow inactive (active=false)")

node_count = len(match.get("nodes", []))
if node_count != expected_nodes:
    print(f"FAIL: workflow node count is {node_count}, expected {expected_nodes}")
    sys.exit(1)

print(f"PASS: workflow node count {node_count}/{expected_nodes}")
PY
  then
    return 1
  fi

  N8N_INACTIVE=1
}

compute_overall_status() {
  if [[ "${BASE_PATH_RESOLVED}" -ne 1 || "${WORKER_OK}" -ne 1 || "${N8N_OK}" -ne 1 || "${N8N_INACTIVE}" -ne 1 ]]; then
    OVERALL_STATUS="FAIL"
    return
  fi
  if [[ "${PUBLIC_BLOG_REPO_OK}" -ne 1 ]]; then
    OVERALL_STATUS="FAIL"
    return
  fi
  if [[ "${CAMPAIGN_STATE}" == "error" ]]; then
    OVERALL_STATUS="FAIL"
    return
  fi
  if [[ "${FLOW_A_COMPLETE}" -eq 1 ]]; then
    OVERALL_STATUS="PASS"
    return
  fi
  if [[ -n "${CAMPAIGN_STATE}" ]]; then
    OVERALL_STATUS="PENDING"
    return
  fi
  OVERALL_STATUS="PENDING"
}

emit_json_report() {
  python3 - <<PY
import json

print(json.dumps({
    "overall_status": "${OVERALL_STATUS}",
    "base_path": "${RESOLVED_BASE_PATH}",
    "base_path_source": "${BASE_PATH_SOURCE}",
    "worker_ok": ${WORKER_OK} == 1,
    "n8n_ok": ${N8N_OK} == 1,
    "n8n_inactive": ${N8N_INACTIVE} == 1,
    "public_blog_repo_ok": ${PUBLIC_BLOG_REPO_OK} == 1,
    "public_blog_host_mount": "${PUBLIC_BLOG_HOST_MOUNT}",
    "campaign_state": "${CAMPAIGN_STATE}",
    "has_blog_publish": ${HAS_BLOG_PUBLISH} == 1,
    "has_linkedin_package": ${HAS_LINKEDIN_PACKAGE} == 1,
    "has_linkedin_distribution": ${HAS_LINKEDIN_DISTRIBUTION} == 1,
    "flow_a_complete": ${FLOW_A_COMPLETE} == 1,
    "has_smoke_artifacts": ${HAS_SMOKE_ARTIFACTS} == 1,
    "workflow_id": "${N8N_WORKFLOW_ID}",
    "post_slug_fragment": "${POST_SLUG_FRAGMENT}",
}, indent=2))
PY
}

main() {
  trap cleanup_temp_files EXIT

  info "Flow A post-smoke evidence collection (read-only)"
  echo "    worker url:      ${WORKER_BASE_URL}"
  echo "    worker container:${WORKER_CONTAINER}"
  echo "    workflow id:     ${N8N_WORKFLOW_ID}"
  echo "    workflow name:   ${N8N_WORKFLOW_NAME}"
  echo "    slug fragment:   ${POST_SLUG_FRAGMENT}"
  echo "    note: read-only; no secrets; no LinkedIn API; no deploy/restart; no n8n activation"

  section "Base path resolution"
  if ! resolve_base_path; then
    compute_overall_status
    section "Overall"
    echo "OVERALL: FAIL (editorial base path unresolved)"
    if [[ "${JSON_OUTPUT}" -eq 1 ]]; then
      emit_json_report
    fi
    exit 1
  fi
  pass "resolved base path ${RESOLVED_BASE_PATH}"
  echo "source: ${BASE_PATH_SOURCE}"

  WORKER_SECTION_OK=0
  if check_worker; then
    WORKER_SECTION_OK=1
  fi

  PUBLIC_BLOG_SECTION_OK=0
  if check_public_blog_repo; then
    PUBLIC_BLOG_SECTION_OK=1
  fi

  check_editorial_artifacts

  check_public_blog_artifacts

  N8N_SECTION_OK=0
  if check_n8n_workflow; then
    N8N_SECTION_OK=1
  fi

  compute_overall_status

  section "Overall"
  case "${OVERALL_STATUS}" in
    PASS)
      echo "OVERALL: PASS (worker OK, public blog repo ready, n8n inactive, Flow A reached distribution_scheduled or linkedin_distribution exists)"
      ;;
    PENDING)
      echo "OVERALL: PENDING (worker OK, public blog repo ready, n8n inactive; campaign has not reached distribution_scheduled)"
      echo "NOTE: run deterministic worker smoke or Flow A in n8n, then re-run this script."
      ;;
    FAIL)
      if [[ "${CAMPAIGN_STATE}" == "error" ]]; then
        echo "OVERALL: FAIL (campaign state is error; worker smoke or publish reconciliation required)"
      elif [[ "${WORKER_OK}" -eq 1 && "${N8N_OK}" -eq 1 && "${N8N_INACTIVE}" -eq 1 && "${PUBLIC_BLOG_REPO_OK}" -ne 1 ]]; then
        echo "OVERALL: FAIL (worker and n8n OK but public blog repo not mounted or incomplete)"
        echo "NOTE: publish fails with blog_publish_public_repo_not_configured until the GitHub Pages checkout is mounted at /public-blog."
      else
        echo "OVERALL: FAIL (worker, n8n, public blog repo, base path, or campaign state checks failed)"
      fi
      ;;
  esac

  if [[ "${JSON_OUTPUT}" -eq 1 ]]; then
    emit_json_report
  fi

  if [[ "${OVERALL_STATUS}" == "FAIL" ]]; then
    exit 1
  fi
  exit 0
}

main "$@"
