#!/usr/bin/env bash
# Controlled US-001 Git publication smoke on the Ubuntu server.
# Creates an isolated ready post, publishes with git_publication=true, verifies remote push
# and idempotent rerun. Does not print API keys or credential material.
set -euo pipefail

WORKER_DIR="${DEPLOY_DIR:-/home/silverman/silverman-blog-linkedin-worker}"
WORKER_BASE_URL="${WORKER_BASE_URL:-http://localhost:8010}"
BASE="${SILVERMAN_BLOG_LINKEDIN_BASE_PATH:-/home/silverman/compartido_mac/silverman-blog-linkedin}"
PUBLIC_REPO="${SILVERMAN_PUBLIC_BLOG_REPO_PATH:-/home/silverman/silverberdi.github.io}"
SECRETS_DIR="/home/silverman/silverman-blog-linkedin-worker/secrets"

SLUG="99-us001-git-smoke-validation"
PUBLIC_SLUG="us001-git-smoke-validation"
DATE="2026-07-11"
SOURCE_REL="blog-posts/ready/${SLUG}.md"
POST_REL="_posts/${DATE}-${PUBLIC_SLUG}.md"
IMAGE_REL="assets/images/${PUBLIC_SLUG}.png"

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

remote_head() {
  git -C "${PUBLIC_REPO}" ls-remote origin refs/heads/main | awk '{print $1}'
}

summarize_response() {
  local label="$1"
  local body="$2"
  python3 - "${label}" <<'PY' "${body}"
import json, sys
label, body = sys.argv[1], sys.argv[2]
try:
    r = json.loads(body)
except json.JSONDecodeError as exc:
    print(f"{label}: invalid JSON ({exc})")
    sys.exit(1)
print(f"{label} status={r.get('status')}")
print(f"{label} campaign_id={r.get('campaign_id')}")
bp = r.get("blog_publish") or {}
print(f"{label} blog_publish.status={bp.get('status')}")
bg = r.get("blog_git_publication") or {}
print(f"{label} blog_git_publication.status={bg.get('status')}")
print(f"{label} blog_git_publication.commit_sha={bg.get('commit_sha')}")
print(f"{label} blog_git_publication.remote={bg.get('remote')}")
print(f"{label} blog_git_publication.branch={bg.get('branch')}")
errors = r.get("errors") or []
if errors:
    print(f"{label} errors={errors}")
PY
}

echo "==> US-001 Git publication smoke"
echo "    worker: ${WORKER_BASE_URL}"
echo "    source: ${SOURCE_REL}"

REMOTE_BEFORE="$(remote_head)"
echo "==> Remote HEAD before: ${REMOTE_BEFORE}"

if grep -q '^SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=false' "${ENV_FILE}"; then
  sed -i 's/^SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=false/SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true/' "${ENV_FILE}"
  echo "==> Set SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true"
elif ! grep -q '^SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true' "${ENV_FILE}"; then
  printf 'SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true\n' >> "${ENV_FILE}"
  echo "==> Appended SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true"
fi

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
title: US-001 Git Publication Smoke Validation
subtitle: Controlled worker validation post — safe to remove after US-001 evidence.
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
description: Controlled US-001 Git publication smoke validation for silverman-blog-linkedin worker.
image: /assets/images/${PUBLIC_SLUG}.png
---

# US-001 Git Publication Smoke Validation

Controlled validation artifact for guarded Git publication. Not editorial content.
EOF

echo "==> First publish (git_publication=true)"
RESP1="$(
  curl -sS -X POST "${WORKER_BASE_URL}/publish-blog-post" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"source_relative_path\": \"${SOURCE_REL}\", \"git_publication\": true}"
)"
summarize_response "first" "${RESP1}"

echo "==> Second publish (idempotency, git_publication=true)"
RESP2="$(
  curl -sS -X POST "${WORKER_BASE_URL}/publish-blog-post" \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"source_relative_path\": \"${SOURCE_REL}\", \"git_publication\": true}"
)"
summarize_response "second" "${RESP2}"

REMOTE_AFTER="$(remote_head)"
echo "==> Remote HEAD after: ${REMOTE_AFTER}"
if [[ "${REMOTE_BEFORE}" != "${REMOTE_AFTER}" ]]; then
  echo "PASS: remote main advanced"
else
  echo "WARN: remote main unchanged (check whether commit was already on remote)"
fi

if [[ -f "${PUBLIC_REPO}/${POST_REL}" ]]; then
  echo "PASS: public checkout contains ${POST_REL}"
else
  echo "FAIL: missing ${POST_REL} in public checkout" >&2
  exit 1
fi
if [[ -f "${PUBLIC_REPO}/${IMAGE_REL}" ]]; then
  echo "PASS: public checkout contains ${IMAGE_REL}"
else
  echo "FAIL: missing ${IMAGE_REL} in public checkout" >&2
  exit 1
fi

git -C "${PUBLIC_REPO}" log -1 --oneline -- "${POST_REL}" "${IMAGE_REL}" || true

FIRST_STATUS="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("status",""))' "${RESP1}")"
FIRST_GIT_STATUS="$(python3 -c 'import json,sys; print((json.loads(sys.argv[1]).get("blog_git_publication") or {}).get("status",""))' "${RESP1}")"
SECOND_GIT_STATUS="$(python3 -c 'import json,sys; print((json.loads(sys.argv[1]).get("blog_git_publication") or {}).get("status",""))' "${RESP2}")"

if [[ "${FIRST_STATUS}" != "completed" ]]; then
  echo "FAIL: first response status expected completed, got ${FIRST_STATUS}" >&2
  exit 1
fi
if [[ "${FIRST_GIT_STATUS}" != "pushed" ]]; then
  echo "FAIL: first blog_git_publication.status expected pushed, got ${FIRST_GIT_STATUS}" >&2
  exit 1
fi
if [[ "${SECOND_GIT_STATUS}" != "already_published" ]]; then
  echo "FAIL: second blog_git_publication.status expected already_published, got ${SECOND_GIT_STATUS}" >&2
  exit 1
fi

echo "OVERALL: PASS"
