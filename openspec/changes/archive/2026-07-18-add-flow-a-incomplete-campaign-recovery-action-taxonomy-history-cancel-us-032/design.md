## Context

BL-012 / US-032 builds on the implemented US-031 incomplete-campaign recovery surface:

- Authenticated `GET .../{campaign_id}`, `POST .../resume`, `POST .../repair`
- Derived `last_valid_stage` from durable campaign evidence
- Canonical `recovery_classification` five-value enum from `flow-a-operational-queue-lifecycle`
- Operator-visible response outcomes that are **not** yet persisted as a dedicated recovery attempt ledger

Product intent (US-032): classify recovery **actions**, preserve attempt **history**, and support safe **cancellation** when recovery is not appropriate — without reopening US-031 stage derivation or LinkedIn publication recovery (BL-008).

Constraints: ADR-0001 (n8n → worker HTTP only), path confinement under configured editorial base, secret-safe payloads, fail closed on ambiguity, no Git / live-site / LinkedIn API / deploy as part of this change. Prefer additive fields and endpoints over breaking US-031 contracts.

## Goals / Non-Goals

**Goals:**

- Define a stable operator-facing recovery-action taxonomy that complements (does not replace) `recovery_classification`.
- Persist a bounded, durable recovery attempt ledger on campaign metadata for applied mutating recovery operations.
- Add authenticated cancel with idempotent semantics; gate subsequent resume/repair when cancelled.
- Keep inspect read-only for editorial/stage evidence; enrich inspect responses with taxonomy, cancel state, and recent attempt history.
- Preserve confirmed durable stage evidence under all cancel and history-write paths.

**Non-Goals:**

- Changing US-031 last-valid-stage algorithm, repair allowlist, or default resume stage chain (except post-cancel gating and additive response/ledger fields).
- Parallel queue ontology or new `recovery_classification` values.
- Separate metadata store / database for attempt history (MVP stays in campaign JSON).
- Auto-cancel by age, LinkedIn variant cancel, reopen-from-cancel (unless explicitly approved later).
- Marking US-032 accepted or BL-012 closed from design alone.

## Decisions

### 1. Recovery-action taxonomy complements `recovery_classification`

Introduce an operator-facing enum `recommended_recovery_action` (response field) and `executed_recovery_action` (ledger / mutating response field). These are **not** queue states and MUST NOT be written into `source_file_status.recovery_classification`.

**Recommended action values** (exact closed set for this change):

| Value | Meaning |
|-------|---------|
| `noop_already_complete` | Consistent `flow_a_complete` / no unfinished worker recovery work |
| `resume` | Unfinished worker stages; resume is appropriate |
| `repair` | Ambiguous or inconsistent metadata; allowlisted repair first |
| `requeue` | `location=error` (or equivalent); explicit requeue required before resume |
| `manual_intervention` | Active claim / severe block; operator must intervene outside auto resume |
| `cancel_recovery` | Recovery is no longer appropriate (shown when already cancelled, or as an available operator choice alongside other recommendations when incomplete) |

Mapping rules (deterministic; classification remains authoritative for queue condition):

- If recovery cancel state is active → `recommended_recovery_action=cancel_recovery` (and resume/repair blocked).
- Else if last-valid is consistent `flow_a_complete` → `noop_already_complete`.
- Else if `recovery_classification=requeue_required` or `location=error` → `requeue`.
- Else if `recovery_classification=repair_required` or inspect outcome is evidence-ambiguous → `repair`.
- Else if `recovery_classification=manual_intervention_required` or non-stale processing claim → `manual_intervention`.
- Else if unfinished worker stages remain and classification is `retryable` or `no_action` → `resume`.
- Else → `manual_intervention` (fail closed rather than invent a new class).

**Executed action values** on ledger / mutating responses: `resume`, `repair`, `cancel` (plus `noop` when cancel/resume is an idempotent no-op). Inspect does not write executed actions.

Alternatives considered:

- Encode actions as new `recovery_classification` values — **rejected** (would invent parallel/overlapping queue ontology; US-031 / queue lifecycle forbid this).
- Free-form action strings — **rejected** (unstable for operators and tests).

