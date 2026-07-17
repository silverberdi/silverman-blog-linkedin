## Context

US-026 and US-027 deliver authenticated read-only `GET /flow-a/operational-status`. Canonical contract: `openspec/specs/flow-a-operational-status/spec.md`.

`GET /health` (worker-foundation) reports process-reachable editorial readiness: `status` `healthy`|`degraded`, `folders_ready`, and per-folder details via `validate_folders`. It does **not** currently expose `BUILD_REVISION` in the JSON body (operators confirm deploy identity via container env / deploy metadata).

US-028 + US-029 deliver authenticated `POST /flow-a/operational-alerts/evaluate` with optional fail-closed generic webhook emission and `metadata/operational-alerts/emissions.json` for six alert types. Canonical contract: `openspec/specs/flow-a-operational-alerts/spec.md`. Implementation: `src/silverman_blog_linkedin/flow_a_operational_alerts.py`.

BL-011 / US-030 needs operators to be **notified** when attention is required for:

1. unhealthy worker, and/or
2. failed n8n workflow.

US-028 and US-029 remain implemented/tested locally (business acceptance pending) and MUST NOT be reworked or re-accepted by this change. BL-015 remains out of scope. ADR-0001 requires n8n ↔ worker HTTP only (no Execute Command).

## Goals / Non-Goals

**Goals:**

- Derive `unhealthy_worker` from concrete health-equivalent evidence the worker already owns.
- Make `failed_n8n_workflow` observable without violating ADR-0001, via a narrow authenticated evidence-ingest contract when existing health/status evidence is insufficient.
- Reuse the evaluate/emit HTTP contract, fail-closed enablement, secret-safe payloads, and emission ledger.
- Extend `summary.counts` for the two US-030 types while preserving all six prior count keys and behaviors.
- Preserve campaign/run/calendar/editorial lifecycle immutability during evaluate-only (emit ledger-only; report writes only alerts evidence).

**Non-Goals:**

- Re-accepting US-028/US-029 or closing BL-011 from proposal/code alone.
- BL-015 UI; Slack/email/SMS SDKs; deploy/live webhook enablement.
- Changing `GET /flow-a/operational-status` request/response shape.
- Alerting on process-down / unreachable worker (n8n cannot call evaluate when the worker is down).
- `BUILD_REVISION` / deploy-mismatch alerts.
- Treating every failed `metadata/runs/*.json` as a failed n8n workflow.
- Calling external provider APIs during evaluation.

## Decisions

### 1. Extend evaluate/emit — no parallel alerts channel

**Decision:** Keep `POST /flow-a/operational-alerts/evaluate` as the sole alert-evaluation and optional-emission HTTP boundary. Same request fields (`now_utc`, `emit`), same auth, same env flags, same emissions ledger, same fail-closed semantics.

US-030 only extends candidate derivation and summary counts. n8n continues to schedule the same evaluate endpoint over HTTP (ADR-0001).

Alternatives considered:

- Separate `/evaluate-us-030` route: rejected; fragments the operator contract.
- New Slack/email adapter: rejected; out of scope.

### 2. What defines “unhealthy worker” (concrete evidence)

**Decision:** For US-030 MVP, `unhealthy_worker` means the worker is reachable but **editorial-layout readiness is degraded**, using the **same** in-process evidence as `GET /health`:

| Signal | Source | Alert? |
|--------|--------|--------|
| `folders_ready == false` / would-be `status=degraded` | `validate_folders(base_path)` (shared with `/health`) | Yes → one `unhealthy_worker` alert |
| `folders_ready == true` / would-be `status=healthy` | same | No unhealthy-worker alert |
| Process down / HTTP unreachable | n8n health-check failure outside worker | **Out of scope** for worker-emitted alerts |
| `BUILD_REVISION` / deploy mismatch | not part of `/health` JSON today | **Out of scope** (do not invent) |
| ComfyUI / DeepSeek / LinkedIn / Git readiness probes | would require external calls | **Out of scope** during evaluate; campaign dependency failures remain US-028/US-029 |

Evaluate MUST call `validate_folders` in-process (or an equivalent shared helper). It MUST NOT HTTP-loopback to `/health`, and MUST NOT call external provider APIs.

