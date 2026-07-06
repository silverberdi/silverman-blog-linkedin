#!/usr/bin/env bash
# Prepare one editorial post pair for GitHub Pages (dry-run by default).
# Does not run git commit/push or modify blog-posts/ready/ sources.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ $# -lt 1 ]]; then
  echo "Usage: publish-blog-post.sh <source-slug> [--date YYYY-MM-DD] [--public-slug SLUG] [--apply] [--json]" >&2
  echo "Environment:" >&2
  echo "  SILVERMAN_BLOG_LINKEDIN_BASE_PATH  editorial workspace root" >&2
  echo "  SILVERMAN_GITHUB_PAGES_REPO_PATH   local clone of silverberdi.github.io" >&2
  echo "  SILVERMAN_SITE_URL                 canonical site URL (default https://silverman.pro)" >&2
  exit 1
fi

if [[ -z "${SILVERMAN_GITHUB_PAGES_REPO_PATH:-}" ]]; then
  echo "ERROR: SILVERMAN_GITHUB_PAGES_REPO_PATH is required" >&2
  exit 1
fi

cd "${REPO_ROOT}"

export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  PYTHON="${REPO_ROOT}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  echo "ERROR: python3 not found; create .venv or install Python 3.11+" >&2
  exit 1
fi

exec "${PYTHON}" -m silverman_blog_linkedin.github_pages_publish "$@"