### 2. Persist attempt history on campaign metadata (not a separate store)

Store ledger under campaign document:

```text
flow_a_recovery:
  cancelled: bool
  cancelled_at: UTC ISO-8601 | null
  cancel_reason_code: string | null
  cancel_summary: short string | null
  attempts: [ RecoveryAttempt, ... ]   # append-only, newest last
```

Each `RecoveryAttempt` (secret-safe fields only):

- `attempt_id` (stable UUID string)
- `recorded_at` (UTC)
- `operation` — `resume` | `repair` | `cancel`
- `executed_recovery_action` — taxonomy value used for the attempt
- `dry_run` — always `false` for persisted entries (see Decision 3)
- `outcome` — `ok` | `blocked` | `failed` | `noop` | `partial`
- `reason_code` (stable machine code when blocked/failed/noop)
- `summary` (short operator text)
- `last_valid_stage` (when known)
- `recovery_classification` (effective value at attempt time)
- `repair_action` (only for repair operations)
- `request_id` / correlation id optional if already available in worker patterns

**Retention / size bounds:**

- Hard cap: **50** attempts per campaign.
- When appending would exceed the cap: **drop oldest** entries (FIFO trim) rather than failing the recovery operation — operators need cancel/resume to succeed; history is audit-assistive, not a hard gate.
- Inspect returns at most the **20 most recent** attempts by default (full array may remain on disk up to 50). No pagination endpoint in this change.

**Why campaign metadata vs `metadata/runs/` or a new folder:** recovery is campaign-scoped; atomic update already exists for campaign writes; avoids a second identity join. Separate store deferred if campaign JSON size becomes an operational problem (follow-up).

**Relation to `state_history`:** ledger is distinct. Cancel/history MUST NOT append fake lifecycle transitions or rewrite `state_history` to invent milestones.

Alternatives considered:

- Response-only history (US-031 style) — **rejected** (fails US-032 “preserve attempt history”).
- Append to `state_history` — **rejected** (conflates pipeline transitions with operator recovery attempts).
- Fail when ledger full — **rejected** for cancel safety; trim-oldest preferred.

### 3. Dry-run does not persist ledger or cancel state

`dry_run=true` on resume / repair / cancel MUST return the planned taxonomy and would-be attempt summary **without** writing `flow_a_recovery` (no ledger append, no cancel flag change). Applied (`dry_run=false`) mutating calls that complete their control path (including blocked/noop outcomes that still represent an operator attempt) MUST append one ledger entry.

Blocked-before-auth or HTTP 401/422 validation failures MUST NOT write ledger entries.

Alternative considered: persist dry-run audits — deferred; would inflate ledger and blur “attempted recovery” semantics.

### 4. Cancellation is a new authenticated endpoint

Add:

`POST /flow-a/incomplete-campaign-recovery/cancel`

Body:

- `campaign_id` (required)
- `dry_run` (boolean, default `false`)
- `reason_code` (optional short stable token; default `operator_cancelled`)
- `summary` (optional short operator text; truncated/sanitized)

Auth: `Depends(require_api_key)`. Path confinement same as US-031. No client absolute paths. No stage side effects.

**Semantics — what becomes cancelled:**

- Incomplete-campaign **recovery eligibility** for this campaign (`flow_a_recovery.cancelled=true`).
- NOT LinkedIn variant publication, NOT calendar items, NOT editorial folder moves, NOT pipeline `state`.

**Immutable under cancel:**

- Confirmed `blog_publish` / package / schedule evidence
- Existing `state` and `state_history`
- Source file bytes and locations (cancel does not move files)

**Who can cancel:** any client with valid worker API key (same trust model as resume/repair). No separate RBAC in this change.

**Idempotency:** if already cancelled, return `outcome=noop` with clear summary; still may append a ledger entry noting noop cancel **or** skip duplicate noop ledger spam — **decision: skip ledger append on idempotent already-cancelled cancel** to avoid noise; response still shows cancel state. First successful cancel appends one `cancel` attempt.

