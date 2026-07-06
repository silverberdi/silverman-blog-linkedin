#!/usr/bin/env bash
# Smoke test for silverman-blog-linkedin-worker on the Ubuntu server (localhost:8010).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="${DEPLOY_DIR:-${SCRIPT_DIR}}"
ENV_FILE="${DEPLOY_DIR}/.env"
WORKER_BASE_URL="${WORKER_BASE_URL:-http://localhost:8010}"
EDITORIAL_ROOT="${EDITORIAL_ROOT:-/home/silverman/compartido_mac/silverman-blog-linkedin}"

REQUIRED_PASSED=0
REQUIRED_FAILED=0
OPTIONAL_SKIPPED=0

pass() {
  echo "PASS: $*"
}

fail() {
  echo "FAIL: $*" >&2
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

echo "==> silverman-blog-linkedin worker smoke test"
echo "    worker: ${WORKER_BASE_URL}"
echo "    env:    ${ENV_FILE}"
echo

if [[ ! -f "${ENV_FILE}" ]]; then
  fail "missing server-local .env at ${ENV_FILE}"
  echo
  echo "OVERALL: FAIL (${REQUIRED_FAILED} required check(s) failed)"
  exit 1
fi

API_KEY="$(load_env_var SILVERMAN_BLOG_LINKEDIN_API_KEY || true)"
if [[ -z "${API_KEY}" ]]; then
  fail "SILVERMAN_BLOG_LINKEDIN_API_KEY not set in ${ENV_FILE}"
  REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
else
  # --- Required: GET /health ---
  HEALTH_HTTP_CODE="$(curl -sS -o /tmp/silverman-worker-health.json -w '%{http_code}' \
    "${WORKER_BASE_URL}/health" || echo "000")"
  if [[ "${HEALTH_HTTP_CODE}" == "200" ]]; then
    pass "GET ${WORKER_BASE_URL}/health returned HTTP 200"
    REQUIRED_PASSED=$((REQUIRED_PASSED + 1))
  else
    fail "GET ${WORKER_BASE_URL}/health returned HTTP ${HEALTH_HTTP_CODE}"
    REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
  fi

  # --- Required: POST /process-ready ---
  PROCESS_HTTP_CODE="$(curl -sS -o /tmp/silverman-worker-process-ready.json -w '%{http_code}' \
    -X POST "${WORKER_BASE_URL}/process-ready" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" || echo "000")"
  if [[ "${PROCESS_HTTP_CODE}" == "200" ]]; then
    pass "POST ${WORKER_BASE_URL}/process-ready returned HTTP 200"
    REQUIRED_PASSED=$((REQUIRED_PASSED + 1))
  else
    fail "POST ${WORKER_BASE_URL}/process-ready returned HTTP ${PROCESS_HTTP_CODE}"
    REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
  fi
fi

# --- Optional: generation smoke when DeepSeek key and ready markdown exist ---
DEEPSEEK_KEY="$(load_env_var DEEPSEEK_API_KEY || true)"
READY_MD=""
if [[ -d "${EDITORIAL_ROOT}/blog-posts/ready" ]]; then
  READY_MD="$(find "${EDITORIAL_ROOT}/blog-posts/ready" -maxdepth 1 -type f -name '*.md' | head -n 1 || true)"
fi

if [[ -z "${DEEPSEEK_KEY}" || "${DEEPSEEK_KEY}" == CHANGE_ME* ]]; then
  echo "SKIP: optional generation smoke (DEEPSEEK_API_KEY not configured)"
  OPTIONAL_SKIPPED=$((OPTIONAL_SKIPPED + 1))
elif [[ -z "${READY_MD}" ]]; then
  echo "SKIP: optional generation smoke (no .md files in blog-posts/ready)"
  OPTIONAL_SKIPPED=$((OPTIONAL_SKIPPED + 1))
elif [[ -n "${API_KEY}" ]]; then
  RELATIVE_PATH="blog-posts/ready/$(basename "${READY_MD}")"
  MARKDOWN_CONTENT="$(cat "${READY_MD}")"
  GENERATE_HTTP_CODE="$(curl -sS -o /tmp/silverman-worker-generate.json -w '%{http_code}' \
    -X POST "${WORKER_BASE_URL}/generate-linkedin-draft" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d "$(python3 -c 'import json,sys; print(json.dumps({"source_relative_path": sys.argv[1], "markdown_content": sys.argv[2], "slug_hint": "smoke-test"}))' "${RELATIVE_PATH}" "${MARKDOWN_CONTENT}")" \
    || echo "000")"
  if [[ "${GENERATE_HTTP_CODE}" == "200" ]]; then
    pass "optional POST ${WORKER_BASE_URL}/generate-linkedin-draft returned HTTP 200"
  else
    echo "WARN: optional generation smoke returned HTTP ${GENERATE_HTTP_CODE} (not required for overall PASS)"
  fi
fi

echo
if [[ "${REQUIRED_FAILED}" -eq 0 ]]; then
  echo "OVERALL: PASS (${REQUIRED_PASSED} required check(s) passed)"
  exit 0
fi

echo "OVERALL: FAIL (${REQUIRED_FAILED} required check(s) failed)"
exit 1
