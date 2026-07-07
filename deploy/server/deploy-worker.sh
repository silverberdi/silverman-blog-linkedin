#!/usr/bin/env bash
# Deploy silverman-blog-linkedin-worker to an isolated directory on the Ubuntu server.
# Does not modify local-ai-stack or any shared-stack compose project.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${DEPLOY_DIR:-/home/silverman/silverman-blog-linkedin-worker}"
WORKER_BASE_URL="${WORKER_BASE_URL:-http://localhost:8010}"
FORCE_NO_CACHE="${DEPLOY_FORCE_REBUILD:-0}"

FLOW_A_SOURCE_FILES=(
  "src/silverman_blog_linkedin/main.py"
  "src/silverman_blog_linkedin/blog_publish_flow.py"
  "src/silverman_blog_linkedin/linkedin_package_flow.py"
  "src/silverman_blog_linkedin/linkedin_distribution_schedule.py"
)

TARGET_LAYOUT_MARKERS=(
  "Dockerfile"
  "pyproject.toml"
  "README.md"
  "src"
)

has_target_layout_markers() {
  local base="$1"
  local name
  for name in "${TARGET_LAYOUT_MARKERS[@]}"; do
    if [[ "${name}" == "src" ]]; then
      [[ -d "${base}/${name}" ]] || return 1
    else
      [[ -f "${base}/${name}" ]] || return 1
    fi
  done
  return 0
}

if has_target_layout_markers "${SCRIPT_DIR}"; then
  DEPLOY_LAYOUT="target"
  SOURCE_ROOT="${SCRIPT_DIR}"
  TARGET_DIR="${SCRIPT_DIR}"
  DEPLOY_SERVER_DIR="${SCRIPT_DIR}"
else
  DEPLOY_LAYOUT="repo"
  SOURCE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
  DEPLOY_SERVER_DIR="${SCRIPT_DIR}"
fi

echo "==> silverman-blog-linkedin worker deploy"
echo "    layout:     ${DEPLOY_LAYOUT}"
echo "    source:     ${SOURCE_ROOT}"
echo "    target:     ${TARGET_DIR}"
echo "    worker URL: ${WORKER_BASE_URL}"

