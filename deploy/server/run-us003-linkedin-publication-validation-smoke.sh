#!/usr/bin/env bash
# Controlled US-003 LinkedIn publication validation on the Ubuntu server.
# Performs OAuth preflight, real queue, real publish-due (publish_now), idempotency rerun,
# and mandatory safeguard restoration. Never prints API keys or tokens.
#
# WARNING: When publication is enabled, this script publishes one real LinkedIn post.
# The post remains visible on the operator profile until manually removed in LinkedIn.
set -euo pipefail

WORKER_DIR="${DEPLOY_DIR:-/home/silverman/silverman-blog-linkedin-worker}"
WORKER_BASE_URL="${WORKER_BASE_URL:-http://localhost:8010}"
ENV_FILE="${ENV_FILE:-${WORKER_DIR}/.env}"
COMPOSE_FILE="${COMPOSE_FILE:-${WORKER_DIR}/silverman-worker.compose.yaml}"

CAMPAIGN_ID=""
VARIANT=""
ALLOW_NON_PENDING=0
SKIP_ENABLEMENT=0

REQUIRED_FAILED=0
SKIP_RESTORE=0
RESPONSE_TMP=""
OAUTH_STATUS_TMP=""
HEALTH_TMP=""

usage() {
  cat <<'EOF'
Usage: run-us003-linkedin-publication-validation-smoke.sh --campaign-id ID --variant ID [options]

Controlled first-real-publish validation for backlog US-003 / US-004 / US-005 (BL-002).
Requires completed OAuth bootstrap (see docs/deployment/linkedin-publication-prerequisites.md).

Options:
  --campaign-id ID         Flow A campaign id (required; no auto-detect)
  --variant ID             LinkedIn variant id (required)
  --allow-non-pending      Allow variant publish_state other than pending (operator override)
  --skip-enablement        Do not toggle SILVERMAN_LINKEDIN_PUBLICATION_ENABLED (assume already true)
  --worker-base-url URL    Worker base URL (default http://localhost:8010)
  --env-file PATH          Server-local .env (default ${WORKER_DIR}/.env)
  -h, --help               Show this help

Does not print API keys, OAuth tokens, client secrets, or authorization codes.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --campaign-id)
      CAMPAIGN_ID="${2:?missing value for --campaign-id}"
      shift 2
      ;;
    --variant)
      VARIANT="${2:?missing value for --variant}"
      shift 2
      ;;
    --allow-non-pending)
      ALLOW_NON_PENDING=1
      shift
      ;;
    --skip-enablement)
      SKIP_ENABLEMENT=1
      shift
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

if [[ -z "${CAMPAIGN_ID}" || -z "${VARIANT}" ]]; then
  echo "ERROR: --campaign-id and --variant are required" >&2
  usage >&2
  exit 1
fi

fail() {
  echo "FAIL: $*" >&2
  REQUIRED_FAILED=$((REQUIRED_FAILED + 1))
}

pass() {
  echo "PASS: $*"
}

info() {
  echo "==> $*"
}

section() {
  echo
  echo "=== $* ==="
}

cleanup_temp_files() {
  rm -f "${RESPONSE_TMP}" "${OAUTH_STATUS_TMP}" "${HEALTH_TMP}"
}

restore_publication_flag() {
  if [[ "${SKIP_ENABLEMENT}" -eq 1 || "${SKIP_RESTORE}" -eq 1 ]]; then
    return 0
  fi
  if [[ ! -f "${ENV_FILE}" ]]; then
    echo "WARN: cannot restore publication flag; missing ${ENV_FILE}" >&2
    return 0
  fi
  info "Restoring SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false"
  if grep -q '^SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=' "${ENV_FILE}"; then
    sed -i 's/^SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=.*/SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false/' "${ENV_FILE}"
  else
    printf 'SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false\n' >> "${ENV_FILE}"
  fi
  if [[ -f "${COMPOSE_FILE}" ]]; then
    (cd "${WORKER_DIR}" && docker compose -f "${COMPOSE_FILE##*/}" up -d --force-recreate --no-build) || true
  fi
}

