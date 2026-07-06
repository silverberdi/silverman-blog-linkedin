#!/usr/bin/env bash
# Verify worker API key rotation: health OK, old Bearer rejected, new Bearer accepted.
# Never prints, writes, or logs API key values.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="${DEPLOY_DIR:-${SCRIPT_DIR}}"
ENV_FILE="${ENV_FILE:-${DEPLOY_DIR}/.env}"
WORKER_BASE_URL="${WORKER_BASE_URL:-http://localhost:8010}"

REQUIRED_PASSED=0
REQUIRED_FAILED=0

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

echo "==> silverman-blog-linkedin worker API key rotation verification"
echo "    worker: ${WORKER_BASE_URL}"
echo "    env:    ${ENV_FILE}"
echo

if [[ ! -f "${ENV_FILE}" ]]; then
  fail "missing server-local .env at ${ENV_FILE}"
  echo
  echo "OVERALL: FAIL (1 required check(s) failed)"
  exit 1
fi

if [[ -z "${OLD_SILVERMAN_BLOG_LINKEDIN_API_KEY:-}" ]]; then
  fail "OLD_SILVERMAN_BLOG_LINKEDIN_API_KEY environment variable is not set"
  echo "    Set it to the previous key before rotation (never pass keys as script arguments)."
  echo
  echo "OVERALL: FAIL (1 required check(s) failed)"
  exit 1
fi

NEW_API_KEY="$(load_env_var SILVERMAN_BLOG_LINKEDIN_API_KEY || true)"
if [[ -z "${NEW_API_KEY}" ]]; then
  fail "SILVERMAN_BLOG_LINKEDIN_API_KEY not set in ${ENV_FILE}"
  REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
else
  OLD_API_KEY="${OLD_SILVERMAN_BLOG_LINKEDIN_API_KEY}"

  if [[ "${OLD_API_KEY}" == "${NEW_API_KEY}" ]]; then
    fail "old and new API keys are identical; rotation verification requires different values"
    REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
  else
    # --- Required: GET /health (unauthenticated) ---
    HEALTH_HTTP_CODE="$(curl -sS -o /tmp/silverman-worker-rotation-health.json -w '%{http_code}' \
      "${WORKER_BASE_URL}/health" || echo "000")"
    if [[ "${HEALTH_HTTP_CODE}" == "200" ]]; then
      pass "GET ${WORKER_BASE_URL}/health returned HTTP 200"
      REQUIRED_PASSED=$((REQUIRED_PASSED + 1))
    else
      fail "GET ${WORKER_BASE_URL}/health returned HTTP ${HEALTH_HTTP_CODE}"
      REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
    fi

    # --- Required: POST /process-ready with old Bearer (expect 401) ---
    OLD_HTTP_CODE="$(curl -sS -o /tmp/silverman-worker-rotation-old.json -w '%{http_code}' \
      -X POST "${WORKER_BASE_URL}/process-ready" \
      -H "Authorization: Bearer ${OLD_API_KEY}" \
      -H "Content-Type: application/json" || echo "000")"
    if [[ "${OLD_HTTP_CODE}" == "401" ]]; then
      pass "POST ${WORKER_BASE_URL}/process-ready with previous Bearer returned HTTP 401"
      REQUIRED_PASSED=$((REQUIRED_PASSED + 1))
    else
      fail "POST ${WORKER_BASE_URL}/process-ready with previous Bearer returned HTTP ${OLD_HTTP_CODE} (expected 401)"
      REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
    fi

    # --- Required: POST /process-ready with new Bearer (expect 200) ---
    NEW_HTTP_CODE="$(curl -sS -o /tmp/silverman-worker-rotation-new.json -w '%{http_code}' \
      -X POST "${WORKER_BASE_URL}/process-ready" \
      -H "Authorization: Bearer ${NEW_API_KEY}" \
      -H "Content-Type: application/json" || echo "000")"
    if [[ "${NEW_HTTP_CODE}" == "200" ]]; then
      pass "POST ${WORKER_BASE_URL}/process-ready with current Bearer returned HTTP 200"
      REQUIRED_PASSED=$((REQUIRED_PASSED + 1))
    else
      fail "POST ${WORKER_BASE_URL}/process-ready with current Bearer returned HTTP ${NEW_HTTP_CODE} (expected 200)"
      REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
    fi
  fi
fi

echo
if [[ "${REQUIRED_FAILED}" -eq 0 ]]; then
  echo "OVERALL: PASS (${REQUIRED_PASSED} required check(s) passed)"
  exit 0
fi

echo "OVERALL: FAIL (${REQUIRED_FAILED} required check(s) failed)"
exit 1
