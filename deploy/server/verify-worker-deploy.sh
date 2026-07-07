#!/usr/bin/env bash
# Post-deploy verification for silverman-blog-linkedin-worker.
# Confirms synced Flow A source files, container identity, and OpenAPI surface.
# Does not print secrets or call LinkedIn API.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="${DEPLOY_DIR:-${SCRIPT_DIR}}"
WORKER_BASE_URL="${WORKER_BASE_URL:-http://localhost:8010}"
CONTAINER_NAME="${WORKER_CONTAINER_NAME:-silverman-blog-linkedin-worker}"

FLOW_A_SOURCE_FILES=(
  "src/silverman_blog_linkedin/main.py"
  "src/silverman_blog_linkedin/blog_publish_flow.py"
  "src/silverman_blog_linkedin/linkedin_package_flow.py"
  "src/silverman_blog_linkedin/linkedin_distribution_schedule.py"
)

REQUIRED_OPENAPI_PATHS=(
  "/health"
  "/process-ready"
  "/publish-blog-post"
  "/generate-linkedin-package"
  "/schedule-linkedin-distribution"
)

REQUIRED_PASSED=0
REQUIRED_FAILED=0
VERIFY_MAX_ATTEMPTS="${VERIFY_MAX_ATTEMPTS:-30}"
VERIFY_RETRY_INTERVAL_SECONDS="${VERIFY_RETRY_INTERVAL_SECONDS:-2}"

pass() {
  echo "PASS: $*"
}

fail() {
  echo "FAIL: $*" >&2
}

wait_for_worker_http_200() {
  local label="$1"
  local url="$2"
  local attempt=1
  local http_code="000"

  while [[ "${attempt}" -le "${VERIFY_MAX_ATTEMPTS}" ]]; do
    echo "waiting for worker ${label}... attempt ${attempt}/${VERIFY_MAX_ATTEMPTS}"
    http_code="$(curl -sS -o /dev/null -w '%{http_code}' "${url}" 2>/dev/null || echo "000")"
    if [[ "${http_code}" == "200" ]]; then
      pass "GET ${url} returned HTTP 200"
      return 0
    fi
    if [[ "${attempt}" -lt "${VERIFY_MAX_ATTEMPTS}" ]]; then
      sleep "${VERIFY_RETRY_INTERVAL_SECONDS}"
    fi
    attempt=$((attempt + 1))
  done

  fail "GET ${url} did not return HTTP 200 after ${VERIFY_MAX_ATTEMPTS} attempts (last: HTTP ${http_code})"
  return 1
}

echo "==> silverman-blog-linkedin worker deploy verification"
echo "    deploy dir: ${DEPLOY_DIR}"
echo "    worker:     ${WORKER_BASE_URL}"
echo "    container:  ${CONTAINER_NAME}"
echo

if [[ ! -d "${DEPLOY_DIR}" ]]; then
  fail "deploy directory does not exist: ${DEPLOY_DIR}"
  echo
  echo "OVERALL: FAIL (${REQUIRED_FAILED} required check(s) failed)"
  exit 1
fi

echo "==> Target directory Flow A source files"
for rel in "${FLOW_A_SOURCE_FILES[@]}"; do
  path="${DEPLOY_DIR}/${rel}"
  if [[ -f "${path}" ]]; then
    if command -v shasum >/dev/null 2>&1; then
      digest="$(shasum -a 256 "${path}" | awk '{print $1}')"
      pass "${rel} present (sha256 ${digest:0:12}...)"
    elif command -v sha256sum >/dev/null 2>&1; then
      digest="$(sha256sum "${path}" | awk '{print $1}')"
      pass "${rel} present (sha256 ${digest:0:12}...)"
    else
      pass "${rel} present"
    fi
    REQUIRED_PASSED=$((REQUIRED_PASSED + 1))
  else
    fail "missing required source file: ${rel}"
    REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
  fi
done
echo

echo "==> Running worker container"
if command -v docker >/dev/null 2>&1; then
  if docker ps --format '{{.Names}}' | grep -Fxq "${CONTAINER_NAME}"; then
    container_id="$(docker inspect -f '{{.Id}}' "${CONTAINER_NAME}")"
    image_id="$(docker inspect -f '{{.Image}}' "${CONTAINER_NAME}")"
    started_at="$(docker inspect -f '{{.State.StartedAt}}' "${CONTAINER_NAME}")"
    ports="$(docker port "${CONTAINER_NAME}" 8000/tcp 2>/dev/null || true)"
    pass "container ${CONTAINER_NAME} running (id ${container_id:0:12}, started ${started_at})"
    pass "container image ${image_id:0:19}"
    if [[ -n "${ports}" ]]; then
      pass "container port mapping 8000/tcp -> ${ports}"
    else
      fail "container ${CONTAINER_NAME} has no published 8000/tcp mapping"
      REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
    fi
    REQUIRED_PASSED=$((REQUIRED_PASSED + 1))
  else
    fail "container ${CONTAINER_NAME} is not running"
    REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
  fi
else
  fail "docker not available; cannot verify container identity"
  REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
fi
echo

echo "==> Public blog repo mount (Flow A publish)"
if command -v docker >/dev/null 2>&1; then
  if docker ps --format '{{.Names}}' | grep -Fxq "${CONTAINER_NAME}"; then
    pages_repo_path="$(
      docker inspect "${CONTAINER_NAME}" 2>/dev/null | python3 - <<'PY' || true
import json
import sys

