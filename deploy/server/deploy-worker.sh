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
  "prompts"
)

has_target_layout_markers() {
  local base="$1"
  local name
  for name in "${TARGET_LAYOUT_MARKERS[@]}"; do
    if [[ "${name}" == "src" || "${name}" == "prompts" ]]; then
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
  for name in src prompts; do
    if [[ ! -d "${TARGET_DIR}/${name}" ]]; then
      echo "ERROR: missing ${name}/ in ${TARGET_DIR}" >&2
      exit 1
    fi
  done
else
  echo "==> Repo layout: syncing build and deployment artifacts..."

  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "${RSYNC_EXCLUDES[@]}" \
      "${SOURCE_ROOT}/Dockerfile" \
      "${SOURCE_ROOT}/pyproject.toml" \
      "${SOURCE_ROOT}/README.md" \
      "${SOURCE_ROOT}/src" \
      "${SOURCE_ROOT}/prompts" \
      "${SOURCE_ROOT}/content-strategy" \
      "${TARGET_DIR}/"

    mkdir -p "${TARGET_DIR}/frontend"
    rsync -a --delete "${RSYNC_EXCLUDES[@]}" \
      --exclude 'node_modules/' \
      --exclude 'dist/' \
      "${SOURCE_ROOT}/frontend/linkedin-variant-supervision-console/" \
      "${TARGET_DIR}/frontend/linkedin-variant-supervision-console/"

    rsync -a \
      "${DEPLOY_SERVER_DIR}/silverman-worker.compose.yaml" \
      "${DEPLOY_SERVER_DIR}/silverman-worker.env.example" \
      "${DEPLOY_SERVER_DIR}/silverman-operator-ui.env.example" \
      "${DEPLOY_SERVER_DIR}/deploy-worker.sh" \
      "${DEPLOY_SERVER_DIR}/smoke-worker.sh" \
      "${DEPLOY_SERVER_DIR}/verify-worker-deploy.sh" \
      "${DEPLOY_SERVER_DIR}/verify-worker-api-key-rotation.sh" \
      "${DEPLOY_SERVER_DIR}/run-linkedin-publication-smoke.sh" \
      "${DEPLOY_SERVER_DIR}/run-us001-git-publication-smoke.sh" \
      "${DEPLOY_SERVER_DIR}/run-us002-live-site-confirmation-smoke.sh" \
      "${DEPLOY_SERVER_DIR}/run-us003-linkedin-publication-validation-smoke.sh" \
      "${DEPLOY_SERVER_DIR}/run-flow-a-worker-smoke.sh" \
      "${DEPLOY_SERVER_DIR}/collect-flow-a-smoke-evidence.sh" \
      "${TARGET_DIR}/"
  else
    echo "    rsync not found; using cp (no delete of stale files)"
    cp "${SOURCE_ROOT}/Dockerfile" "${SOURCE_ROOT}/pyproject.toml" "${SOURCE_ROOT}/README.md" "${TARGET_DIR}/"
    rm -rf "${TARGET_DIR}/src" "${TARGET_DIR}/prompts" "${TARGET_DIR}/content-strategy"
    cp -R "${SOURCE_ROOT}/src" "${TARGET_DIR}/src"
    cp -R "${SOURCE_ROOT}/prompts" "${TARGET_DIR}/prompts"
    cp -R "${SOURCE_ROOT}/content-strategy" "${TARGET_DIR}/content-strategy"
    mkdir -p "${TARGET_DIR}/frontend"
    rm -rf "${TARGET_DIR}/frontend/linkedin-variant-supervision-console"
    cp -R "${SOURCE_ROOT}/frontend/linkedin-variant-supervision-console" \
      "${TARGET_DIR}/frontend/linkedin-variant-supervision-console"
    rm -rf "${TARGET_DIR}/frontend/linkedin-variant-supervision-console/node_modules" \
      "${TARGET_DIR}/frontend/linkedin-variant-supervision-console/dist"
    cp "${DEPLOY_SERVER_DIR}/silverman-worker.compose.yaml" \
      "${DEPLOY_SERVER_DIR}/silverman-worker.env.example" \
      "${DEPLOY_SERVER_DIR}/silverman-operator-ui.env.example" \
      "${DEPLOY_SERVER_DIR}/deploy-worker.sh" \
      "${DEPLOY_SERVER_DIR}/smoke-worker.sh" \
      "${DEPLOY_SERVER_DIR}/verify-worker-deploy.sh" \
      "${DEPLOY_SERVER_DIR}/verify-worker-api-key-rotation.sh" \
      "${DEPLOY_SERVER_DIR}/run-linkedin-publication-smoke.sh" \
      "${DEPLOY_SERVER_DIR}/run-us001-git-publication-smoke.sh" \
      "${DEPLOY_SERVER_DIR}/run-us002-live-site-confirmation-smoke.sh" \
      "${DEPLOY_SERVER_DIR}/run-us003-linkedin-publication-validation-smoke.sh" \
      "${DEPLOY_SERVER_DIR}/run-flow-a-worker-smoke.sh" \
      "${DEPLOY_SERVER_DIR}/collect-flow-a-smoke-evidence.sh" \
      "${TARGET_DIR}/"
  fi

  chmod +x "${TARGET_DIR}/deploy-worker.sh" \
    "${TARGET_DIR}/smoke-worker.sh" \
    "${TARGET_DIR}/verify-worker-deploy.sh" \
    "${TARGET_DIR}/verify-worker-api-key-rotation.sh" \
    "${TARGET_DIR}/run-linkedin-publication-smoke.sh" \
    "${TARGET_DIR}/run-us001-git-publication-smoke.sh" \
    "${TARGET_DIR}/run-us002-live-site-confirmation-smoke.sh" \
    "${TARGET_DIR}/run-us003-linkedin-publication-validation-smoke.sh" \
    "${TARGET_DIR}/run-flow-a-worker-smoke.sh" \
    "${TARGET_DIR}/collect-flow-a-smoke-evidence.sh"
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

resolve_public_blog_repo_host_path() {
  local path="${SILVERMAN_PUBLIC_BLOG_REPO_PATH:-}"
  if [[ -z "${path}" && -f "${TARGET_DIR}/.env" ]]; then
    path="$(
      grep -E '^[[:space:]]*SILVERMAN_PUBLIC_BLOG_REPO_PATH=' "${TARGET_DIR}/.env" 2>/dev/null \
        | tail -1 \
        | cut -d= -f2- \
        | tr -d '"' \
        | tr -d "'" \
        || true
    )"
  fi
  echo "${path:-/home/silverman/silverberdi.github.io}"
}

