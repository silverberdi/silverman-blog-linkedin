#!/usr/bin/env bash
# Controlled US-002 live-site confirmation smoke on the Ubuntu server.
# Publishes with git_publication and live_site_confirmation, verifies remote push,
# container egress to https://silverman.pro, and slug marker in probed page body.
set -euo pipefail

WORKER_DIR="${DEPLOY_DIR:-/home/silverman/silverman-blog-linkedin-worker}"
WORKER_BASE_URL="${WORKER_BASE_URL:-http://localhost:8010}"
BASE="${SILVERMAN_BLOG_LINKEDIN_BASE_PATH:-/home/silverman/compartido_mac/silverman-blog-linkedin}"
PUBLIC_REPO="${SILVERMAN_PUBLIC_BLOG_REPO_PATH:-/home/silverman/silverberdi.github.io}"
SECRETS_DIR="/home/silverman/silverman-blog-linkedin-worker/secrets"
SITE_URL="${SILVERMAN_SITE_URL:-https://silverman.pro}"

SLUG="99-us002-live-site-smoke-validation"
PUBLIC_SLUG="us002-live-site-smoke-validation"
DATE="2026-07-11"
SOURCE_REL="blog-posts/ready/${SLUG}.md"
POST_REL="_posts/${DATE}-${PUBLIC_SLUG}.md"
IMAGE_REL="assets/images/${PUBLIC_SLUG}.png"
PUBLIC_URL="${SITE_URL}/2026/07/11/${PUBLIC_SLUG}/"

GIT_SSH_COMMAND="ssh -i ${SECRETS_DIR}/github-pages-deploy-key -o IdentitiesOnly=yes -o UserKnownHostsFile=${SECRETS_DIR}/known_hosts -o StrictHostKeyChecking=yes"
export GIT_SSH_COMMAND

ENV_FILE="${WORKER_DIR}/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: missing ${ENV_FILE}" >&2
  exit 1
fi

API_KEY="$(
  grep -E '^SILVERMAN_BLOG_LINKEDIN_API_KEY=' "${ENV_FILE}" \
    | head -1 \
    | cut -d= -f2- \
    | tr -d '\r'
)"
if [[ -z "${API_KEY}" ]]; then
  echo "ERROR: SILVERMAN_BLOG_LINKEDIN_API_KEY not set in ${ENV_FILE}" >&2
  exit 1
fi

enable_env_flag() {
  local key="$1"
  if grep -q "^${key}=false" "${ENV_FILE}"; then
    sed -i "s/^${key}=false/${key}=true/" "${ENV_FILE}"
    echo "==> Set ${key}=true"
  elif ! grep -q "^${key}=true" "${ENV_FILE}"; then
    printf '%s=true\n' "${key}" >> "${ENV_FILE}"
    echo "==> Appended ${key}=true"
  fi
}

summarize_response() {
  local label="$1"
  local body="$2"
  python3 - "${label}" <<'PY' "${body}"
import json, sys
label, body = sys.argv[1], sys.argv[2]
r = json.loads(body)
print(f"{label} status={r.get('status')}")
print(f"{label} campaign_id={r.get('campaign_id')}")
bg = r.get("blog_git_publication") or {}
print(f"{label} blog_git_publication.status={bg.get('status')}")
bl = r.get("blog_live_site_publication") or {}
print(f"{label} blog_live_site_publication.status={bl.get('status')}")
print(f"{label} blog_live_site_publication.http_status={bl.get('http_status')}")
print(f"{label} blog_live_site_publication.final_url={bl.get('final_url')}")
print(f"{label} blog_live_site_publication.attempts={bl.get('attempts')}")
errors = r.get("errors") or []
if errors:
    print(f"{label} errors={errors}")
PY
}

echo "==> US-002 live-site confirmation smoke"
echo "    worker: ${WORKER_BASE_URL}"
echo "    source: ${SOURCE_REL}"
echo "    public URL: ${PUBLIC_URL}"

echo "==> Container egress precheck to ${SITE_URL}"
EGRESS_BODY="$(docker compose -f "${WORKER_DIR}/silverman-worker.compose.yaml" exec -T silverman-blog-linkedin-worker \
  python3 -c "import urllib.request, urllib.error
try:
    r = urllib.request.urlopen('${SITE_URL}', timeout=15)
    print(r.status)
except urllib.error.HTTPError as exc:
    print(exc.code)")"
echo "==> Egress precheck HTTP status: ${EGRESS_BODY}"
if [[ -z "${EGRESS_BODY}" ]] || [[ "${EGRESS_BODY}" == "000" ]]; then
  echo "FAIL: container egress precheck did not return an HTTP status" >&2
  exit 1
