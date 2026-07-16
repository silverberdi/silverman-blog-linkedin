#!/usr/bin/env bash
# Queue and publish pending Flow A LinkedIn variants through the worker.
# Uses POST /publish-linkedin-due-variants with auto_queue_pending=true.
# Defaults to dry-run. Real publish requires --real and publication enabled.
set -euo pipefail

ENV_FILE="${ENV_FILE:-/home/silverman/silverman-blog-linkedin-worker/.env}"
WORKER_BASE_URL="${WORKER_BASE_URL:-http://localhost:8010}"
CAMPAIGN_ID="${CAMPAIGN_ID:-}"
VARIANT="${VARIANT:-}"
REAL_PUBLISH=0
PUBLISH_NOW=1
RESPECT_SCHEDULE=0

usage() {
  cat <<'EOF'
Usage: run-publish-pending-linkedin-variants.sh [options]

Queues pending Flow A variants and publishes eligible queued variants in one worker call:
  POST /publish-linkedin-due-variants
    auto_queue_pending=true
    publish_now=true|false

Defaults to dry-run (safe). Real publish requires --real and
SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true in the worker .env.

Options:
  --real                 Real publish (dry_run=false)
  --respect-schedule     Only queue/publish variants whose scheduled_at_utc is due
  --campaign-id ID       Limit to one campaign (optional)
  --variant ID           Limit to one variant (optional; requires --campaign-id)
  --worker-base-url URL  Worker base URL (default http://localhost:8010)
  --env-file PATH        Server-local .env with SILVERMAN_BLOG_LINKEDIN_API_KEY
  -h, --help             Show this help

Examples:
  # Preview all pending variants across campaigns
  ./run-publish-pending-linkedin-variants.sh

  # Send all pending now (construction / operator override)
  ./run-publish-pending-linkedin-variants.sh --real

  # Send pending for one campaign only
  ./run-publish-pending-linkedin-variants.sh --real --campaign-id flow-a-2026-07-06-example
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --real)
      REAL_PUBLISH=1
      shift
      ;;
    --respect-schedule)
      RESPECT_SCHEDULE=1
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

if [[ -n "${VARIANT}" && -z "${CAMPAIGN_ID}" ]]; then
  echo "ERROR: --variant requires --campaign-id" >&2
  exit 1
fi

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

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: env file not found: ${ENV_FILE}" >&2
  exit 1
fi

api_key="$(load_env_var SILVERMAN_BLOG_LINKEDIN_API_KEY || true)"
if [[ -z "${api_key}" ]]; then
  echo "ERROR: SILVERMAN_BLOG_LINKEDIN_API_KEY not set in ${ENV_FILE}" >&2
  exit 1
fi

if [[ "${REAL_PUBLISH}" -eq 1 ]]; then
  enabled="$(load_env_var SILVERMAN_LINKEDIN_PUBLICATION_ENABLED 2>/dev/null || echo "")"
  if [[ "${enabled}" != "true" ]]; then
    echo "ERROR: --real requires SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true in ${ENV_FILE}" >&2
    exit 1
  fi
fi

if [[ "${RESPECT_SCHEDULE}" -eq 1 ]]; then
  PUBLISH_NOW=0
fi

dry_run="true"
if [[ "${REAL_PUBLISH}" -eq 1 ]]; then
  dry_run="false"
fi

publish_now="false"
if [[ "${PUBLISH_NOW}" -eq 1 ]]; then
  publish_now="true"
fi

body="$(python3 - <<PY
import json

dry_run = ${dry_run@Q}
publish_now = ${publish_now@Q}
payload = {
    "dry_run": dry_run == "true",
    "publish_now": publish_now == "true",
    "auto_queue_pending": True,
}
campaign_id = ${CAMPAIGN_ID@Q}
variant = ${VARIANT@Q}
if campaign_id:
    payload["campaign_id"] = campaign_id
if variant:
    payload["variant"] = variant
print(json.dumps(payload))
PY
)"

echo "==> POST /publish-linkedin-due-variants"
echo "worker url: ${WORKER_BASE_URL}"
echo "dry_run: ${dry_run}"
echo "publish_now: ${publish_now}"
echo "auto_queue_pending: true"
if [[ -n "${CAMPAIGN_ID}" ]]; then
  echo "campaign_id: ${CAMPAIGN_ID}"
fi
if [[ -n "${VARIANT}" ]]; then
  echo "variant: ${VARIANT}"
fi

response_tmp="$(mktemp)"
trap 'rm -f "${response_tmp}"' EXIT

http_code="$(curl -sS -o "${response_tmp}" -w '%{http_code}' \
  -X POST "${WORKER_BASE_URL}/publish-linkedin-due-variants" \
  -H "Authorization: Bearer ${api_key}" \
  -H "Content-Type: application/json" \
  -d "${body}" || echo "000")"

if [[ "${http_code}" != "200" ]]; then
  echo "FAIL: HTTP ${http_code}" >&2
  python3 -m json.tool "${response_tmp}" 2>/dev/null || cat "${response_tmp}"
  exit 1
fi

python3 -m json.tool "${response_tmp}"
status="$(python3 - "${response_tmp}" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as fh:
    payload = json.load(fh)

for phase, key in (("auto-queue", "auto_queue_results"), ("publish", "results")):
    for item in payload.get(key) or []:
        outcome = item.get("skip_reason") or (
            ",".join(item.get("errors") or [])
            or item.get("publish_state")
            or item.get("status")
            or "unknown"
        )
        print(
            f"{phase}: campaign={item.get('campaign_id', 'unknown')} "
            f"variant={item.get('variant', 'unknown')} outcome={outcome}",
            file=sys.stderr,
        )

print(payload.get("status", "unknown"))
PY
)"

if [[ "${status}" == "completed" ]]; then
  echo "OVERALL: PASS"
  exit 0
fi

echo "OVERALL: FAIL (status=${status})" >&2
exit 1
