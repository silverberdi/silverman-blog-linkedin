#!/usr/bin/env bash
# Copy the HTTP-only publish-pending runner to Ubuntu and execute it.
# Defaults to the server runner's dry-run mode. Pass --real explicitly for a
# separately approved real window; this helper never deploys or changes flags.
set -euo pipefail

SERVER="${SERVER:-silverman@192.168.0.194}"
WORKER_ROOT="${WORKER_ROOT:-/home/silverman/silverman-blog-linkedin-worker}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOCAL_SCRIPT="${REPO_ROOT}/deploy/server/run-publish-pending-linkedin-variants.sh"
REMOTE_SCRIPT="${WORKER_ROOT}/run-publish-pending-linkedin-variants.sh"

printf '==> Copy HTTP runner to %s\n' "${SERVER}"
scp "${LOCAL_SCRIPT}" "${SERVER}:${REMOTE_SCRIPT}"

remote_args=()
for arg in "$@"; do
  printf -v quoted '%q' "${arg}"
  remote_args+=("${quoted}")
done

printf '==> Run publish-pending worker request (dry-run unless --real was supplied)\n'
ssh "${SERVER}" \
  "chmod +x $(printf '%q' "${REMOTE_SCRIPT}") && $(printf '%q' "${REMOTE_SCRIPT}") ${remote_args[*]}"
