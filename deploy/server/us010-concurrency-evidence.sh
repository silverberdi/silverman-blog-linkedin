#!/usr/bin/env bash
# US-010 concurrency evidence using shared-mount lockfile.
# Stops/starts n8n briefly for CLI execute. Redacts secrets from logs.
set -euo pipefail

WORKFLOW_ID="${WORKFLOW_ID:-silvermanFlowAPublish01}"
COMPOSE_DIR="${COMPOSE_DIR:-/home/silverman/local-ai-stack}"
COMPOSE_FILE="${COMPOSE_FILE:-compose.yaml}"
LOCK_HOST="${LOCK_HOST:-/home/silverman/compartido_mac/.silverman-flow-a-single-flight.lock}"

redact() {
  python3 - "$1" <<'PY'
from pathlib import Path
import re, sys
p = Path(sys.argv[1])
t = p.read_text(encoding="utf-8", errors="replace")
t = re.sub(r'"worker_api_key"\s*:\s*"[^"]+"', '"worker_api_key": "[REDACTED]"', t)
t = re.sub(r"Bearer\s+[A-Za-z0-9._\-]+", "Bearer [REDACTED]", t)
p.write_text(t, encoding="utf-8")
print(f"redacted {p}")
PY
}

summarize() {
  python3 - "$1" <<'PY'
from pathlib import Path
import re, sys
text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
last = re.findall(r'"lastNodeExecuted":\s*"([^"]+)"', text)
outcomes = re.findall(r'"outcome":\s*"([^"]+)"', text)
acquired = re.findall(r'"single_flight_acquired":\s*(true|false)', text)
print("lastNode=", last[-1] if last else None)
print("outcomes=", list(dict.fromkeys(outcomes)))
print("acquired_flags=", list(dict.fromkeys(acquired)))
print("publish_executed=", '"Publish Blog Post": [' in text)
print("success=", "Execution was successful" in text)
print("skipped=", "skipped_already_running" in outcomes or "Stop Skipped Already Running" in text)
PY
}

run_execute() {
  local out="$1"
  cd "$COMPOSE_DIR"
  docker compose -f "$COMPOSE_FILE" stop n8n >/dev/null
  set +e
  docker compose -f "$COMPOSE_FILE" run --rm --no-deps --entrypoint n8n n8n \
    execute --id="$WORKFLOW_ID" >"$out" 2>&1
  local rc=$?
  set -e
  docker compose -f "$COMPOSE_FILE" start n8n >/dev/null
  local i
  for i in $(seq 1 40); do
    curl -fsS http://192.168.0.194:5678/healthz >/dev/null 2>&1 && break
    sleep 2
  done
  redact "$out"
  echo "execute_rc=${rc} out=${out}"
  return "$rc"
}

write_lock() {
  local exec_id="$1"
  local acquired_ms="$2"
  python3 - "$LOCK_HOST" "$exec_id" "$acquired_ms" <<'PY'
from pathlib import Path
import json, sys
from datetime import datetime, timezone
path, exec_id, acquired_ms = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
iso = datetime.fromtimestamp(acquired_ms/1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
path.write_text(json.dumps({
    "execution_id": exec_id,
    "acquired_at_ms": acquired_ms,
    "acquired_at_utc": iso,
}), encoding="utf-8")
print(f"PASS: wrote lockfile {path} exec_id={exec_id} acquired_ms={acquired_ms}")
PY
}

clear_lock() {
  rm -f "$LOCK_HOST"
  echo "PASS: cleared lockfile if present"
}

NOW_MS="$(python3 -c 'import time; print(int(time.time()*1000))')"
EXPIRED_MS="$((NOW_MS - 3 * 60 * 60 * 1000))"

echo "==> 5.2 skip while lock held (lockfile)"
write_lock "held-for-skip-test" "$NOW_MS"
run_execute /tmp/us010-exec-skip.txt || true
summarize /tmp/us010-exec-skip.txt
# lock should still be held (skip path does not release)
if [[ -f "$LOCK_HOST" ]]; then echo "PASS: lockfile still present after skip"; else echo "NOTE: lockfile cleared unexpectedly"; fi

echo "==> 5.4 TTL recovery (expired lockfile)"
write_lock "expired-lock-test" "$EXPIRED_MS"
run_execute /tmp/us010-exec-ttl.txt || true
summarize /tmp/us010-exec-ttl.txt

echo "==> 5.5 idempotent empty-ready"
clear_lock
run_execute /tmp/us010-exec-idempotent.txt || true
summarize /tmp/us010-exec-idempotent.txt

TMP="$(mktemp)"
docker exec local-ai-stack-n8n-1 n8n export:workflow --id="$WORKFLOW_ID" --output=/tmp/flow-a-final.json
docker cp "local-ai-stack-n8n-1:/tmp/flow-a-final.json" "$TMP"
python3 - "$TMP" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as fh:
    data = json.load(fh)
w = data[0] if isinstance(data, list) else data
assert w.get("active") is True
assert len(w.get("nodes") or []) == 31
print("PASS: final active=true nodes=31")
PY
rm -f "$TMP"
clear_lock
echo "ready_count=$(ls -1 /home/silverman/compartido_mac/silverman-blog-linkedin/blog-posts/ready/ | wc -l | tr -d ' ')"
echo "OVERALL_OPS_SLICE_DONE"
