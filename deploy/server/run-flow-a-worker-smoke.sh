#!/usr/bin/env bash
# Deterministic Flow A worker smoke — calls publish/package/schedule without n8n UI.
# Runs on the Ubuntu server. Safety: no secrets printed, no n8n activation, no LinkedIn API,
# no git push, no destructive cleanup by default.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-/home/silverman/silverman-blog-linkedin-worker/.env}"
WORKER_BASE_URL="${WORKER_BASE_URL:-http://localhost:8010}"
RELATIVE_PATH="${RELATIVE_PATH:-blog-posts/ready/01-why-i-did-not-start-with-the-database.md}"
SITE_URL="${SITE_URL:-https://silverman.pro}"
PUBLIC_BLOG_HOST_MOUNT="${PUBLIC_BLOG_HOST_MOUNT:-/home/silverman/silverberdi.github.io}"
EDITORIAL_ROOT="${EDITORIAL_ROOT:-}"
POST_SLUG_FRAGMENT="${POST_SLUG_FRAGMENT:-why-i-did-not-start-with-the-database}"
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: run-flow-a-worker-smoke.sh [options]

Deterministic Flow A worker smoke (no n8n UI). Calls worker endpoints in order:
  GET  /health
  POST /publish-blog-post
  POST /generate-linkedin-package
  POST /schedule-linkedin-distribution

Options:
  --dry-run              Print planned requests without calling worker endpoints
  --worker-base-url URL  Worker base URL (default http://localhost:8010)
  --relative-path PATH   Ready post relative path
  --site-url URL         Canonical site URL for publish/package payloads
  --env-file PATH        Server-local .env with SILVERMAN_BLOG_LINKEDIN_API_KEY
  --editorial-root PATH  Editorial workspace root (auto-detected when omitted)
  --public-blog-root PATH  Public GitHub Pages checkout on host
  -h, --help             Show this help

Does not print API keys, activate n8n, call LinkedIn API, git push, or delete artifacts.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --worker-base-url)
      WORKER_BASE_URL="${2:?missing value for --worker-base-url}"
      shift 2
      ;;
    --relative-path)
      RELATIVE_PATH="${2:?missing value for --relative-path}"
      shift 2
      ;;
    --site-url)
      SITE_URL="${2:?missing value for --site-url}"
      shift 2
      ;;
    --env-file)
      ENV_FILE="${2:?missing value for --env-file}"
      shift 2
      ;;
    --editorial-root)
      EDITORIAL_ROOT="${2:?missing value for --editorial-root}"
      shift 2
      ;;
    --public-blog-root)
      PUBLIC_BLOG_HOST_MOUNT="${2:?missing value for --public-blog-root}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

RESPONSE_TMP=""
OVERALL_STATUS="FAIL"
REQUIRED_FAILED=0

cleanup() {
  rm -f "${RESPONSE_TMP}"
}
trap cleanup EXIT

pass() {
  echo "PASS: $*"
}

fail() {
  echo "FAIL: $*" >&2
  REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
}

info() {
  echo "==> $*"
}

section() {
  echo
  echo "=== $* ==="
}

load_env_var() {
  local key="$1"
  local line value
  line="$(grep -E "^${key}=" "${ENV_FILE}" | tail -n 1 || true)"
  if [[ -z "${line}" ]]; then
    return 1
  fi
  value="${line#*=}"
  value="${value%\"}"
  value="${value#\"}"
  value="${value%\'}"
  value="${value#\'}"
  printf '%s' "${value}"
}

pretty_json_file() {
  local path="$1"
  if command -v python3 >/dev/null 2>&1; then
    python3 -m json.tool "${path}" 2>/dev/null || cat "${path}"
  else
    cat "${path}"
  fi
}

resolve_editorial_root() {
  if [[ -n "${EDITORIAL_ROOT}" ]]; then
    printf '%s' "${EDITORIAL_ROOT}"
    return 0
  fi
  local candidate
  for candidate in \
    "/home/silverman/compartido_mac/silverman-blog-linkedin" \
    "/home/silverman/silverman-blog-linkedin" \
    "/data/silverman-blog-linkedin"; do
    if [[ -d "${candidate}/metadata/campaigns" ]]; then
      printf '%s' "${candidate}"
      return 0
    fi
  done
  return 1
}

