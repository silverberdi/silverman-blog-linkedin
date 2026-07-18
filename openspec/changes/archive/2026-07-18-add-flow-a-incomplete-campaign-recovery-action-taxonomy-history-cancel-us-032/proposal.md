## Why

BL-012 / US-032 requires operators to classify recovery actions, preserve attempt history, and safely cancel recovery when it is not appropriate. US-031 already delivers authenticated inspect / resume / repair with last-valid-stage derivation and the canonical five-value `recovery_classification` enum, but outcomes are response-only today: there is no durable attempt ledger, no operator-facing action taxonomy complementary to queue classification, and no fail-closed cancel path that stops further recovery without inventing stage success.

## What Changes

- Extend the existing `flow-a-incomplete-campaign-recovery` HTTP surface (additive, non-breaking) so inspect returns an operator-facing **recovery-action taxonomy** derived from persisted evidence and `recovery_classification`, without inventing a parallel queue ontology.
- Persist a durable **recovery attempt ledger** on campaign metadata for inspect / resume / repair / cancel outcomes (including dry-run vs applied, blocked/failed/noop), with retention/size bounds and secret-safe fields only.
- Add authenticated **safe cancellation** so operators can mark incomplete-campaign recovery as not appropriate; subsequent resume/repair fail closed with a clear code while confirmed durable stage evidence remains immutable.
- Keep inspect read-only except that mutating operations (resume / repair / cancel) append ledger entries; dry-run mutating calls MUST NOT write ledger or campaign recovery-cancel flags unless design explicitly records a non-mutating dry-run audit entry (default: dry-run does not persist).
- Update CURRENT-STATE / operator docs / product progress only to the demonstrated implementation level; do not mark US-032 accepted or BL-012 closed from proposal or code alone.

## Goals

- Satisfy US-032 acceptance criteria: classify recovery actions; preserve attempt history; support safe cancellation; make outcomes visible; communicate failures/blocks clearly; avoid duplicating or unintentionally changing completed work.
- Prefer additive fields and one new cancel endpoint over **BREAKING** changes to US-031 inspect / resume / repair contracts.
- Reuse US-031 recovery routes and canonical `recovery_classification`; action taxonomy complements classification rather than replacing it.
- Fail closed: cancellation and history writes MUST NOT invent durable stage success or rewrite confirmed publish / package / schedule / lifecycle evidence.
- Keep ADR-0001 (n8n → worker HTTP only); no Execute Command.

## Non-goals

- Re-implementing US-031 last-valid-stage, resume short-circuits, or repair allowlist behavior (reuse as-is; extend only where needed for taxonomy, history, cancel).
- Changing `GET /flow-a/operational-status`, operational-alerts evaluate/report, or LinkedIn publication recovery (BL-008 / US-021–US-022) contracts.
- BL-013 concurrency hardening, BL-014 backup/restore, BL-015 UI/console.
- LinkedIn API publish, Git push, live-site mutation, deploy, or production n8n activation.
- Closing BL-012 or marking US-032 accepted from proposal/code alone.
- Cancelling LinkedIn variant publication / supervision overrides (distinct from incomplete-campaign recovery cancel).
- Silent auto-heal or automatic cancel based on age alone.

## Acceptance Criteria Coverage

- **Classify recovery actions:** inspect (and mutating responses) expose a stable `recommended_recovery_action` / executed-action taxonomy mapped from evidence + `recovery_classification`, not a second queue state machine.
- **Preserve attempt history:** each applied resume / repair / cancel (and optionally applied inspect is excluded — inspect stays read-only) appends a durable ledger entry readable on subsequent inspect.
- **Support safe cancellation when recovery is not appropriate:** authenticated cancel marks recovery cancelled; resume/repair thereafter blocked with a clear code; durable stage evidence unchanged.
- **Visible and understandable outcome:** structured JSON includes action taxonomy, ledger summary / recent attempts, cancel state, and existing US-031 outcome fields.
- **Failures or blocked states clearly communicated:** stable codes for already cancelled, ledger bounds exceeded, auth/validation failure, and existing US-031 blocks.
- **Existing completed work not duplicated or unintentionally changed:** cancel and history MUST NOT rewrite confirmed milestones; resume/repair remain idempotent short-circuiting as in US-031.

No US-031 acceptance criteria are reopened by this change except additive response fields and post-cancel gating of resume/repair.

## Capabilities

### New Capabilities

- (none) — US-032 extends the existing incomplete-campaign recovery capability rather than introducing a separate capability name.

### Modified Capabilities

- `flow-a-incomplete-campaign-recovery`: Add recovery-action taxonomy on inspect/mutating responses; durable recovery attempt ledger with bounds; authenticated cancel endpoint and cancel-state gating for resume/repair; update purpose/scope to include US-032 (remove US-032-out-of-scope wording from the capability purpose).
- `flow-a-operational-queue-lifecycle`: Narrow alignment so cancel/history reuse `recovery_classification` and do not invent parallel queue ontology values; clarify that recovery-action taxonomy is complementary operator vocabulary, not a replacement for `source_file_status.recovery_classification`.
- `flow-a-lifecycle`: Narrow clarification that recovery attempt ledger entries are distinct from pipeline `state_history` and MUST NOT be used to invent lifecycle transitions or durable stage success.

## Impact

- **API:** additive fields on existing inspect / resume / repair responses; new authenticated `POST /flow-a/incomplete-campaign-recovery/cancel` (dry-run supported). No breaking removal of US-031 fields.
- **Worker:** extend `flow_a_incomplete_campaign_recovery` service + routes; append-only ledger writes on applied mutating recovery operations; cancel flag gating.
- **Data:** additive campaign metadata fields under `metadata/campaigns/<campaign_id>.json` (recovery attempt ledger + cancel state); no new lifecycle states; no separate metadata store for MVP.
- **n8n:** may call cancel/history-enriched endpoints over HTTP later; no production workflow ship/activation in this change.
- **Tests and docs:** behavioral tests for taxonomy mapping, ledger append/bounds, cancel idempotency, post-cancel resume/repair blocks, dry-run non-persistence, secret-safe payloads; operator doc + CURRENT-STATE updates after demonstrated implementation.
- **Out of scope systems:** operational-status/alerts and LinkedIn publication recovery remain intact; no Git/live/LinkedIn API mutation.
