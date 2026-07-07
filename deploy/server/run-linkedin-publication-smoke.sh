#!/usr/bin/env bash
# LinkedIn publication smoke — queue, publish-due, and optional cancel against the worker.
# Defaults to dry-run (safe). Real LinkedIn publish requires explicit flags and env enablement.
# Never prints secrets.
set -euo pipefail

ENV_FILE="${ENV_FILE:-/home/silverman/silverman-blog-linkedin-worker/.env}"
WORKER_BASE_URL="${WORKER_BASE_URL:-http://localhost:8010}"
CAMPAIGN_ID="${CAMPAIGN_ID:-}"
VARIANT="${VARIANT:-executive-recruiter}"
REAL_MODE=0
REAL_PUBLISH=0
RUN_CANCEL=0
CANCEL_DRY_RUN=1

usage() {
  cat <<'EOF'
Usage: run-linkedin-publication-smoke.sh [options]

Exercises LinkedIn publication worker endpoints:
  POST /queue-linkedin-publication
  POST /publish-linkedin-due-variants
  POST /cancel-linkedin-publication (optional)

Defaults to dry-run for all steps (no LinkedIn API calls).
Real queue (--real) mutates campaign metadata but still does not call LinkedIn.
Real publish (--real-publish) requires SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true and credentials.

Options:
  --real                 Real queue (dry_run=false on queue step)
  --real-publish         Real publish-due (dry_run=false; requires publication enabled)
  --cancel               Also run cancel step after publish-due (dry-run by default)
  --cancel-real          Run cancel with dry_run=false (only when --cancel)
  --campaign-id ID       Campaign id (auto-detected from latest metadata when omitted)
  --variant ID           Variant id (default executive-recruiter)
  --worker-base-url URL  Worker base URL (default http://localhost:8010)
  --env-file PATH        Server-local .env with SILVERMAN_BLOG_LINKEDIN_API_KEY
  -h, --help             Show this help

Does not print API keys or LinkedIn access tokens.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --real)
      REAL_MODE=1
      shift
      ;;
    --real-publish)
      REAL_PUBLISH=1
      shift
      ;;
    --cancel)
      RUN_CANCEL=1
      shift
      ;;
    --cancel-real)
      RUN_CANCEL=1
      CANCEL_DRY_RUN=0
      shift
      ;;
    --campaign-id)
      CAMPAIGN_ID="${2:?missing value for --campaign-id}"
      shift 2
      ;;
    --variant)
      VARIANT="${2:?missing value for --variant}"
      shift 2
      ;;
    --worker-base-url)
      WORKER_BASE_URL="${2:?missing value for --worker-base-url}"
      shift 2
      ;;
    --env-file)
      ENV_FILE="${2:?missing value for --env-file}"
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

resolve_latest_campaign_id() {
  local root="$1"
  python3 - "${root}" <<'PY'
import sys
from pathlib import Path

root = Path(sys.argv[1]) / "metadata" / "campaigns"
if not root.is_dir():
    sys.exit(1)
files = sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
if not files:
    sys.exit(1)
print(files[0].stem)
PY
}

print_variant_publish_state() {
  local root="$1"
  local campaign_id="$2"
  local variant="$3"
  python3 - "${root}" "${campaign_id}" "${variant}" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
campaign_id = sys.argv[2]
variant = sys.argv[3]
path = root / "metadata" / "campaigns" / f"{campaign_id}.json"
if not path.is_file():
    print(f"variant publish_state: (campaign metadata not found)")
    sys.exit(0)
with open(path, encoding="utf-8") as fh:
    data = json.load(fh)
for entry in data.get("variants") or []:
    if entry.get("variant") == variant:
        print(f"variant publish_state: {entry.get('publish_state')}")
        if entry.get("publish_after_utc"):
            print(f"publish_after_utc: {entry.get('publish_after_utc')}")
        if entry.get("published_at"):
            print(f"published_at: {entry.get('published_at')}")
        if entry.get("linkedin_post_urn"):
            print(f"linkedin_post_urn: {entry.get('linkedin_post_urn')}")
        sys.exit(0)
print(f"variant publish_state: (variant {variant!r} not found)")
PY
}

call_worker() {
  local path="$1"
  local body="$2"
  local auth_header=()

  if [[ ! -f "${ENV_FILE}" ]]; then
    fail "env file not found: ${ENV_FILE}"
    return 1
  fi

  local api_key
  api_key="$(load_env_var SILVERMAN_BLOG_LINKEDIN_API_KEY || true)"
  if [[ -z "${api_key}" ]]; then
    fail "SILVERMAN_BLOG_LINKEDIN_API_KEY not set in ${ENV_FILE}"
    return 1
  fi
  auth_header=(-H "Authorization: Bearer ${api_key}")

  RESPONSE_TMP="$(mktemp)"
  local http_code
  http_code="$(curl -sS -o "${RESPONSE_TMP}" -w '%{http_code}' \
    -X POST "${WORKER_BASE_URL}${path}" \
    -H "Content-Type: application/json" \
    "${auth_header[@]}" \
    -d "${body}" 2>/dev/null || echo "000")"

  if [[ "${http_code}" != "200" ]]; then
    fail "${path}: HTTP ${http_code}"
    pretty_json_file "${RESPONSE_TMP}"
    return 1
  fi

  if ! python3 -m json.tool "${RESPONSE_TMP}" >/dev/null 2>&1; then
    fail "${path}: response is not valid JSON"
    cat "${RESPONSE_TMP}"
    return 1
  fi

  local serialized
  serialized="$(cat "${RESPONSE_TMP}")"
  if [[ "${serialized}" == *"${api_key}"* ]]; then
    fail "${path}: response appears to contain API key (unexpected)"
    return 1
  fi

  pretty_json_file "${RESPONSE_TMP}"
  return 0
}