on_exit() {
  local exit_code=$?
  restore_publication_flag
  cleanup_temp_files
  if [[ "${exit_code}" -ne 0 && "${REQUIRED_FAILED}" -eq 0 ]]; then
    echo "OVERALL: FAIL" >&2
  fi
  return "${exit_code}"
}

trap on_exit EXIT

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

print_variant_snapshot() {
  local label="$1"
  local root="$2"
  local campaign_id="$3"
  local variant="$4"
  python3 - "${label}" "${root}" "${campaign_id}" "${variant}" <<'PY'
import json
import sys
from pathlib import Path

label, root, campaign_id, variant = sys.argv[1:5]
path = Path(root) / "metadata" / "campaigns" / f"{campaign_id}.json"
print(f"{label}:")
if not path.is_file():
    print("  campaign metadata: (not found)")
    sys.exit(0)
with open(path, encoding="utf-8") as fh:
    data = json.load(fh)
print(f"  campaign state: {data.get('state') or '(unset)'}")
print(f"  campaign flow: {data.get('flow') or '(unset)'}")
for entry in data.get("variants") or []:
    if entry.get("variant") == variant:
        print(f"  variant publish_state: {entry.get('publish_state')}")
        if entry.get("publish_after_utc"):
            print(f"  publish_after_utc: {entry.get('publish_after_utc')}")
        if entry.get("published_at"):
            print(f"  published_at: {entry.get('published_at')}")
        if entry.get("linkedin_post_urn"):
            print(f"  linkedin_post_urn: {entry.get('linkedin_post_urn')}")
        sys.exit(0)
print(f"  variant publish_state: (variant {variant!r} not found)")
PY
}

validate_campaign_preflight() {
  local root="$1"
  python3 - "${root}" "${CAMPAIGN_ID}" "${VARIANT}" "${ALLOW_NON_PENDING}" <<'PY'
import json
import sys
from pathlib import Path

root, campaign_id, variant, allow_non_pending = sys.argv[1:5]
allow_non_pending = allow_non_pending == "1"
path = Path(root) / "metadata" / "campaigns" / f"{campaign_id}.json"
if not path.is_file():
    print(f"FAIL: campaign metadata not found: {path}")
    sys.exit(1)
with open(path, encoding="utf-8") as fh:
    data = json.load(fh)
flow = data.get("flow")
if flow == "flow_b":
    print("FAIL: Flow B campaigns are not eligible for US-003 validation")
    sys.exit(1)
state = data.get("state") or ""
allowed_states = {
    "distribution_scheduled",
    "distribution_complete",
    "flow_a_complete",
}
if state not in allowed_states:
    print(
        "FAIL: campaign state must be distribution_scheduled or later; "
        f"got {state!r}"
    )
    sys.exit(1)
entry = None
for item in data.get("variants") or []:
    if item.get("variant") == variant:
        entry = item
        break
if entry is None:
    print(f"FAIL: variant {variant!r} not found in campaign metadata")
    sys.exit(1)
publish_state = entry.get("publish_state")
if publish_state != "pending" and not allow_non_pending:
    print(
        "FAIL: variant publish_state must be pending for first real publish; "
        f"got {publish_state!r} (use --allow-non-pending only with operator approval)"
    )
    sys.exit(1)
artifact_rel = (
    Path("linkedin-posts/generated") / campaign_id / f"{variant}.md"
)
artifact_path = Path(root) / artifact_rel
if not artifact_path.is_file():
    print(f"FAIL: generated artifact missing: {artifact_rel}")
    sys.exit(1)
print("PASS: campaign preflight (Flow A, distribution_scheduled+, pending variant, artifact present)")
PY
}

wait_for_health() {
  info "Waiting for worker health..."
  for _ in $(seq 1 30); do
    if curl -sf "${WORKER_BASE_URL}/health" >/dev/null; then
      return 0
    fi
    sleep 2
  done
  fail "worker health check failed"
  return 1
}