fi

enable_env_flag "SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED"
enable_env_flag "SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED"

cd "${WORKER_DIR}"
docker compose -f silverman-worker.compose.yaml up -d --force-recreate --no-build

echo "==> Waiting for worker health..."
for _ in $(seq 1 30); do
  if curl -sf "${WORKER_BASE_URL}/health" >/dev/null; then
    break
  fi
  sleep 2
done
if ! curl -sf "${WORKER_BASE_URL}/health" >/dev/null; then
  echo "ERROR: worker health check failed" >&2
  exit 1
fi

if [[ ! -f "${BASE}/blog-posts/processed/04-a-bounded-context-is-not-a-folder.png" ]]; then
  echo "ERROR: template PNG missing for smoke post" >&2
  exit 1
fi

cp "${BASE}/blog-posts/processed/04-a-bounded-context-is-not-a-folder.png" \
  "${BASE}/blog-posts/ready/${SLUG}.png"

cat > "${BASE}/blog-posts/ready/${SLUG}.md" <<EOF
---
title: US-002 Live-Site Confirmation Smoke Validation
subtitle: Controlled worker validation post — safe to remove after US-002 evidence.
audience: Architects, senior developers, tech leads, engineering managers.
type: blog-post
language: en
status: draft
layout: post
date: ${DATE} 00:00:00 -0500
categories:
- architecture
tags:
- validation
description: Controlled US-002 live-site confirmation smoke validation for silverman-blog-linkedin worker.
image: /assets/images/${PUBLIC_SLUG}.png
---

# US-002 Live-Site Confirmation Smoke Validation

Controlled validation artifact for live-site confirmation. Marker slug: ${PUBLIC_SLUG}
EOF

echo "==> Publish (git_publication=true, live_site_confirmation=true)"
RESP="$(
  curl -sS -X POST "${WORKER_BASE_URL}/publish-blog-post" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"source_relative_path\": \"${SOURCE_REL}\", \"git_publication\": true, \"live_site_confirmation\": true}"
)"
summarize_response "publish" "${RESP}"

PROBE_HTTP_STATUS="$(python3 -c 'import json,sys; print((json.loads(sys.argv[1]).get("blog_live_site_publication") or {}).get("http_status",""))' "${RESP}")"
PROBE_FINAL_URL="$(python3 -c 'import json,sys; print((json.loads(sys.argv[1]).get("blog_live_site_publication") or {}).get("final_url",""))' "${RESP}")"
PROBE_ATTEMPTS="$(python3 -c 'import json,sys; print((json.loads(sys.argv[1]).get("blog_live_site_publication") or {}).get("attempts",""))' "${RESP}")"
LIVE_STATUS="$(python3 -c 'import json,sys; print((json.loads(sys.argv[1]).get("blog_live_site_publication") or {}).get("status",""))' "${RESP}")"
OVERALL_STATUS="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("status",""))' "${RESP}")"

echo "==> Direct slug marker check on ${PUBLIC_URL}"
PAGE_BODY="$(docker compose -f "${WORKER_DIR}/silverman-worker.compose.yaml" exec -T silverman-blog-linkedin-worker \
  python3 -c "import urllib.request, urllib.error
url='${PUBLIC_URL}'
req=urllib.request.Request(url, headers={'User-Agent': 'silverman-blog-linkedin-live-site-smoke/1.0'})
try:
    print(urllib.request.urlopen(req, timeout=20).read().decode('utf-8', errors='replace'))
except urllib.error.HTTPError as exc:
    print(exc.read().decode('utf-8', errors='replace'))")"
if grep -q "${PUBLIC_SLUG}" <<< "${PAGE_BODY}"; then
  echo "PASS: public_slug marker found in probed page body"
else
  echo "FAIL: public_slug marker not found in probed page body" >&2
  exit 1
fi

if [[ "${OVERALL_STATUS}" != "completed" ]]; then
  echo "FAIL: overall status expected completed, got ${OVERALL_STATUS}" >&2
  exit 1
fi
if [[ "${LIVE_STATUS}" != "confirmed" && "${LIVE_STATUS}" != "already_confirmed" ]]; then
  echo "FAIL: blog_live_site_publication.status expected confirmed or already_confirmed, got ${LIVE_STATUS}" >&2
  exit 1
fi

echo "==> Evidence summary"
echo "    egress_precheck_http_status=${EGRESS_BODY}"
echo "    probe_http_status=${PROBE_HTTP_STATUS}"
echo "    probe_final_url=${PROBE_FINAL_URL}"
echo "    probe_attempts=${PROBE_ATTEMPTS}"
echo "    slug_marker_check=pass"

echo "OVERALL: PASS"