print_campaign_snapshot() {
  local campaign_id="$1"
  local metadata_path="${EDITORIAL_ROOT}/metadata/campaigns/${campaign_id}.json"
  if [[ ! -f "${metadata_path}" ]]; then
    echo "campaign metadata: not found at ${metadata_path}"
    return 0
  fi
  python3 - "${metadata_path}" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as fh:
    data = json.load(fh)

blog_publish = data.get("blog_publish") or {}
package = data.get("linkedin_package")
distribution = data.get("linkedin_distribution")

print(f"state: {data.get('state')}")
print(f"source_public_url: {data.get('source_public_url')}")
print(
    "published_post_relative_path: "
    f"{blog_publish.get('public_repo_path')}"
)
print(
    "published_image_relative_path: "
    f"{blog_publish.get('public_repo_image_path')}"
)
print(f"linkedin_package: {'present' if package else 'None'}")
print(f"linkedin_distribution: {'present' if distribution else 'None'}")
errors = data.get("errors") or []
print(f"errors: {errors if errors else '[]'}")
PY
}

assert_json_field() {
  local path="$1"
  local field_expr="$2"
  local label="$3"
  python3 - "${path}" "${field_expr}" "${label}" <<'PY'
import json
import sys

path, expr, label = sys.argv[1:4]
with open(path, encoding="utf-8") as fh:
    data = json.load(fh)

value = data
for part in expr.split("."):
    if not part:
        continue
    if part not in value:
        print(f"missing required response field: {label} ({expr})")
        sys.exit(1)
    value = value[part]

if value in (None, ""):
    print(f"missing required response field: {label} ({expr})")
    sys.exit(1)
PY
}

check_step_response() {
  local step_name="$1"
  local http_code="$2"
  local expected_status="${3:-}"

  if [[ "${http_code}" != "200" ]]; then
    fail "${step_name}: HTTP ${http_code}"
    pretty_json_file "${RESPONSE_TMP}"
    return 1
  fi

  if ! python3 -m json.tool "${RESPONSE_TMP}" >/dev/null 2>&1; then
    fail "${step_name}: response is not valid JSON"
    cat "${RESPONSE_TMP}"
    return 1
  fi

  local status state
  status="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("status",""))' "${RESPONSE_TMP}")"
  state="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("state",""))' "${RESPONSE_TMP}")"
  if [[ -z "${status}" ]]; then
    fail "${step_name}: missing status field"
    pretty_json_file "${RESPONSE_TMP}"
    return 1
  fi
  if [[ "${status}" == "failed" ]]; then
    fail "${step_name}: worker returned status=failed"
    if [[ -n "${state}" ]]; then
      echo "response state: ${state}"
    fi
    python3 - "${RESPONSE_TMP}" <<'PY' || true
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    data = json.load(fh)

errors = data.get("errors") or []
if errors:
    print(f"response errors: {errors}")
source_public_url = data.get("source_public_url")
if source_public_url:
    print(f"response source_public_url: {source_public_url}")
blog_publish = data.get("blog_publish") or {}
skip_reason = blog_publish.get("reconciliation_skip_reason")
if skip_reason:
    print(f"reconciliation_skip_reason: {skip_reason}")
for key in (
    "reconciliation_expected_post_relative_path",
    "reconciliation_actual_post_relative_path",
    "reconciliation_expected_post_sha256",
    "reconciliation_actual_post_sha256",
    "reconciliation_expected_image_sha256",
    "reconciliation_actual_image_sha256",
):
    value = blog_publish.get(key)
    if value:
        print(f"{key}: {value}")
PY
    pretty_json_file "${RESPONSE_TMP}"
    return 1
  fi
  if [[ -n "${expected_status}" && "${status}" != "${expected_status}" ]]; then
    fail "${step_name}: expected status=${expected_status}, got status=${status}"
    if [[ -n "${state}" ]]; then
      echo "response state: ${state}"
    fi
    pretty_json_file "${RESPONSE_TMP}"
    return 1
  fi

  pass "${step_name}: HTTP 200 status=${status}"
  if [[ -n "${state}" ]]; then
    echo "response state: ${state}"
  fi
  if [[ "${step_name}" == "publish-blog-post" && "${status}" != "failed" ]]; then
    python3 - "${RESPONSE_TMP}" <<'PY' || true
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    data = json.load(fh)

blog_publish = data.get("blog_publish") or {}
for key in (
    "public_image_adopted",
    "public_image_source",
    "ready_image_sha256",
    "published_image_sha256",
):
    value = blog_publish.get(key)
    if value is not None and value != "":
        print(f"{key}: {value}")
PY
  fi
  pretty_json_file "${RESPONSE_TMP}"
  return 0
}