enable_publication_flag() {
  if [[ "${SKIP_ENABLEMENT}" -eq 1 ]]; then
    info "Skipping enablement toggle (--skip-enablement)"
    return 0
  fi
  if [[ ! -f "${ENV_FILE}" ]]; then
    fail "env file not found: ${ENV_FILE}"
    return 1
  fi
  local enabled
  enabled="$(load_env_var SILVERMAN_LINKEDIN_PUBLICATION_ENABLED 2>/dev/null || echo "")"
  if [[ "${enabled}" == "true" || "${enabled}" == "1" || "${enabled}" == "yes" ]]; then
    info "SILVERMAN_LINKEDIN_PUBLICATION_ENABLED already true"
    return 0
  fi
  if grep -q '^SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=' "${ENV_FILE}"; then
    sed -i 's/^SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=.*/SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true/' "${ENV_FILE}"
  else
    printf 'SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true\n' >> "${ENV_FILE}"
  fi
  info "Set SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true for validation window"
  if [[ ! -f "${COMPOSE_FILE}" ]]; then
    fail "compose file not found: ${COMPOSE_FILE}"
    return 1
  fi
  (cd "${WORKER_DIR}" && docker compose -f "${COMPOSE_FILE##*/}" up -d --force-recreate --no-build)
  wait_for_health
}

call_get() {
  local path="$1"
  local out_var="$2"
  local api_key http_code

  api_key="$(load_env_var SILVERMAN_BLOG_LINKEDIN_API_KEY || true)"
  if [[ -z "${api_key}" ]]; then
    fail "SILVERMAN_BLOG_LINKEDIN_API_KEY not set in ${ENV_FILE}"
    return 1
  fi

  RESPONSE_TMP="$(mktemp)"
  http_code="$(curl -sS -o "${RESPONSE_TMP}" -w '%{http_code}' \
    -H "Authorization: Bearer ${api_key}" \
    "${WORKER_BASE_URL}${path}" 2>/dev/null || echo "000")"

  if [[ "${http_code}" != "200" ]]; then
    fail "${path}: HTTP ${http_code}"
    python3 -m json.tool "${RESPONSE_TMP}" 2>/dev/null || cat "${RESPONSE_TMP}"
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

  printf -v "${out_var}" '%s' "${serialized}"
  python3 -m json.tool <<< "${serialized}"
  return 0
}

call_post() {
  local path="$1"
  local body="$2"
  local out_var="$3"
  local api_key http_code

  api_key="$(load_env_var SILVERMAN_BLOG_LINKEDIN_API_KEY || true)"
  if [[ -z "${api_key}" ]]; then
    fail "SILVERMAN_BLOG_LINKEDIN_API_KEY not set in ${ENV_FILE}"
    return 1
  fi

  RESPONSE_TMP="$(mktemp)"
  http_code="$(curl -sS -o "${RESPONSE_TMP}" -w '%{http_code}' \
    -X POST "${WORKER_BASE_URL}${path}" \
    -H "Authorization: Bearer ${api_key}" \
    -H "Content-Type: application/json" \
    -d "${body}" 2>/dev/null || echo "000")"

  if [[ "${http_code}" != "200" ]]; then
    fail "${path}: HTTP ${http_code}"
    python3 -m json.tool "${RESPONSE_TMP}" 2>/dev/null || cat "${RESPONSE_TMP}"
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

  printf -v "${out_var}" '%s' "${serialized}"
  python3 -m json.tool <<< "${serialized}"
  return 0
}

