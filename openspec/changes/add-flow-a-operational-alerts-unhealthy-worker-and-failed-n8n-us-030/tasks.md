## 1. Orchestration-failure report ingest

- [x] 1.1 Add authenticated `POST /flow-a/operational-alerts/report-orchestration-failure` request model (required `workflow_id` + allowlisted `reason_code`; optional `observed_at_utc`, `execution_id`, `node_name`, `campaign_id`, `run_id`; reject unsafe/extra fields with HTTP 422)
- [x] 1.2 Persist secret-safe orchestration-failure records under `metadata/operational-alerts/orchestration-failures.json` with atomic write and idempotent identical fingerprints
- [x] 1.3 Ensure report writes only the orchestration-failures store (no emissions ledger, no webhook, no campaign/run/calendar/editorial lifecycle mutation) and returns HTTP 401 without a valid API key

## 2. US-030 candidate derivation

- [x] 2.1 Extend `OperationalAlert` (or equivalent) with optional `workflow_id` / `execution_id` and ensure payload serialization omits unset optional fields
- [x] 2.2 Derive `unhealthy_worker` from in-process `validate_folders` / health-equivalent readiness (`folders_ready=false` → one error alert with sorted not-ready folder reason codes; healthy → none); do not HTTP-loopback to `/health`
- [x] 2.3 Derive `failed_n8n_workflow` from open orchestration-failure store entries (one alert per fingerprint; severity `error`); do not map failed `metadata/runs/*` alone to this type
- [x] 2.4 Update summary counts and alert-type constants to include all eight types (US-028 + US-029 + US-030) while preserving existing US-028/US-029 derivation behavior and deterministic ordering

## 3. Emission and contract reuse

- [x] 3.1 Confirm evaluate/emit HTTP contract, auth, fail-closed env flags, webhook adapter, and `metadata/operational-alerts/emissions.json` ledger remain unchanged except for accepting new fingerprints
- [x] 3.2 Ensure evaluate-only still performs no ledger write, no orchestration-failure write, and no campaign/run/calendar/editorial lifecycle mutation; emit still writes only the emissions ledger after HTTP 2xx

## 4. Tests

- [x] 4.1 Add focused tests for `unhealthy_worker` (degraded vs healthy folder fixtures) and `failed_n8n_workflow` (after report ingest; empty store + failed run alone does not produce the type)
- [x] 4.2 Add tests for report auth 401, invalid reason_code/now_utc 422, idempotent duplicate report, eight-type `summary.counts`, safe omission of secrets/raw n8n payloads/absolute base path
- [x] 4.3 Add coexistence regression: US-028 and US-029 types still produced; evaluate-only zero lifecycle mutation; fail-closed emit and idempotent ledger behavior for new US-030 fingerprints
- [x] 4.4 Assert no external provider or n8n API calls during evaluation; run targeted operational-alerts tests plus operational-status regression; resolve warnings attributable to this change

## 5. Documentation and progress

- [x] 5.1 Update `docs/operations/flow-a-operational-alerts.md` for US-030 types, health-equivalent unhealthy-worker evidence, report-ingest contract, severities, and unchanged evaluate/emit/ledger rules
- [x] 5.2 Update `docs/CURRENT-STATE.md` to the demonstrated US-030 implementation level only; do not claim US-030 acceptance, US-028/US-029 re-acceptance, or BL-011 closure
- [x] 5.3 Update `docs/product/user-stories.md` US-030 status and `docs/product/progress-checklist.md` only for criteria actually demonstrated; leave BL-011 closure unchanged

## 6. Business validation

- [x] 6.1 Demonstrate against controlled fixtures that an authenticated operator/n8n client can report orchestration failure and evaluate alerts for unhealthy worker and failed n8n workflow with understandable secret-safe payloads
- [x] 6.2 Confirm failures/blocked states are clearly communicated (alert type, severity, emission status) and that evaluate-only does not mutate existing completed lifecycle work
- [x] 6.3 Confirm out-of-scope items remain absent (BL-015 UI, Slack/email SDK, deploy/live mutation, US-028/US-029 re-acceptance, BL-011 closure) and record remaining acceptance gaps explicitly