call_worker() {
  local method="$1"
  local path="$2"
  local body="${3:-}"
  local auth_header=()

  if [[ -n "${API_KEY:-}" ]]; then
    auth_header=(-H "Authorization: Bearer ${API_KEY}")
  fi

  if [[ "${method}" == "GET" ]]; then
    curl -sS -o "${RESPONSE_TMP}" -w '%{http_code}' \
      "${WORKER_BASE_URL}${path}" \
      "${auth_header[@]}"
  else
    curl -sS -o "${RESPONSE_TMP}" -w '%{http_code}' \
      -X "${method}" "${WORKER_BASE_URL}${path}" \
      "${auth_header[@]}" \
      -H "Content-Type: application/json" \
      -d "${body}"
  fi
}

verify_public_artifacts() {
  local posts_dir="${PUBLIC_BLOG_HOST_MOUNT}/_posts"
  local images_dir="${PUBLIC_BLOG_HOST_MOUNT}/assets/images"
  local found_post=0
  local found_image=0

  if [[ -d "${posts_dir}" ]]; then
    if find "${posts_dir}" -maxdepth 1 -type f -name "*${POST_SLUG_FRAGMENT}*" | grep -q .; then
      pass "public post exists under ${posts_dir}"
      found_post=1
    else
      fail "no public post matching *${POST_SLUG_FRAGMENT}* under ${posts_dir}"
    fi
  else
    fail "public posts directory missing: ${posts_dir}"
  fi

  if [[ -d "${images_dir}" ]]; then
    if find "${images_dir}" -maxdepth 1 -type f -name "*${POST_SLUG_FRAGMENT}*" | grep -q .; then
      pass "public image exists under ${images_dir}"
      found_image=1
    else
      fail "no public image matching *${POST_SLUG_FRAGMENT}* under ${images_dir}"
    fi
  else
    fail "public images directory missing: ${images_dir}"
  fi

  [[ "${found_post}" -eq 1 && "${found_image}" -eq 1 ]]
}

verify_generated_artifacts() {
  local generated_root="${EDITORIAL_ROOT}/linkedin-posts/generated"
  if [[ ! -d "${generated_root}" ]]; then
    fail "generated LinkedIn artifacts directory missing: ${generated_root}"
    return 1
  fi
  if find "${generated_root}" -type f -name "*.md" | grep -q .; then
    pass "generated LinkedIn artifacts exist under ${generated_root}"
    return 0
  fi
  fail "no generated LinkedIn artifacts under ${generated_root}"
  return 1
}

verify_campaign_distribution_complete() {
  local campaign_id="$1"
  local metadata_path="${EDITORIAL_ROOT}/metadata/campaigns/${campaign_id}.json"
  python3 - "${metadata_path}" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as fh:
    data = json.load(fh)

state = data.get("state")
distribution = data.get("linkedin_distribution")
allowed_states = {
    "distribution_scheduled",
    "distribution_complete",
    "flow_a_complete",
}

if state not in allowed_states:
    print(f"campaign state {state!r} did not reach distribution_scheduled")
    sys.exit(1)
if distribution is None:
    print("linkedin_distribution metadata is missing")
    sys.exit(1)
print(f"campaign state reached {state} with linkedin_distribution present")
PY
}

section "Flow A worker smoke"
info "worker: ${WORKER_BASE_URL}"
info "env:    ${ENV_FILE}"
info "post:   ${RELATIVE_PATH}"
info "site:   ${SITE_URL}"
info "public blog: ${PUBLIC_BLOG_HOST_MOUNT}"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "DRY-RUN: would call GET ${WORKER_BASE_URL}/health"
  echo "DRY-RUN: would call POST ${WORKER_BASE_URL}/publish-blog-post"
  echo "DRY-RUN: would call POST ${WORKER_BASE_URL}/generate-linkedin-package"
  echo "DRY-RUN: would call POST ${WORKER_BASE_URL}/schedule-linkedin-distribution"
  echo
  echo "OVERALL: PASS (dry-run)"
  exit 0
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  fail "missing server-local .env at ${ENV_FILE}"
  echo
  echo "OVERALL: FAIL"
  exit 1
fi

API_KEY="$(load_env_var SILVERMAN_BLOG_LINKEDIN_API_KEY || true)"
if [[ -z "${API_KEY}" ]]; then
  fail "SILVERMAN_BLOG_LINKEDIN_API_KEY not set in ${ENV_FILE}"
  echo
  echo "OVERALL: FAIL"
  exit 1