check_oauth_preflight() {
  local body
  section "OAuth preflight (GET /linkedin/oauth/status)"
  if ! call_get "/linkedin/oauth/status" body; then
    echo "Remediation: complete OAuth bootstrap in docs/deployment/linkedin-publication-prerequisites.md" >&2
    return 1
  fi

  python3 - "${body}" <<'PY'
import json
import sys

body = json.loads(sys.argv[1])
errors = []

def require_true(field, label):
    if not body.get(field):
        errors.append(label)

require_true("token_store_configured", "token_store_configured")
require_true("token_present", "token_present")
if not body.get("member_urn"):
    errors.append("member_urn")
if not body.get("access_token_expires_at"):
    errors.append("access_token_expires_at metadata")
if not body.get("publication_enabled"):
    errors.append("publication_enabled (enable validation window first)")

forbidden_keys = ("access_token", "refresh_token", "client_secret", "authorization_code")
serialized = json.dumps(body)
for key in forbidden_keys:
    if key in body and body[key]:
        errors.append(f"unexpected secret field in response: {key}")

if errors:
    print("FAIL: OAuth preflight checks failed:")
    for item in errors:
        print(f"  - {item}")
    sys.exit(1)

print("PASS: OAuth preflight")
print(f"  member_urn: {body.get('member_urn')}")
print(f"  access_token_expires_at: {body.get('access_token_expires_at')}")
print(f"  refresh_token_present: {body.get('refresh_token_present')}")
print(f"  publication_enabled: {body.get('publication_enabled')}")
if body.get("access_token"):
    raise SystemExit("FAIL: access_token leaked in diagnostic response")
PY
}

assert_queue_response() {
  local body="$1"
  python3 - "${body}" "${VARIANT}" <<'PY'
import json
import sys

body = json.loads(sys.argv[1])
variant = sys.argv[2]
if body.get("dry_run") is not False:
    raise SystemExit("FAIL: queue response dry_run expected false")
if body.get("publish_state") != "queued":
    raise SystemExit(f"FAIL: queue publish_state expected queued, got {body.get('publish_state')!r}")
if body.get("variant") != variant:
    raise SystemExit(f"FAIL: queue variant mismatch {body.get('variant')!r}")
print("PASS: queue step (pending → queued)")
PY
}

assert_publish_response() {
  local body="$1"
  local expect_already_published="${2:-0}"
  python3 - "${body}" "${VARIANT}" "${expect_already_published}" <<'PY'
import json
import sys

body = json.loads(sys.argv[1])
variant = sys.argv[2]
expect_already = sys.argv[3] == "1"
if body.get("dry_run") is not False:
    raise SystemExit("FAIL: publish-due response dry_run expected false")
results = body.get("results") or []
match = next((item for item in results if item.get("variant") == variant), None)
if match is None:
    raise SystemExit(f"FAIL: publish-due missing result for variant {variant!r}")
state = match.get("publish_state")
if state != "published":
    raise SystemExit(f"FAIL: publish_state expected published, got {state!r}")
urn = match.get("linkedin_post_urn")
if not urn:
    raise SystemExit("FAIL: linkedin_post_urn missing after publish")
warnings = match.get("warnings") or []
if expect_already:
    if "linkedin_publish_already_published" not in warnings:
        raise SystemExit(
            "FAIL: idempotent rerun expected linkedin_publish_already_published warning"
        )
    print(f"PASS: idempotent publish-due (linkedin_post_urn unchanged: {urn})")
else:
    print(f"PASS: publish-due step (linkedin_post_urn={urn})")
PY
}

