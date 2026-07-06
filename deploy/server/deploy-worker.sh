#!/usr/bin/env bash
# Deploy silverman-blog-linkedin-worker to an isolated directory on the Ubuntu server.
# Does not modify local-ai-stack or any shared-stack compose project.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TARGET_DIR="${DEPLOY_DIR:-/home/silverman/silverman-blog-linkedin-worker}"

echo "==> silverman-blog-linkedin worker deploy"
echo "    repository: ${REPO_ROOT}"
echo "    target:     ${TARGET_DIR}"

mkdir -p "${TARGET_DIR}"

RSYNC_EXCLUDES=(
  --exclude '.git/'
  --exclude '.venv/'
  --exclude '__pycache__/'
  --exclude '.pytest_cache/'
  --exclude 'data/'
  --exclude '.env'
  --exclude '*.pyc'
  --exclude '.DS_Store'
)

echo "==> Syncing build and deployment artifacts..."

if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete "${RSYNC_EXCLUDES[@]}" \
    "${REPO_ROOT}/Dockerfile" \
    "${REPO_ROOT}/pyproject.toml" \
    "${REPO_ROOT}/README.md" \
    "${REPO_ROOT}/src" \
    "${TARGET_DIR}/"

  rsync -a \
    "${SCRIPT_DIR}/silverman-worker.compose.yaml" \
    "${SCRIPT_DIR}/silverman-worker.env.example" \
    "${SCRIPT_DIR}/deploy-worker.sh" \
    "${SCRIPT_DIR}/smoke-worker.sh" \
    "${TARGET_DIR}/"
else
  echo "    rsync not found; using cp (no delete of stale files)"
  cp "${REPO_ROOT}/Dockerfile" "${REPO_ROOT}/pyproject.toml" "${REPO_ROOT}/README.md" "${TARGET_DIR}/"
  rm -rf "${TARGET_DIR}/src"
  cp -R "${REPO_ROOT}/src" "${TARGET_DIR}/src"
  cp "${SCRIPT_DIR}/silverman-worker.compose.yaml" \
    "${SCRIPT_DIR}/silverman-worker.env.example" \
    "${SCRIPT_DIR}/deploy-worker.sh" \
    "${SCRIPT_DIR}/smoke-worker.sh" \
    "${TARGET_DIR}/"
fi

chmod +x "${TARGET_DIR}/deploy-worker.sh" "${TARGET_DIR}/smoke-worker.sh"

if [[ ! -f "${TARGET_DIR}/silverman-worker.env.example" ]]; then
  echo "ERROR: silverman-worker.env.example missing in ${TARGET_DIR}" >&2
  exit 1
fi

if [[ ! -f "${TARGET_DIR}/.env" ]]; then
  cat >&2 <<EOF

ERROR: Server-local .env is missing in ${TARGET_DIR}

Create it manually from the example (do not commit real secrets to git):

  cd ${TARGET_DIR}
  cp silverman-worker.env.example .env
  # Edit .env and set real values for:
  #   SILVERMAN_BLOG_LINKEDIN_API_KEY
  #   DEEPSEEK_API_KEY

Then re-run this script.

EOF
  exit 1
fi

echo "==> Starting worker via isolated compose (port 8010)..."
cd "${TARGET_DIR}"
docker compose -f silverman-worker.compose.yaml up -d --build

echo "==> Deploy complete."
echo "    Worker URL: http://localhost:8010"
echo "    Smoke test: ${TARGET_DIR}/smoke-worker.sh"