**Post-cancel gating:** resume and repair MUST fail closed with `outcome=blocked`, `reason_code=flow_a_recovery_cancelled`, `recommended_recovery_action=cancel_recovery`, and MUST NOT run stage side effects or repair mutations. Inspect remains allowed and MUST show cancel state + history.

**`recovery_classification` on cancel:** do **not** invent a sixth classification value. Leave existing classification unchanged unless it is unset/`no_action` while campaign is still incomplete — then MAY set `manual_intervention_required` to reflect that automated recovery is intentionally stopped. Prefer **leave classification unchanged** as default to avoid surprising queue/status consumers; expose cancel via `flow_a_recovery.cancelled` and taxonomy instead.

**Reopen:** out of scope for US-032 (no uncancel endpoint). Document as follow-up if operators need it.

Alternatives considered:

- `repair_action=cancel_recovery` — **rejected** (cancel is not metadata repair; pollutes repair allowlist).
- `resume` mode flag `cancel=true` — **rejected** (confusing; mixes advance-with-stop intents).
- Soft-delete campaign — **rejected** (destroys/hides evidence; violates preserve-completed-work).

### 5. Additive response fields; no breaking US-031 contracts

Existing inspect / resume / repair JSON fields remain. Add:

- `recommended_recovery_action`
- `executed_recovery_action` (mutating responses)
- `recovery_cancel` object (`cancelled`, `cancelled_at`, `reason_code`, `summary`)
- `recovery_attempts` (recent attempts array for inspect; single `attempt` echo on mutating applied responses)

### 6. Security, HTTP boundary, configuration, deployment

- Auth on cancel identical to US-031 routes.
- Secret-safe: no Markdown bodies, tokens, absolute base paths, provider payloads in ledger or responses.
- No new env vars required for MVP (bounds are code constants; optional later config deferred).
- Deploy: ordinary worker image after implementation approval; not part of this propose step.
- Rollback: prior worker revision; leftover `flow_a_recovery` keys are inert if unread.

### 7. Keep status/alerts and LinkedIn recovery intact

No requirement changes to operational-status or operational-alerts contracts. LinkedIn publication recovery remains owned by `linkedin-retry-recovery-classification`. Incomplete-campaign cancel MUST NOT call LinkedIn cancel-publication endpoints.

## Risks / Trade-offs

- **[Risk] Operators confuse recovery cancel with LinkedIn variant cancel** → Mitigation: distinct routes, field names (`flow_a_recovery`), operator docs, response summaries stating “incomplete-campaign recovery cancelled.”
- **[Risk] Ledger trim drops forensic detail** → Mitigation: 50-cap FIFO; document bound; follow-up external archive if needed.
- **[Risk] Leaving `recovery_classification` unchanged after cancel confuses status UIs** → Mitigation: taxonomy + `recovery_cancel` on inspect; optional follow-up to surface cancel in status without new enum values.
- **[Risk] No reopen path traps operators** → Mitigation: document as known non-goal; metadata remains; manual JSON edit is last resort and out of scope; reopen as later change if demanded.
- **[Risk] Accidental claim of BL-012 completion** → Mitigation: progress checklist updates only after demonstrated US-032 acceptance criteria; BL-012 stays open until both stories accepted.

## Migration Plan

1. Implement additive metadata schema + cancel route + taxonomy/history on existing recovery module.
2. No migration job: missing `flow_a_recovery` means not cancelled and empty attempts.
3. Operator docs: inspect → classify action → (repair|requeue|resume) or cancel; history visible on inspect.
4. Rollback = previous worker revision; additive keys harmless.

## Open Questions

1. **Reopen-from-cancel:** Confirm out of scope for US-032 (design assumes yes).
2. **Classification mutation on cancel:** Confirm default “leave `recovery_classification` unchanged” vs set `manual_intervention_required`.
3. **Idempotent cancel ledger:** Confirm skip append on already-cancelled cancel (design assumes yes).
4. **Inspect returning attempts:** Confirm default window of 20 most recent (design assumes yes).
