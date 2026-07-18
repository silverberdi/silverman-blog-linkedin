## Context

BL-012 / US-031 asks for a consistent operator recovery model for Flow A campaigns that stop before campaign lifecycle completion (`flow_a_complete`). The worker already persists rich recovery-relevant evidence:

- Campaign pipeline `state` and append-only `state_history` (`flow-a-lifecycle`)
- Operational `source_file_status` (`location`, `execution_state`, `recovery_classification`, `physical_move_state`, claim clocks)
- Durable stage evidence (`blog_publish`, `linkedin_package` / `variants[]`, `linkedin_distribution` / schedule fields)
- Existing idempotent stage services (`publish_blog_post`, package generation, `schedule_linkedin_distribution`, source lifecycle completion) and queue claim/stale/reclaim/requeue helpers (`flow-a-operational-queue-lifecycle`)

What is missing is a single authenticated HTTP surface that (1) derives an explicit last-valid-stage from that evidence, (2) resumes unfinished work without repeating durable side effects, and (3) repairs allowlisted metadata inconsistencies with fail-closed ambiguity handling and operator-visible outcomes.

Adjacent but out of primary scope: LinkedIn API publication recovery (BL-008 / US-021–US-022), operational status/alerts (BL-010 / BL-011), concurrency hardening (BL-013), backup (BL-014), and UI (BL-015). CURRENT-STATE already treats Flow A core pipeline as operationally validated; this change adds recovery tooling, not a claim that incomplete campaigns are already solved.

Constraints: ADR-0001 (n8n → worker HTTP only), path confinement under `SILVERMAN_BLOG_LINKEDIN_BASE_PATH`, no secrets in responses, no new lifecycle states unless strictly necessary (none proposed here), and no Git push / live-site / LinkedIn API / deploy enablement as part of this change.

## Goals / Non-Goals

**Goals:**

- Expose authenticated inspect, resume, and repair contracts that satisfy US-031.
- Derive `last_valid_stage` deterministically from persisted campaign evidence without inventing lifecycle states.
- Resume unfinished Flow A worker stages idempotently using existing stage services and short-circuits.
- Repair only allowlisted, unambiguous metadata/filesystem mismatches; fail closed otherwise.
- Reuse canonical `recovery_classification` values; keep status/alerts contracts intact.
- Make every outcome and block reason operator-visible in structured, secret-safe JSON.

**Non-Goals:**

- US-032 action taxonomy, dedicated recovery attempt ledger, or safe cancellation.
- BL-013/014/015, LinkedIn publication recovery rework, production n8n workflow ship/activation.
- Silent auto-healing, inventing missing publish/package/schedule success evidence, or opting into Git/live-site/LinkedIn API side effects by default.
- Marking US-031 accepted or BL-012 closed from proposal/code alone.

## Decisions

### 1. Three authenticated HTTP operations under one recovery prefix

Add worker routes protected by `Depends(require_api_key)`:

| Operation | Method / path | Mutation |
|-----------|---------------|----------|
| Inspect | `GET /flow-a/incomplete-campaign-recovery/{campaign_id}` | None (read-only) |
| Resume | `POST /flow-a/incomplete-campaign-recovery/resume` | Yes (optional `dry_run`) |
| Repair | `POST /flow-a/incomplete-campaign-recovery/repair` | Yes (optional `dry_run`) |

Request bodies for mutating modes MUST include `campaign_id` and MUST NOT accept client-supplied absolute filesystem paths. Optional `dry_run` defaults to `false`; when `true`, the service returns the planned outcome without writing metadata, moving files, or invoking mutating stage side effects.

Clients MUST NOT pass editorial content bodies. Responses MUST exclude secrets, tokens, Markdown/draft bodies, absolute base paths, and provider payloads.

Alternatives considered:

- Single POST with `mode=inspect|resume|repair`: workable, but mixes read-only inspect with mutations and forces POST for observation; rejected in favor of GET inspect (matches `GET /flow-a/operational-status` pattern).
- Extend operational-status with repair actions: rejected — status is intentionally read-only (US-026) and must stay that way.
- n8n Execute Command / filesystem scrape: rejected by ADR-0001.

### 2. Derive `last_valid_stage` from durable milestones — no new lifecycle states

`last_valid_stage` is a derived operator field. It MUST use existing durable pipeline milestone names only:

- `ready` — campaign exists but no durable post-validation external stage evidence is confirmed
- `validated` — validation durable; blog publish not confirmed
- `blog_published` — `blog_publish` durable success confirmed (`completed` or `already_published` with matching identity evidence)
- `derivatives_generated` — package/variants durable evidence confirmed
- `distribution_scheduled` — distribution schedule durable evidence confirmed
- `flow_a_complete` — campaign lifecycle completion confirmed (`state=flow_a_complete` and `location=processed` with consistent evidence)