try:
    payload = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(1)
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

    if [[ "${pages_repo_path}" == "/public-blog" ]]; then
      pass "container env SILVERMAN_GITHUB_PAGES_REPO_PATH=/public-blog"
      REQUIRED_PASSED=$((REQUIRED_PASSED + 1))
    else
      fail "container env SILVERMAN_GITHUB_PAGES_REPO_PATH is ${pages_repo_path:-unset}, expected /public-blog"
      REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
    fi

    for rel in "_posts" "assets/images"; do
      if docker exec "${CONTAINER_NAME}" test -d "/public-blog/${rel}" 2>/dev/null; then
        pass "container path /public-blog/${rel} exists"
        REQUIRED_PASSED=$((REQUIRED_PASSED + 1))
      else
        fail "container path /public-blog/${rel} missing (public blog repo not mounted or incomplete checkout)"
        REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
      fi
    done

    host_mount="$(
      docker inspect "${CONTAINER_NAME}" 2>/dev/null | python3 - <<'PY' || true
import json
import sys

try:
    payload = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(1)
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
    )"
    if [[ -n "${host_mount}" ]]; then
      pass "host mount for /public-blog: ${host_mount}"
      REQUIRED_PASSED=$((REQUIRED_PASSED + 1))
    else
      fail "no Docker mount mapped to /public-blog"
      REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
    fi
  else
    fail "container ${CONTAINER_NAME} is not running; cannot verify public blog repo mount"
    REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
  fi
else
  fail "docker not available; cannot verify public blog repo mount"
  REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
fi
echo

echo "==> Worker readiness (health + OpenAPI)"
echo "    max attempts: ${VERIFY_MAX_ATTEMPTS}"
echo "    retry interval: ${VERIFY_RETRY_INTERVAL_SECONDS}s"
echo

OPENAPI_TMP="$(mktemp)"
trap 'rm -f "${OPENAPI_TMP}"' EXIT

if wait_for_worker_http_200 "health" "${WORKER_BASE_URL}/health"; then
  REQUIRED_PASSED=$((REQUIRED_PASSED + 1))
else
  REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
fi
echo

echo "==> Worker OpenAPI Flow A endpoints"
OPENAPI_READY=0
attempt=1
OPENAPI_HTTP_CODE="000"

while [[ "${attempt}" -le "${VERIFY_MAX_ATTEMPTS}" ]]; do
  echo "waiting for worker OpenAPI... attempt ${attempt}/${VERIFY_MAX_ATTEMPTS}"
  OPENAPI_HTTP_CODE="$(curl -sS -o "${OPENAPI_TMP}" -w '%{http_code}' \
    "${WORKER_BASE_URL}/openapi.json" 2>/dev/null || echo "000")"
  if [[ "${OPENAPI_HTTP_CODE}" == "200" ]]; then
    OPENAPI_READY=1
    break
  fi
  if [[ "${attempt}" -lt "${VERIFY_MAX_ATTEMPTS}" ]]; then
    sleep "${VERIFY_RETRY_INTERVAL_SECONDS}"
  fi
  attempt=$((attempt + 1))
done

if [[ "${OPENAPI_READY}" -ne 1 ]]; then
  fail "GET ${WORKER_BASE_URL}/openapi.json did not return HTTP 200 after ${VERIFY_MAX_ATTEMPTS} attempts (last: HTTP ${OPENAPI_HTTP_CODE})"
  REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
else
  pass "GET ${WORKER_BASE_URL}/openapi.json returned HTTP 200"
  REQUIRED_PASSED=$((REQUIRED_PASSED + 1))

  MISSING_PATHS="$(
    python3 - "${OPENAPI_TMP}" "${REQUIRED_OPENAPI_PATHS[@]}" <<'PY'
import json
import sys

doc_path = sys.argv[1]
required = sys.argv[2:]
with open(doc_path, encoding="utf-8") as fh:
    doc = json.load(fh)
paths = set(doc.get("paths", {}))
missing = [path for path in required if path not in paths]
print(",".join(missing))
PY
  )"

  if [[ -n "${MISSING_PATHS}" ]]; then
    fail "OpenAPI missing required Flow A paths: ${MISSING_PATHS//,/, }"
    echo "HINT: deploy may have synced source but the running container still serves an old image." >&2
    echo "HINT: on the Ubuntu server run:" >&2
    echo "  cd ${DEPLOY_DIR}" >&2
    echo "  BUILD_REVISION=\$(git -C <repo-checkout> rev-parse HEAD 2>/dev/null || date +%s) \\" >&2
    echo "    docker compose -f silverman-worker.compose.yaml build --no-cache" >&2
    echo "  docker compose -f silverman-worker.compose.yaml up -d --force-recreate" >&2
    echo "HINT: ensure deploy-worker.sh runs on the server target ${DEPLOY_DIR}, not only from Mac." >&2
    REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
  else
    pass "OpenAPI exposes required Flow A paths (${#REQUIRED_OPENAPI_PATHS[@]}/${#REQUIRED_OPENAPI_PATHS[@]})"
    REQUIRED_PASSED=$((REQUIRED_PASSED + 1))
  fi
fi

echo
if [[ "${REQUIRED_FAILED}" -eq 0 ]]; then
  echo "OVERALL: PASS (${REQUIRED_PASSED} required check(s) passed)"
  exit 0
fi

echo "OVERALL: FAIL (${REQUIRED_FAILED} required check(s) failed)"
exit 1