main() {
  section "US-003 LinkedIn publication validation smoke"
  echo "worker url:  ${WORKER_BASE_URL}"
  echo "campaign id: ${CAMPAIGN_ID}"
  echo "variant:     ${VARIANT}"
  echo "note: real LinkedIn publication when enabled — irreversible external artifact"

  if [[ ! -f "${ENV_FILE}" ]]; then
    fail "missing ${ENV_FILE}"
    echo "OVERALL: FAIL"
    exit 1
  fi

  local editorial_root=""
  if ! editorial_root="$(resolve_editorial_root)"; then
    fail "could not resolve editorial root with metadata/campaigns"
    echo "OVERALL: FAIL"
    exit 1
  fi
  pass "editorial root ${editorial_root}"

  section "Campaign preflight"
  if ! validate_campaign_preflight "${editorial_root}"; then
    echo "OVERALL: FAIL"
    exit 1
  fi

  enable_publication_flag

  section "Worker health"
  HEALTH_TMP="$(mktemp)"
  local health_code
  health_code="$(curl -sS -o "${HEALTH_TMP}" -w '%{http_code}' "${WORKER_BASE_URL}/health" 2>/dev/null || echo "000")"
  if [[ "${health_code}" != "200" ]]; then
    fail "GET /health HTTP ${health_code}"
    echo "OVERALL: FAIL"
    exit 1
  fi
  pass "GET /health HTTP 200"
  python3 - "${HEALTH_TMP}" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as fh:
    data = json.load(fh)
print(f"  service version: {data.get('version')}")
print(f"  status: {data.get('status')}")
PY

  if ! check_oauth_preflight; then
    echo "OVERALL: FAIL"
    exit 1
  fi

  section "Variant state before queue"
  print_variant_snapshot "before queue" "${editorial_root}" "${CAMPAIGN_ID}" "${VARIANT}"

  local queue_body=""
  section "Queue LinkedIn publication (dry_run=false)"
  if ! call_post "/queue-linkedin-publication" \
    "{\"campaign_id\":\"${CAMPAIGN_ID}\",\"variant\":\"${VARIANT}\",\"dry_run\":false}" \
    queue_body; then
    echo "OVERALL: FAIL"
    exit 1
  fi
  assert_queue_response "${queue_body}"

  section "Variant state after queue"
  print_variant_snapshot "after queue" "${editorial_root}" "${CAMPAIGN_ID}" "${VARIANT}"

  local publish_body=""
  section "Publish due variants (dry_run=false, publish_now=true)"
  if ! call_post "/publish-linkedin-due-variants" \
    "{\"campaign_id\":\"${CAMPAIGN_ID}\",\"variant\":\"${VARIANT}\",\"dry_run\":false,\"publish_now\":true}" \
    publish_body; then
    echo "OVERALL: FAIL"
    exit 1
  fi
  assert_publish_response "${publish_body}" 0

  section "Variant state after publish"
  print_variant_snapshot "after publish" "${editorial_root}" "${CAMPAIGN_ID}" "${VARIANT}"

  section "LinkedIn visibility checklist (operator — record in Phase 3 report)"
  echo "  1. Open LinkedIn profile feed/activity and confirm the post is visible"
  echo "  2. Record linkedin_post_urn and published_at from metadata above"
  echo "  3. Optional: capture public post URL if obtainable from URN"
  echo "  4. Do not store session cookies or credentials in the repository"

  local idempotent_body=""
  section "Idempotent publish-due rerun"
  if ! call_post "/publish-linkedin-due-variants" \
    "{\"campaign_id\":\"${CAMPAIGN_ID}\",\"variant\":\"${VARIANT}\",\"dry_run\":false,\"publish_now\":true}" \
    idempotent_body; then
    echo "OVERALL: FAIL"
    exit 1
  fi
  assert_publish_response "${idempotent_body}" 1

  section "Safeguard restoration verification"
  restore_publication_flag
  SKIP_RESTORE=1
  wait_for_health || true
  local post_restore_body=""
  if call_get "/linkedin/oauth/status" post_restore_body; then
    python3 - "${post_restore_body}" <<'PY'
import json
import sys

body = json.loads(sys.argv[1])
if body.get("publication_enabled"):
    print("FAIL: publication_enabled still true after restoration")
    sys.exit(1)
print("PASS: publication_enabled=false after safeguard restoration")
PY
  else
    fail "could not verify publication disabled after restoration"
  fi

  section "Overall"
  if [[ "${REQUIRED_FAILED}" -eq 0 ]]; then
    echo "OVERALL: PASS"
    exit 0
  fi
  echo "OVERALL: FAIL"
  exit 1
}

main "$@"