Intermediate pending states (`blog_publish_pending`, `derivatives_pending`) and terminal failure states (`validation_failed`, `error`) are not themselves “last valid durable milestones.” For failure/error campaigns, inspect still reports the highest confirmed durable milestone from evidence (which may be `ready` / `validated` / later) plus blocked/failure context — it MUST NOT invent success.

Derivation algorithm (normative intent for specs):

1. Collect candidate milestones from (a) current `state` when it is a durable milestone, (b) `state_history` entries whose `to_state` is a durable milestone, and (c) stage evidence markers.
2. Confirm each candidate against its required durable evidence (below). Unconfirmed candidates are discarded.
3. `last_valid_stage` is the highest confirmed milestone in pipeline order.
4. If metadata and filesystem/evidence conflict such that two milestones cannot be reconciled without guessing → set outcome `blocked` with `recovery_classification=repair_required` (or retain existing classification when already more severe) and stable code `flow_a_recovery_evidence_ambiguous`. Resume MUST NOT proceed.

Minimum durable evidence markers:

| Milestone | Required evidence (all must hold) |
|-----------|-----------------------------------|
| `validated` | Campaign passed validation path; not solely `validation_failed` |
| `blog_published` | `blog_publish.status` in `{completed, already_published}` with stable identity/idempotency evidence already required by blog publish specs |
| `derivatives_generated` | Non-empty durable package/variant evidence required by package-generation specs (e.g. `linkedin_package` / expected `variants[]`) |
| `distribution_scheduled` | `linkedin_distribution` + per-variant schedule fields required by scheduling specs for a successful schedule |
| `flow_a_complete` | `state=flow_a_complete` AND `source_file_status.location=processed` AND source identity consistent with processed consumption |

Physical location is corroborating evidence for repair decisions; a missing file alone does not erase confirmed `blog_published` short-circuit evidence when publish specs already allow already-published without resolvable editorial sources.

Alternative considered: introduce new enum values like `last_valid_stage=package_ok`. Rejected — duplicates lifecycle vocabulary and drifts from GLOSSARY/lifecycle specs.

### 3. Resume advances remaining unfinished worker stages idempotently for one campaign

`POST .../resume` is campaign-scoped (not calendar due-scan). When inspect would report a clear `last_valid_stage` and no ambiguity block:

1. Reject with `manual_intervention_required` when `execution_state=processing` and the claim is not stale.
2. When `execution_state=stale` or stale by clock, reclaim using existing stale/reclaim helpers before continuing.
3. When `location=error`, do not silently requeue; return blocked with `requeue_required` and guidance to use existing requeue helper/endpoint path (explicit operator step). US-031 resume does not redefine requeue-from-error.
4. Otherwise claim/resume from `queued` + `idle`/`stale` as required by queue lifecycle.
5. Advance remaining unfinished Flow A **worker** stages in order, short-circuiting stages whose durable evidence already satisfies the milestone:
   - publish → package → schedule → source lifecycle completion (queued → processed / `flow_a_complete` when eligible)
6. Stop at the first hard failure or ambiguity; return partial progress with clear stage results.
7. Default request MUST NOT enable Git publication, live-site confirmation, or LinkedIn API publish. Those remain separately gated existing capabilities and are out of scope for this recovery change’s default resume path.

Idempotency: reuse existing `already_published`, package idempotency, already-scheduled, and lifecycle completion guards. Resume MUST NOT create a second campaign document, regenerate completed variants, or rewrite confirmed schedule slots.

`dry_run=true` returns the planned `last_valid_stage`, `next_stage`, and per-stage intent (`skip_already_complete` / `would_run` / `blocked`) without mutation.

Alternative considered: resume only the single next stage per call. Deferred as default because operators need predictable catch-up; single-stage-only remains possible later via an optional `stop_after_stage` if implementation needs it — propose optional `stop_after_stage` in the request as an explicit, default-unset control.

Alternative considered: call `execute_due_editorial_calendar_flow_a`. Rejected as primary path — that is calendar due orchestration, not per-campaign recovery.

### 4. Repair is explicit, allowlisted, and fail-closed

`POST .../repair` requires an explicit `repair_action` enum. Initial allowlist:

- `sync_location_from_filesystem` — when Markdown identity resolves to exactly one of `ready|queued|processed|error` and metadata `location` disagrees, update `source_file_status` to the observed location and related path fields; set `recovery_classification` appropriately (`no_action` or retain `retryable` when still incomplete).
- `clear_stale_execution_claim` — when stale by canonical clock/`execution_state=stale`, release/reclaim to `idle` using existing helpers without erasing stage evidence.
- `complete_partial_source_move` — when `physical_move_state=partial` and the remaining sibling move is unambiguous and safe, complete the move and update move evidence.