**Severity:** `error`.

**Payload:** `alert_type=unhealthy_worker`, sorted stable reason codes for not-ready folders (for example `editorial_folder_not_ready:<folder_name>`), short summary, no absolute `base_path`, no secrets. Optional `error_codes` list; no `campaign_id` / `run_id` required.

**Fingerprint:** `unhealthy_worker:folders_not_ready:{comma-sorted-not-ready-folder-names}` so a different missing-folder set can re-open attention without inventing a reset API.

**Rationale:** US-030 asks for unhealthy worker attention the worker can observe. Folder unreadiness is the existing, tested health contract. Process liveness is tautological when evaluate succeeds. Deploy-revision mismatch and live dependency probes are not declared product requirements and are not currently evaluate-owned evidence.

Alternatives considered:

- Infer unhealthy from operational-status `data_issues` alone: rejected; those are evidence-parse issues, not worker health.
- Add `BUILD_REVISION` to `/health` and alert on mismatch: rejected for this change; expands worker-foundation without backlog AC and invents expected-revision config.
- Probe ComfyUI/LinkedIn during evaluate: rejected; contradicts fail-closed evaluate and duplicates dependency alerts.

### 3. What defines “failed n8n workflow” (concrete evidence)

**Decision:** The worker **cannot** observe n8n execution history under ADR-0001 (no Execute Command; no assumed n8n Admin API scrape). Existing operational-status failed runs are **worker execution outcomes**, not proof that an n8n workflow failed (and mapping all failed runs to `failed_n8n_workflow` would mislabel and overlap US-028/US-029).

Therefore US-030 requires a **narrow new evidence contract** that still respects ADR-0001:

1. Authenticated `POST /flow-a/operational-alerts/report-orchestration-failure` accepts a secret-safe failure report from n8n (Error Trigger / catch / IF failure branch) or an operator client.
2. The worker persists the report under `metadata/operational-alerts/` only (isolated from campaign/run/calendar/editorial lifecycle docs).
3. `POST /flow-a/operational-alerts/evaluate` derives `failed_n8n_workflow` candidates from that persisted store (plus emit/ledger rules unchanged).

**Report body (MVP, `extra` forbidden):**

| Field | Required | Notes |
|-------|----------|-------|
| `workflow_id` | yes | Stable opaque id (e.g. `silvermanFlowAPublish01`); validated non-empty safe token |
| `reason_code` | yes | Validated machine code from an allowlist (e.g. `n8n_workflow_failed`, `n8n_http_node_failed`, `n8n_error_trigger`) |
| `observed_at_utc` | no | Canonical UTC; default request-time UTC |
| `execution_id` | no | Opaque n8n execution id if known |
| `node_name` | no | Short safe label; no expression dumps |
| `campaign_id` / `run_id` | no | Only if already known and valid-shaped |

Rejected fields: raw error stacks, HTTP response bodies, authorization headers, webhook URLs, Markdown/content bodies, absolute paths, arbitrary env dumps.

**Persistence:** `metadata/operational-alerts/orchestration-failures.json` (versioned entries map keyed by a stable report fingerprint / id). Atomic write. Report endpoint MUST NOT write emissions ledger or lifecycle artifacts.

**Alert derivation:** one `failed_n8n_workflow` alert per distinct open report fingerprint present at evaluate time.

**Severity:** `error`.

**Fingerprint (alert):** `failed_n8n_workflow:{workflow_id}:{reason_code}:{execution_id|none}` (normalized).

**Payload:** includes `workflow_id`, `reason_code` in `error_codes`, optional `execution_id` as a safe identifier field (or encoded only in fingerprint if keeping the dataclass minimal — prefer optional `workflow_id` + `execution_id` fields on the alert object, omitted when unset), short summary; no secrets.

**Evaluate-only** MUST NOT create orchestration-failure reports. **Emit** MUST NOT create them either.

Alternatives considered:

- Derive solely from failed `metadata/runs/*`: rejected; confuses worker run failure with n8n workflow failure and duplicates other alerts.
- Have evaluate accept ephemeral `orchestration_failures[]` in the request body without persistence: workable for one-shot calls but loses durable evidence for later evaluate/emit polls; rejected as primary design.
- Worker polls n8n REST API: rejected; invents credentials/topology and violates the HTTP-orchestration ownership model.