if [[ "${TARGET_DIR}" == /home/silverman/* ]] && [[ "$(uname -s)" != "Linux" ]]; then
  cat >&2 <<EOF

WARN: deploy target is a Ubuntu server path but this host is not Linux.
      Files will sync locally to ${TARGET_DIR} on this machine and will NOT
      update the worker on 192.168.0.194 unless you run this script on the
      server (SSH) or set DEPLOY_DIR to the actual server deployment path.

EOF
fi

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

if [[ "${DEPLOY_LAYOUT}" == "target" ]]; then
  echo "==> Target layout: validating local build artifacts (skip rsync)..."
  for name in Dockerfile pyproject.toml README.md; do
    if [[ ! -f "${TARGET_DIR}/${name}" ]]; then
      echo "ERROR: missing ${name} in ${TARGET_DIR}" >&2
      exit 1
    fi
  done
  if [[ ! -d "${TARGET_DIR}/src" ]]; then
    echo "ERROR: missing src/ in ${TARGET_DIR}" >&2
    exit 1
  fi
else
  echo "==> Repo layout: syncing build and deployment artifacts..."

  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "${RSYNC_EXCLUDES[@]}" \
      "${SOURCE_ROOT}/Dockerfile" \
      "${SOURCE_ROOT}/pyproject.toml" \
      "${SOURCE_ROOT}/README.md" \
      "${SOURCE_ROOT}/src" \
      "${TARGET_DIR}/"

    rsync -a \
      "${DEPLOY_SERVER_DIR}/silverman-worker.compose.yaml" \
      "${DEPLOY_SERVER_DIR}/silverman-worker.env.example" \
      "${DEPLOY_SERVER_DIR}/deploy-worker.sh" \
      "${DEPLOY_SERVER_DIR}/smoke-worker.sh" \
      "${DEPLOY_SERVER_DIR}/verify-worker-deploy.sh" \
      "${DEPLOY_SERVER_DIR}/verify-worker-api-key-rotation.sh" \
      "${TARGET_DIR}/"
  else
    echo "    rsync not found; using cp (no delete of stale files)"
    cp "${SOURCE_ROOT}/Dockerfile" "${SOURCE_ROOT}/pyproject.toml" "${SOURCE_ROOT}/README.md" "${TARGET_DIR}/"
    rm -rf "${TARGET_DIR}/src"
    cp -R "${SOURCE_ROOT}/src" "${TARGET_DIR}/src"
    cp "${DEPLOY_SERVER_DIR}/silverman-worker.compose.yaml" \
      "${DEPLOY_SERVER_DIR}/silverman-worker.env.example" \
      "${DEPLOY_SERVER_DIR}/deploy-worker.sh" \
      "${DEPLOY_SERVER_DIR}/smoke-worker.sh" \
      "${DEPLOY_SERVER_DIR}/verify-worker-deploy.sh" \
      "${DEPLOY_SERVER_DIR}/verify-worker-api-key-rotation.sh" \
      "${TARGET_DIR}/"
  fi

  chmod +x "${TARGET_DIR}/deploy-worker.sh" \
    "${TARGET_DIR}/smoke-worker.sh" \
    "${TARGET_DIR}/verify-worker-deploy.sh" \
    "${TARGET_DIR}/verify-worker-api-key-rotation.sh"
fi

echo "==> Verifying synced Flow A source files in target directory..."
for rel in "${FLOW_A_SOURCE_FILES[@]}"; do
  path="${TARGET_DIR}/${rel}"
  if [[ ! -f "${path}" ]]; then
    echo "ERROR: missing synced source file: ${path}" >&2
    exit 1
  fi
  if command -v shasum >/dev/null 2>&1; then
    digest="$(shasum -a 256 "${path}" | awk '{print $1}')"
    echo "    ${rel} (sha256 ${digest:0:12}...)"
  elif command -v sha256sum >/dev/null 2>&1; then
    digest="$(sha256sum "${path}" | awk '{print $1}')"
    echo "    ${rel} (sha256 ${digest:0:12}...)"
  else
    echo "    ${rel}"
  fi
done

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

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is required to build and start the worker container" >&2
  exit 1
fi

BUILD_REVISION="$(git -C "${SOURCE_ROOT}" rev-parse HEAD 2>/dev/null || date +%s)"
export BUILD_REVISION

echo "==> Building worker image (BUILD_REVISION=${BUILD_REVISION:0:12})..."
cd "${TARGET_DIR}"
if [[ "${FORCE_NO_CACHE}" == "1" ]]; then
  echo "    DEPLOY_FORCE_REBUILD=1: building with --no-cache"
  docker compose -f silverman-worker.compose.yaml build --no-cache
else
  docker compose -f silverman-worker.compose.yaml build
fi

echo "==> Recreating worker container (port 8010)..."
docker compose -f silverman-worker.compose.yaml up -d --force-recreate --remove-orphans

echo "==> Container status"
docker compose -f silverman-worker.compose.yaml ps
if docker ps --format '{{.Names}}' | grep -Fxq "silverman-blog-linkedin-worker"; then
  container_id="$(docker inspect -f '{{.Id}}' silverman-blog-linkedin-worker)"
  image_id="$(docker inspect -f '{{.Image}}' silverman-blog-linkedin-worker)"
  started_at="$(docker inspect -f '{{.State.StartedAt}}' silverman-blog-linkedin-worker)"
  echo "    container id: ${container_id:0:12}"
  echo "    image id:     ${image_id:0:19}"
  echo "    started at:   ${started_at}"
fi

echo "==> Post-deploy verification (OpenAPI Flow A endpoints)..."
if ! DEPLOY_DIR="${TARGET_DIR}" WORKER_BASE_URL="${WORKER_BASE_URL}" \
  "${TARGET_DIR}/verify-worker-deploy.sh"; then
  cat >&2 <<EOF

ERROR: Deploy finished but post-deploy verification failed.
       The running worker on ${WORKER_BASE_URL} may still be serving an old image.

Next steps on the Ubuntu server:
  cd ${TARGET_DIR}
  DEPLOY_FORCE_REBUILD=1 ${TARGET_DIR}/deploy-worker.sh

Or manually:
  cd ${TARGET_DIR}
  BUILD_REVISION=\$(date +%s) docker compose -f silverman-worker.compose.yaml build --no-cache
  docker compose -f silverman-worker.compose.yaml up -d --force-recreate

EOF
  exit 1
fi

echo "==> Deploy complete."
echo "    Worker URL: ${WORKER_BASE_URL}"
echo "    Smoke test: ${TARGET_DIR}/smoke-worker.sh"
READINESS_SCRIPT="${SOURCE_ROOT}/scripts/flow_a_readiness.py"
if [[ -f "${READINESS_SCRIPT}" ]]; then
  echo "    Flow A gate: python3 ${READINESS_SCRIPT} --worker-base-url ${WORKER_BASE_URL} --phase 0"
fi