Repair MUST refuse (stable codes, no mutation) when:

- multiple candidate locations match;
- identity/hash mismatch;
- required to invent `blog_publish` / variants / schedule success;
- would mark `flow_a_complete` without processed consumption evidence;
- active non-stale processing claim blocks safe mutation.

Repair responses MUST summarize before/after safe fields and whether `dry_run` prevented writes.

Alternative considered: automatic repair inside resume. Rejected for US-031 — repair must be explicit so operators see the reconciliation choice (anti silent auto-heal).

### 5. Reuse `recovery_classification`; do not invent US-032 action taxonomy

Inspect/resume/repair responses MUST echo the effective `recovery_classification` using the existing five-value enum (`no_action`, `retryable`, `repair_required`, `requeue_required`, `manual_intervention_required`).

This change MAY set/clear those values when resume/repair legitimately changes operational state (same as queue lifecycle today). It MUST NOT introduce a parallel “recovery action class” vocabulary — that is US-032.

Optional additive response-only fields (not a new attempt ledger): `last_valid_stage`, `next_stage`, `outcome`, `block_reason`, `stages[]` summary. Persisting a dedicated `flow_a_recovery_history` array is deferred to US-032.

### 6. Keep status/alerts and LinkedIn recovery untouched as contracts

No requirement changes to `GET /flow-a/operational-status` request/response behavior or operational-alerts evaluate/report contracts unless a tiny cross-reference is needed for wording. Incomplete-campaign recovery is a separate capability.

LinkedIn failed-variant re-queue / `recovery_confirmation` paths remain owned by `linkedin-retry-recovery-classification` and MUST NOT be the primary recovery surface for Flow A incomplete campaigns.

### 7. Security, path validation, configuration, deployment

- Auth: API key required on all three operations.
- Path confinement: resolve campaign files only under `settings.base_path` / `metadata/campaigns/<campaign_id>.json` and editorial folders already approved by queue lifecycle specs.
- No new env vars required for MVP enablement; reuse existing stale-seconds and base-path settings.
- Deployment: ordinary worker image deploy after implementation approval; this design does not include push/deploy/live validation.
- Rollback: stop calling endpoints / redeploy prior revision; additive routes leave existing pipelines intact.

## Risks / Trade-offs

- **[Risk] Ambiguous historical campaigns with partial metadata** → Mitigation: fail closed with `flow_a_recovery_evidence_ambiguous`; require explicit repair or manual operator fix; never guess durable success.
- **[Risk] Resume chain performs more work than operator expected** → Mitigation: inspect-first workflow; `dry_run`; optional `stop_after_stage`; default excludes Git/live/LinkedIn API.
- **[Risk] Repair allowlist too narrow for real incidents** → Mitigation: document gaps as follow-ups; prefer expanding allowlist in a later change over unsafe generic patching.
- **[Risk] Confusion with LinkedIn publication recovery** → Mitigation: separate routes, specs, and operator docs; responses state Flow A lifecycle recovery scope explicitly.
- **[Risk] Accidental claim of BL-012 completion** → Mitigation: product progress updates only after demonstrated US-031 acceptance; US-032 remains open.

## Migration Plan

1. Implement service + routes + tests behind normal worker release.
2. No campaign schema migration; derivation is read-compatible with existing documents.
3. Operator docs describe inspect → (repair if needed) → resume dry-run → resume.
4. Rollback = previous worker revision; no data rewrite required for rollback of this additive capability.

## Open Questions

1. **Multi-stage vs single-stage default for resume:** Design proposes multi-stage catch-up with optional `stop_after_stage`. Confirm at approval if operators prefer single-next-stage-only as the hard default.
2. **Error-folder campaigns:** Design requires explicit existing requeue before resume (no silent requeue). Confirm that is the desired US-031 boundary vs folding requeue into resume as an explicit `repair_action` / flag.
3. **Calendar item patching:** Should successful resume that reaches lifecycle completion also update a linked calendar item when `campaign_id` matches, or leave calendar reconciliation to existing calendar endpoints? Proposal lean: do not auto-complete calendar in US-031 unless an existing lifecycle-completion path already does so for the invoked service; avoid new calendar mutation rules here.
4. **Persistence of recovery outcomes:** Confirm response-only summaries are enough for US-031 (US-032 owns attempt history persistence).
5. **`distribution_complete` milestone:** Lifecycle lists `distribution_complete` as a state; operational Flow A commonly lands `distribution_scheduled` then lifecycle completion to `flow_a_complete`. Confirm treating `distribution_scheduled` as the durable pre-completion milestone for last-valid-stage (and not requiring `distribution_complete`) matches current implemented reality.