### 4. Evidence model summary (answers the design questions)

| Alert type | Evidence class | New contract? |
|------------|----------------|---------------|
| `unhealthy_worker` | Existing health-equivalent folder readiness (`validate_folders` / `/health`) | No |
| `failed_n8n_workflow` | Worker-persisted orchestration-failure reports | Yes — narrow authenticated report ingest |
| US-028 / US-029 types | Existing operational-status evidence | No (unchanged) |

US-030 is therefore a **hybrid**: health-derived + narrow ingest, both evaluated through the existing evaluate/emit surface.

### 5. Preserve payloads, counts, ordering, emission, non-mutation

**Decision:**

- Reuse `OperationalAlert` shape; add optional `workflow_id` and `execution_id` for n8n alerts (omit when unset).
- `summary.counts` MUST include the prior six keys **plus** `unhealthy_worker` and `failed_n8n_workflow` (eight types).
- Ordering remains `alert_type` ascending, then `fingerprint` ascending.
- Same fail-closed emit flags and `emissions.json` ledger; new fingerprints participate in once-per-fingerprint emit.
- Evaluate-only: zero lifecycle mutation; no emissions write; no orchestration-failure write.
- Report: writes only orchestration-failure store under `metadata/operational-alerts/`.
- Emit: writes only `emissions.json` after HTTP 2xx.

### 6. Preserve operational-status as observation-only

**Decision:** Do not add alert fields to `GET /flow-a/operational-status`. Update purpose/scope text so BL-011 US-028/US-029/**US-030** alerting is owned by `flow-a-operational-alerts`. No request/response shape change.

### 7. Documentation and progress discipline

Update `docs/CURRENT-STATE.md`, `docs/operations/flow-a-operational-alerts.md`, and product progress only to the demonstrated level after implementation. Do not mark US-030 accepted, do not re-accept US-028/US-029, and do not close BL-011 from proposal/code alone. Shipping or activating an n8n Error Trigger workflow is an optional later ops step — not required to complete implementation (tests use controlled fixtures / direct report calls).

## Risks / Trade-offs

- **[Risk] Operators expect process-down alerts from evaluate** → Mitigation: document that unreachable worker is an n8n `/health` failure outside this contract; US-030 covers degraded-but-reachable readiness.
- **[Risk] n8n never calls report ingest → `failed_n8n_workflow` never appears** → Mitigation: contract + tests + operator docs make the report path explicit; implementation completeness does not require live n8n wiring.
- **[Risk] Alert storms if n8n retries report on every failure poll** → Mitigation: persist by fingerprint; evaluate/emit ledger still once-per-alert-fingerprint; report endpoint is idempotent for identical fingerprints.
- **[Risk] Overlap between failed runs and n8n reports** → Mitigation: do not auto-map runs to n8n alerts; keep report explicit.
- **[Risk] Regressing US-028/US-029** → Mitigation: keep prior derivation intact; add US-030 beside it; regression tests for all eight types.
- **[Trade-off] Once-per-fingerprint means cleared-then-recurring conditions need a new fingerprint** → Same as US-028/US-029 MVP; acceptable.
- **[Trade-off] Hybrid evidence (health + ingest)** → Necessary under ADR-0001; prefer honesty over inventing n8n observability the worker does not have.

## Migration Plan

1. Implement report ingest + US-030 derivation + eight-type summary counts with tests (`emit` default false).
2. Confirm US-028/US-029 regression suite still passes.
3. Document alert types and report contract in operator docs; leave webhook enablement false until operator approval.
4. Optional later ops: wire n8n Error Trigger / catch to report + schedule evaluate — not part of default change completion.
5. Rollback: disable emit flag; evaluate/report remain available; lifecycle artifacts untouched.

## Open Questions

None blocking proposal approval. Apply-time may choose exact allowlisted `reason_code` string set and whether `execution_id` is a first-class alert field vs fingerprint-only; prefer first-class optional fields for operator clarity, omitted when unset.