check_public_blog_repo_path() {
  local host_path
  host_path="$(resolve_public_blog_repo_host_path)"

  if [[ "${SKIP_PUBLIC_BLOG_REPO_CHECK:-0}" == "1" ]]; then
    echo "==> Public blog repo check skipped (SKIP_PUBLIC_BLOG_REPO_CHECK=1)"
    echo "    configured host path: ${host_path}"
    return 0
  fi

  echo "==> Verifying public GitHub Pages repo checkout for Flow A publish..."
  echo "    host path: ${host_path}"
  echo "    container path: /public-blog (SILVERMAN_GITHUB_PAGES_REPO_PATH)"

  if [[ ! -d "${host_path}" ]]; then
    cat >&2 <<EOF

ERROR: Public blog repo checkout not found at ${host_path}

Flow A publish requires a local clone of the GitHub Pages repository
(silverberdi.github.io) mounted at /public-blog inside the worker container.

Remediation (manual — deploy does not clone automatically):
  1. Clone or sync the GitHub Pages repo on the Ubuntu server:
       git clone git@github.com:silverberdi/silverberdi.github.io.git ${host_path}
     Or rsync from another machine that already has the checkout.
  2. Ensure the checkout contains:
       ${host_path}/_posts/
       ${host_path}/assets/images/
  3. Set SILVERMAN_PUBLIC_BLOG_REPO_PATH in ${TARGET_DIR}/.env if using a non-default path.
  4. Re-run this deploy script.

To deploy without Flow A publishing (non-publishing smoke only), set:
  SKIP_PUBLIC_BLOG_REPO_CHECK=1

Without a valid public repo mount, POST /publish-blog-post fails with:
  blog_publish_public_repo_not_configured

EOF
    exit 1
  fi

  local missing=()
  if [[ ! -d "${host_path}/_posts" ]]; then
    missing+=("_posts/")
  fi
  if [[ ! -d "${host_path}/assets/images" ]]; then
    missing+=("assets/images/")
  fi

  if [[ "${#missing[@]}" -gt 0 ]]; then
    cat >&2 <<EOF

ERROR: Public blog repo at ${host_path} is missing required layout:
  ${missing[*]}

Remediation:
  - Ensure ${host_path} is a complete silverberdi.github.io checkout
  - Required directories: _posts/ and assets/images/
  - Or set SKIP_PUBLIC_BLOG_REPO_CHECK=1 only for non-publishing deploys

EOF
    exit 1
  fi

  echo "    public blog repo layout OK (_posts/, assets/images/)"
}

