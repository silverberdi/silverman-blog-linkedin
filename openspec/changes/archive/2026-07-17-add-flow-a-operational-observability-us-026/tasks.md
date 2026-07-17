## 1. Operational Status Service

- [x] 1.1 Add a focused `flow_a_operational_status` module with safe result models, canonical UTC parsing, stable data-issue codes, and deterministic sorting.
- [x] 1.2 Implement confined direct-file readers for `metadata/runs/*.json`, `metadata/campaigns/*.json`, and `editorial-calendar/calendar.json`, rejecting escaping symlinks and malformed or identifier-inconsistent artifacts without returning raw content.
- [x] 1.3 Implement persisted worker execution classification for `completed` and `failed` run records using a safe output-field whitelist and no inferred campaign linkage.
- [x] 1.4 Implement independent Flow A campaign `successful`, `failed`, `blocked`, `stale`, and `in_progress` derivations from canonical lifecycle and `source_file_status` evidence.
- [x] 1.5 Reuse `SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS` and derive stale processing from `last_progress_at`, including fail-safe handling for missing or invalid progress clocks without invoking stale-state mutation.
- [x] 1.6 Implement LinkedIn progress summaries from existing `linkedin_distribution` and variant schedule, queue, `publish_state`, and publication timestamps without duplicating publication eligibility or dependency logic.
- [x] 1.7 Implement delayed-calendar classification from non-terminal item status and strict `due_at_utc < observed_at_utc`, with terminal and exact-due boundary handling.
- [x] 1.8 Aggregate source results, counts, partial status, stable data issues, and one request-level `observed_at_utc` into the specified read-only response.

## 2. HTTP Contract and Safety Boundary

- [x] 2.1 Add `GET /flow-a/operational-status` to the FastAPI application with `Depends(require_api_key)`, optional canonical `now_utc` query validation, and no request body, dry-run mode, or path parameter.
- [x] 2.2 Ensure route logging contains only safe counts/status fields and never absolute base paths, content bodies, credentials, arbitrary source values, or raw exceptions.
- [x] 2.3 Keep the aggregation module free of metadata/calendar writers, lifecycle/recovery/publication services, Git helpers, HTTP clients, and external dependency clients.

## 3. Behavioral Tests

- [x] 3.1 Add service tests for completed/failed/unknown persisted run statuses, safe fields, deterministic ordering, and the no-synthetic-campaign-history boundary.
- [x] 3.2 Add campaign tests covering lifecycle success qualification, failure states, all blocking recovery classifications, retryable non-blocking behavior, combined flags, and LinkedIn publication separation.
- [x] 3.3 Add stale tests for before/equal/after threshold, persisted `stale`, divergent lease evidence, missing/invalid `last_progress_at`, and reuse of configured default/minimum validation.
- [x] 3.4 Add LinkedIn summary tests for existing state counts, anchors, elapsed pending/queued windows, invalid state/timestamp evidence, and no duplicated sequence/cadence/OAuth checks.
- [x] 3.5 Add calendar tests for `planned`, `scheduled`, `due`, and `in_progress` delays; exact-due and future boundaries; terminal exclusions; invalid/missing calendar evidence; and ordering.
- [x] 3.6 Add malformed-file, filename/ID mismatch, escaping-symlink, missing-directory, empty-valid-source, safe-data-issue, and partial-results tests.
- [x] 3.7 Add byte-for-byte inventory and content snapshots proving repeated service calls perform no writes, file moves, stale marking, reconciliation, publication, Git, or external API calls.
- [x] 3.8 Add HTTP tests for authenticated success, HTTP 401, invalid `now_utc` HTTP 422, deterministic supplied time, response shape, secret/body exclusion, and zero mutation.

## 4. Documentation and Status

- [x] 4.1 Document the endpoint, response fields, precise execution/campaign/stale/delay classifications, data-source limitation, partial-result behavior, and read-only guarantee for operators.
- [x] 4.2 Update `docs/CURRENT-STATE.md` after implementation verification to record the capability as implemented/tested without claiming deployment, operational validation, alerting, US-027, or BL-010 closure.
- [x] 4.3 Update `docs/product/progress-checklist.md` and US-026 status only to the demonstrated business-validation level; leave US-027 and BL-010 incomplete until separately accepted.

## 5. Verification and Business Validation

- [x] 5.1 Run targeted operational-status service and HTTP tests, plus affected Flow A lifecycle, operational queue, editorial calendar, and LinkedIn scheduling/publication regression suites.
- [x] 5.2 Run the full pytest suite because executable worker code changes, resolve any new warnings attributable to this change, and run strict OpenSpec validation.
- [x] 5.3 Run `git diff --check` and a secrets/content-body audit over all modified files and representative endpoint responses.
- [x] 5.4 Demonstrate US-026 against controlled fixtures containing successful and failed runs, blocked and stale campaigns, and delayed calendar items; record that one response is understandable and that source bytes remain unchanged.
- [ ] 5.5 Obtain business review of every US-026 acceptance criterion before marking the story accepted; keep BL-010 open for US-027 stage-duration and dependency-failure work.
