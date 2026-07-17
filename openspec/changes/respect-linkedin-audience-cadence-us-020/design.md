# Design: respect-linkedin-audience-cadence-us-020

## Context

BL-007 covers scheduled LinkedIn publication execution. US-018 (auto-queue, operationally validated) and US-019 (publication evidence, implemented) are synced into canonical `linkedin-publication-integration`. US-020 asks that due variants are published "once, **in order**" respecting "audience cadence and sequence."

The existing enforcement points:

- **Schedule time** (`linkedin-distribution-scheduling-model`, `linkedin_distribution_schedule.py`): `flow_a_staggered` orders variants by canonical `AUDIENCE_SEQUENCE` (`executive-recruiter` → `engineering-leadership` → `technical-architect` → `short-provocative`), day offsets 0/3/6/9, distinct `scheduled_at_utc`, ≥3 calendar days between consecutive variants.
- **Auto-queue time** (`linkedin_publication_flow.py`, `_auto_queue_skip_reason`): a `pending` variant is due only when `scheduled_at_utc <= now` (unless `publish_now`); supervision exclusions (cancel, defer-not-yet-due) always apply.
- **Publish time** (`_publish_single_variant`): a `queued` variant is published only when `publish_after_utc <= now` (unless `publish_now`) — no ordering or spacing check exists here today.

Both existing gates are **timing** gates. Neither guarantees order or real spacing once schedules have drifted: after downtime or under `publish_now`, multiple `queued` variants of one campaign publish back-to-back, and a manually queued later variant can publish before an earlier one.

## Goals / Non-Goals

**Goals:**

- Enforce US-020 semantics at the only point that cannot be bypassed: the publish evaluation of `queued` variants, in every invocation mode.
- Guarantee a **real** minimum interval of 3 days (72 hours) between successful publications within one campaign, anchored to stored `published_at` evidence (US-019), not to schedule intent.
- Specify blocking vs releasing earlier-variant states, `publish_now` scope, defer interaction, fail-closed evidence behavior, distinct stable reasons, and the US-020 ↔ BL-008 boundary.

**Non-Goals:**

- BL-008 mechanics (retries, recoverable classification, token renewal, timeout duplicate mitigation, attempt history after manual re-queue).
- Changes to US-017 supervision mechanics/endpoints, to `POST /queue-linkedin-publication`'s queue contract, or to the scheduling model spec.
- Global cross-campaign cadence; deploy/n8n activation; story/backlog closure.
- Automatic repair of invalid publication evidence.

## Decisions

### D1 — Enforcement point: publish time, in every mode (not auto-queue-only)

**Analysis.** An auto-queue-only guard was considered and rejected: it governs only `pending` variants entering the combined flow. It cannot protect against (a) variants already `queued` from earlier runs or manual queueing publishing out of order, (b) plain publish-due (`auto_queue_pending` false) bursting a backlog of `queued` variants, or (c) two due `queued` variants publishing seconds apart after accumulated delays. "One variant per request" is also not cadence: an orchestrator invoked hourly would publish one variant per hour.

**Decision.** The guard lives in the publish evaluation of `queued` variants and applies identically in plain publish-due, the combined flow, targeted requests, and the cross-campaign scan. The auto-queue phase keeps a sequence **pre-filter** (`linkedin_publish_auto_queue_skipped_sequence`) purely to avoid queueing variants that could not publish anyway — visibility and churn reduction; the publish-time guard is the normative enforcement. Manual queueing via `POST /queue-linkedin-publication` keeps its contract (it stays a queue authorization), but it no longer functions as an escape hatch to publish out of order: the guard catches the manually queued variant at publish time.

### D2 — Two rules: sequence and real cadence

**Sequence rule.** Variant V of campaign C is not published while an earlier variant E in the canonical sequence is **awaiting publication**: `pending` (including operator-deferred) or `queued` and unpublished. Ordering source is the canonical `AUDIENCE_SEQUENCE` exported by `linkedin_distribution_schedule.py`, restricted to C's variants; non-canonical variant ids (none exist today) order after canonical ones by ascending `scheduled_at_utc`, then variant id, so the ordering is total and deterministic.

**Cadence rule.** V is not published unless every `published` variant of C has `published_at + 72h <= now_utc`. The anchor is stored US-019 evidence — the actual last successful publication — so the interval holds regardless of invocation frequency or how late the schedule ran. A publish completed earlier in the same request counts (the just-written `published_at` is now), so at most one variant per campaign publishes per run as a corollary, not as the primary rule. A campaign with no `published` variants has no cadence constraint (its first publication is gated by sequence and the existing timing gates only).

**Evidence fail-closed.** If any `published` variant of C lacks a parsable `published_at`, the interval cannot be computed. The guard blocks all publication in C with dedicated reason `linkedin_publish_blocked_evidence_invalid` — visible, per variant, without state mutation, without LinkedIn/OAuth calls, and without failing the cross-campaign scan (other campaigns proceed). Silently assuming "old enough" or "too recent" would either break cadence or freeze invisibly; a distinct reason makes the corrupted evidence an explicit operator-actionable signal. Repair is a manual metadata fix outside this capability.

**Rejected alternative — schedule-carried cadence with a one-per-request sequence guard (the earlier draft of this proposal):** rejected because it only bounds catch-up to the orchestration interval (daily, hourly — whatever the caller chooses) rather than guaranteeing 3 real days, and because it left `queued` variants and the plain publish-due path unguarded.