check_public_blog_repo_path

LINKEDIN_SECRETS_DIR="/home/silverman/silverman-blog-linkedin-worker/secrets"
echo "==> Ensuring LinkedIn OAuth secrets directory..."
echo "    host path: ${LINKEDIN_SECRETS_DIR}"
mkdir -p "${LINKEDIN_SECRETS_DIR}"
chmod 700 "${LINKEDIN_SECRETS_DIR}"

LINKEDIN_OAUTH_DIR="${LINKEDIN_SECRETS_DIR}/linkedin-oauth"
mkdir -p "${LINKEDIN_OAUTH_DIR}"
chmod 700 "${LINKEDIN_OAUTH_DIR}"

LINKEDIN_OAUTH_TOKEN_FILE="${LINKEDIN_OAUTH_DIR}/linkedin-oauth-tokens.json"
LINKEDIN_OAUTH_STATE_FILE="${LINKEDIN_OAUTH_DIR}/linkedin-oauth-state.json"
for oauth_file in "${LINKEDIN_OAUTH_TOKEN_FILE}" "${LINKEDIN_OAUTH_STATE_FILE}"; do
  if [[ ! -f "${oauth_file}" ]]; then
    echo "    creating placeholder: ${oauth_file}"
    : > "${oauth_file}"
  fi
  chmod 600 "${oauth_file}"
done

# Migrate legacy flat secrets/linkedin-oauth-*.json if directory files are empty
legacy_token="${LINKEDIN_SECRETS_DIR}/linkedin-oauth-tokens.json"
legacy_state="${LINKEDIN_SECRETS_DIR}/linkedin-oauth-state.json"
if [[ -f "${legacy_token}" && ! -s "${LINKEDIN_OAUTH_TOKEN_FILE}" && -s "${legacy_token}" ]]; then
  echo "    migrating legacy token file into ${LINKEDIN_OAUTH_DIR}/"
  cp "${legacy_token}" "${LINKEDIN_OAUTH_TOKEN_FILE}"
  chmod 600 "${LINKEDIN_OAUTH_TOKEN_FILE}"
fi
if [[ -f "${legacy_state}" && ! -s "${LINKEDIN_OAUTH_STATE_FILE}" && -s "${legacy_state}" ]]; then
  echo "    migrating legacy state file into ${LINKEDIN_OAUTH_DIR}/"
  cp "${legacy_state}" "${LINKEDIN_OAUTH_STATE_FILE}"
  chmod 600 "${LINKEDIN_OAUTH_STATE_FILE}"
fi

GIT_PUBLICATION_KEY_FILE="${LINKEDIN_SECRETS_DIR}/github-pages-deploy-key"
GIT_PUBLICATION_KNOWN_HOSTS="${LINKEDIN_SECRETS_DIR}/known_hosts"
if [[ ! -f "${GIT_PUBLICATION_KEY_FILE}" ]]; then
  cat >&2 <<EOF

WARN: Git publication deploy key not found at ${GIT_PUBLICATION_KEY_FILE}.
      Git publication will fail until the key is installed (see deployment docs).

EOF
fi
if [[ ! -f "${GIT_PUBLICATION_KNOWN_HOSTS}" ]]; then
  cat >&2 <<EOF

WARN: Git publication known_hosts not found at ${GIT_PUBLICATION_KNOWN_HOSTS}.
      Git publication SSH will fail until known_hosts is installed.

EOF
fi

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