main() {
  section "LinkedIn publication smoke"
  echo "worker url: ${WORKER_BASE_URL}"
  echo "variant:    ${VARIANT}"
  echo "real queue: $([[ ${REAL_MODE} -eq 1 ]] && echo yes || echo no)"
  echo "real publish: $([[ ${REAL_PUBLISH} -eq 1 ]] && echo yes || echo no)"
  echo "cancel step: $([[ ${RUN_CANCEL} -eq 1 ]] && echo yes || echo no)"

  EDITORIAL_ROOT=""
  if EDITORIAL_ROOT="$(resolve_editorial_root)"; then
    pass "editorial root ${EDITORIAL_ROOT}"
  else
    echo "INFO: editorial root not resolved; variant state snapshots skipped"
  fi

  if [[ -z "${CAMPAIGN_ID}" && -n "${EDITORIAL_ROOT}" ]]; then
    if CAMPAIGN_ID="$(resolve_latest_campaign_id "${EDITORIAL_ROOT}")"; then
      pass "auto-detected campaign_id ${CAMPAIGN_ID}"
    else
      fail "could not auto-detect campaign_id; pass --campaign-id"
    fi
  elif [[ -z "${CAMPAIGN_ID}" ]]; then
    fail "campaign_id required when editorial root unavailable"
  fi

  if [[ "${REAL_PUBLISH}" -eq 1 ]]; then
    local enabled
    enabled="$(load_env_var SILVERMAN_LINKEDIN_PUBLICATION_ENABLED 2>/dev/null || echo "")"
    if [[ "${enabled}" != "true" && "${enabled}" != "1" && "${enabled}" != "yes" ]]; then
      fail "real publish requested but SILVERMAN_LINKEDIN_PUBLICATION_ENABLED is not true"
      echo "Remediation: set SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true in ${ENV_FILE}" >&2
      section "Overall"
      echo "OVERALL: FAIL"
      exit 1
    fi
  fi

  section "Variant state before queue"
  if [[ -n "${EDITORIAL_ROOT}" ]]; then
    print_variant_publish_state "${EDITORIAL_ROOT}" "${CAMPAIGN_ID}" "${VARIANT}"
  fi

  section "Queue LinkedIn publication"
  local queue_dry_run="true"
  if [[ "${REAL_MODE}" -eq 1 ]]; then
    queue_dry_run="false"
  fi
  if ! call_worker "/queue-linkedin-publication" \
    "{\"campaign_id\":\"${CAMPAIGN_ID}\",\"variant\":\"${VARIANT}\",\"dry_run\":${queue_dry_run}}"; then
    section "Overall"
    echo "OVERALL: FAIL"
    exit 1
  fi
  pass "queue step completed"

  section "Variant state after queue"
  if [[ -n "${EDITORIAL_ROOT}" ]]; then
    print_variant_publish_state "${EDITORIAL_ROOT}" "${CAMPAIGN_ID}" "${VARIANT}"
  fi

  section "Publish due variants"
  local publish_dry_run="true"
  if [[ "${REAL_PUBLISH}" -eq 1 ]]; then
    publish_dry_run="false"
  fi
  if ! call_worker "/publish-linkedin-due-variants" \
    "{\"campaign_id\":\"${CAMPAIGN_ID}\",\"variant\":\"${VARIANT}\",\"dry_run\":${publish_dry_run}}"; then
    section "Overall"
    echo "OVERALL: FAIL"
    exit 1
  fi
  pass "publish-due step completed"

  section "Variant state after publish-due"
  if [[ -n "${EDITORIAL_ROOT}" ]]; then
    print_variant_publish_state "${EDITORIAL_ROOT}" "${CAMPAIGN_ID}" "${VARIANT}"
  fi

  if [[ "${RUN_CANCEL}" -eq 1 ]]; then
    section "Cancel LinkedIn publication"
    local cancel_dry_run="true"
    if [[ "${CANCEL_DRY_RUN}" -eq 0 ]]; then
      cancel_dry_run="false"
    fi
    if ! call_worker "/cancel-linkedin-publication" \
      "{\"campaign_id\":\"${CAMPAIGN_ID}\",\"variant\":\"${VARIANT}\",\"dry_run\":${cancel_dry_run}}"; then
      section "Overall"
      echo "OVERALL: FAIL"
      exit 1
    fi
    pass "cancel step completed"
    section "Variant state after cancel"
    if [[ -n "${EDITORIAL_ROOT}" ]]; then
      print_variant_publish_state "${EDITORIAL_ROOT}" "${CAMPAIGN_ID}" "${VARIANT}"
    fi
  fi

  section "Overall"
  if [[ "${REQUIRED_FAILED}" -eq 0 ]]; then
    OVERALL_STATUS="PASS"
    echo "OVERALL: PASS"
    exit 0
  fi
  echo "OVERALL: FAIL"
  exit 1
}

main "$@"