fi

if ! EDITORIAL_ROOT="$(resolve_editorial_root)"; then
  fail "could not resolve editorial workspace root (use --editorial-root)"
  echo
  echo "OVERALL: FAIL"
  exit 1
fi
info "editorial root: ${EDITORIAL_ROOT}"

RESPONSE_TMP="$(mktemp)"
CAMPAIGN_ID=""

section "Step 1: GET /health"
HEALTH_HTTP="$(call_worker GET /health)"
if ! check_step_response "health" "${HEALTH_HTTP}"; then
  echo
  echo "OVERALL: FAIL"
  exit 1
fi

section "Step 2: POST /publish-blog-post"
PUBLISH_BODY="$(python3 -c 'import json,sys; print(json.dumps({"source_relative_path": sys.argv[1], "site_url": sys.argv[2]}))' "${RELATIVE_PATH}" "${SITE_URL}")"
PUBLISH_HTTP="$(call_worker POST /publish-blog-post "${PUBLISH_BODY}")"
if ! check_step_response "publish-blog-post" "${PUBLISH_HTTP}" "completed"; then
  if python3 -m json.tool "${RESPONSE_TMP}" >/dev/null 2>&1; then
    CAMPAIGN_ID="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("campaign_id") or "")' "${RESPONSE_TMP}")"
    if [[ -n "${CAMPAIGN_ID}" ]]; then
      section "Campaign metadata after publish failure"
      print_campaign_snapshot "${CAMPAIGN_ID}"
    fi
  fi
  echo
  echo "OVERALL: FAIL"
  exit 1
fi
assert_json_field "${RESPONSE_TMP}" "campaign_id" "campaign_id"
CAMPAIGN_ID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["campaign_id"])' "${RESPONSE_TMP}")"
section "Campaign metadata after publish"
print_campaign_snapshot "${CAMPAIGN_ID}"

section "Step 3: POST /generate-linkedin-package"
PACKAGE_BODY="$(python3 -c 'import json,sys; print(json.dumps({"campaign_id": sys.argv[1], "site_url": sys.argv[2]}))' "${CAMPAIGN_ID}" "${SITE_URL}")"
PACKAGE_HTTP="$(call_worker POST /generate-linkedin-package "${PACKAGE_BODY}")"
if ! check_step_response "generate-linkedin-package" "${PACKAGE_HTTP}" "completed"; then
  if grep -q "deepseek_config_invalid" "${RESPONSE_TMP}" 2>/dev/null; then
    fail "generate-linkedin-package blocked by deepseek_config_invalid — configure DEEPSEEK_API_KEY in ${ENV_FILE}"
  fi
  section "Campaign metadata after package failure"
  print_campaign_snapshot "${CAMPAIGN_ID}"
  echo
  echo "OVERALL: FAIL"
  exit 1
fi
section "Campaign metadata after package"
print_campaign_snapshot "${CAMPAIGN_ID}"

section "Step 4: POST /schedule-linkedin-distribution"
SCHEDULE_BODY="$(python3 -c 'import json,sys; print(json.dumps({"campaign_id": sys.argv[1]}))' "${CAMPAIGN_ID}")"
SCHEDULE_HTTP="$(call_worker POST /schedule-linkedin-distribution "${SCHEDULE_BODY}")"
if ! check_step_response "schedule-linkedin-distribution" "${SCHEDULE_HTTP}" "completed"; then
  section "Campaign metadata after schedule failure"
  print_campaign_snapshot "${CAMPAIGN_ID}"
  echo
  echo "OVERALL: FAIL"
  exit 1
fi
section "Campaign metadata after schedule"
print_campaign_snapshot "${CAMPAIGN_ID}"

section "Artifact verification"
verify_public_artifacts || true
verify_generated_artifacts || true
if ! verify_campaign_distribution_complete "${CAMPAIGN_ID}"; then
  fail "campaign did not reach distribution_scheduled with linkedin_distribution metadata"
else
  pass "campaign reached distribution_scheduled with linkedin_distribution metadata"
fi

echo
if [[ "${REQUIRED_FAILED}" -eq 0 ]]; then
  OVERALL_STATUS="PASS"
fi
echo "OVERALL: ${OVERALL_STATUS} (final campaign state must be distribution_scheduled with linkedin_distribution)"
if [[ "${OVERALL_STATUS}" == "FAIL" ]]; then
  exit 1
fi