### D3 — Interaction table (blocking vs releasing, normative)

For a candidate variant V of campaign C, each variant E earlier than V in the canonical sequence:

| E's condition | Effect on V | Rationale |
|---|---|---|
| `published` (valid `published_at`) | **Releases** the sequence; E's `published_at` feeds the cadence rule | Sequence satisfied; real spacing still enforced |
| `published` (missing/invalid `published_at`) | **Blocks** V with `linkedin_publish_blocked_evidence_invalid` | Cadence cannot be computed; fail closed and visible |
| `failed` | **Releases** | Never retried automatically (US-019/BL-008); blocking would silently freeze remaining audiences. US-019 failure evidence stays intact. If the operator later manually re-queues E, E is again `queued` and blocks its followers from then on; an inversion relative to already-published followers is the recorded consequence of that manual intervention |
| `cancelled` | **Releases** | Operator removed E from the plan |
| `pending` with US-017 `defer` | **Blocks** V with `linkedin_publish_blocked_sequence` (publish time) / `linkedin_publish_auto_queue_skipped_sequence` (auto-queue pre-filter) | Defer is a deliberate "not yet" for E; publishing followers first would invert the audience sequence the operator is still committed to. Blocking is execution-time only: no sibling `scheduled_at_utc` or supervision metadata is mutated, US-017 mechanics and endpoints are untouched. The chain unblocks when E is published, fails, or is cancelled |
| `pending` (not deferred) | **Blocks** V | E is still ahead in the chain |
| `queued` unpublished (auto- or manually queued, this run or earlier) | **Blocks** V | E is authorized but unpublished; publishing V first would invert the sequence |

**Ordering guarantee, stated precisely.** The guard does NOT claim unconditional strict canonical publication order — `failed`/`cancelled` release the chain, and a manual re-queue after followers published can produce an inversion. The normative guarantee is: **a later variant never publishes while an earlier variant is awaiting publication**, and successful publications are ≥72 hours apart per campaign.

**`publish_now` scope.** `publish_now` bypasses only the ordinary timing gates (`scheduled_at_utc` due gate at auto-queue; `publish_after_utc` at publish), exactly as today. It bypasses neither the sequence rule, nor the cadence rule, nor the evidence rule, nor supervision exclusions, nor a deferred time — consistent with the established precedent that `publish_now` never bypasses supervision. There is no escape hatch for out-of-order or early publication in this capability; if one is ever needed it requires a new OpenSpec change.

**Reason precedence.** Existing evaluation is preserved bit-for-bit up to the guard: auto-queue reports `…skipped_state` / `…skipped_supervision` / `…skipped_not_due` exactly as today with the sequence pre-filter last; the publish phase keeps already-published idempotency, `…variant_not_queued`, and `…variant_not_due` first, then evaluates sequence → evidence → cadence. Existing US-018/US-019 tests therefore keep their reasons unchanged.

### D4 — Per-campaign scope in the cross-campaign scan

Sequence and cadence are evaluated per campaign document. In the bounded cross-campaign scan, each eligible `distribution_scheduled` Flow A campaign has an independent chain and cadence clock; campaign A's blocks, publications, or corrupted evidence never affect campaign B. Blocked variants never fail the overall operation. No global cadence is introduced (BL-020/BL-021 territory).

### D5 — US-020 ↔ BL-008 boundary

US-020 governs ordering/cadence of publication execution over the existing state machine. Explicitly BL-008 (excluded here and named in the delta): recoverable/non-recoverable classification, retry limits and automatic re-queue, token-renewal behavior on failure, duplicate prevention after timeouts/uncertain outcomes, and attempt-history/evidence semantics after manual re-queue. "Failed releases the chain" takes no position on whether/when a failed variant should be retried — it only refuses to let an unretried failure freeze sibling audiences. If BL-008 later introduces automatic retry, the blocking set may need revisiting via a new change.

## Risks / Trade-offs

- [A deferred earlier variant freezes the rest of its campaign] → Intentional per US-020: defer means "this audience goes later, order preserved." The block is visible per variant with a stable reason; the operator releases it by publishing, cancelling, or letting the deferred variant come due. US-017 metadata is never touched.
- [Campaign-wide `publish_now` catch-up now takes ≥3 days per remaining variant] → Intentional: `publish_now` is a timing override, not a saturation override. US-018's validated single-variant scenarios are unaffected; existing tests must pass unmodified — verified in tasks.
- [Manually queued variants can sit `queued` and blocked] → Correct behavior: queue is authorization, publish-time guard decides order/spacing. Visible via `linkedin_publish_blocked_sequence` / `…_cadence` on every publish-due evaluation.
- [Corrupted `published_at` halts a campaign] → Fail-closed by design with a dedicated visible reason; scoped to that campaign only; repair is a deliberate manual metadata fix rather than a silent guess.
- [Hand-edited metadata with non-canonical variant ids] → Deterministic fallback ordering; worst case a variant is blocked with a visible stable reason, never wrongly published.

## Migration Plan

No deployment in this change (implemented, not deployed — local build only until an approved deploy). No metadata migration: the guard reads existing fields (`publish_state`, `published_at`, `scheduled_at_utc`, `operator_supervision.last_action`) and writes nothing new. Rollback = revert the code change; no stored state depends on it.

## Open Questions

None — enforcement point, both rules, blocking/releasing states, `publish_now` scope, defer interaction, evidence fail-closed behavior, per-campaign scope, and the BL-008 boundary are resolved above.
