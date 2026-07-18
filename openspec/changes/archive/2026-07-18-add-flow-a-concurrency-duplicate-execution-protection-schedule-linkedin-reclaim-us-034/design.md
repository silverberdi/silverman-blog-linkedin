## Context

BL-013 / US-034 asks the worker to ensure simultaneous or repeated Flow A triggers cannot create **duplicate distribution schedules** or **duplicate LinkedIn API publications**, and that **abandoned processing claims** can be recovered via stale detect + reclaim with operator-visible outcomes. US-033 (accepted for fixture evidence; not live-deploy validated) already covers claim CAS, ComfyUI skip/reuse, and blog handoff idempotency. US-035 (restart validation) remains out of scope.

Current evidence (`docs/CURRENT-STATE.md`, `src/`, `tests/`):

| Surface | Existing contract | Gap for US-034 |
|---------|-------------------|----------------|
| Scheduling | Sequential idempotency via schedule-level key; matching → completed without duplicate `state_history`; mismatch → `linkedin_schedule_metadata_mismatch` | First-time schedule apply uses non-CAS `write_campaign_metadata`; two overlapping schedule calls can both observe `derivatives_generated` and both transition/write |
| LinkedIn publish | `publish_state=published` + URN → `linkedin_publish_already_published` (no API call); BL-008 covers uncertain/timeout recovery | Concurrent first publish of the same queued variant can race before URN evidence is durable; need explicit once-only under contention without reworking BL-008 |
| Abandoned claims | `detect_stale_flow_a_execution`, claim reclaim from `stale` with `reclaimed_from_stale`, TTL via `SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS` | Helpers and unit tests exist, but US-034 requires reclaim as a **story deliverable** with clear operator-visible detect / reclaim / blocked outcomes under the concurrency capability |

Orchestration-side single-flight remains complementary. Per ADR-0001, the **worker** MUST remain safe if overlapping HTTP calls occur.

Constraints: reuse claim / stale / reclaim / schedule idempotency / LinkedIn once-only vocabulary; no parallel queue ontology; fail closed on ambiguity; secret-safe responses; preserve US-033, BL-012, and BL-008 contracts; no Git push / live-site / deploy / production n8n activation; no US-035.

## Goals / Non-Goals

**Goals:**

- Satisfy US-034 acceptance criteria on the worker HTTP surface.
- Close schedule first-write races with CAS (or equivalent) patterned after US-033 claim metadata protection.
- Keep LinkedIn once-only publish durable under concurrent/repeated publish-due / queue paths using existing URN evidence and `linkedin_publish_already_published`.
- Make stale detect + reclaim a demonstrated, operator-visible US-034 deliverable without new execution states.
- Prefer existing endpoints and helpers; no new primary HTTP routes unless apply-time inspection proves an unavoidable gap.
- Leave US-033, BL-012, and BL-008 intact except narrow shared CAS helper reuse.

**Non-Goals:**

- Re-implementing or reshaping US-033 post / image / blog protections.
- US-035 restart validation evidence.
- Global campaign-metadata locking for unrelated writers.
- New lifecycle states, new folders, or a second claim ontology.
- Changing BL-008 uncertain-outcome / recovery confirmation semantics.
- Marking US-034 accepted or BL-013 closed from proposal/code alone.

## Decisions

### 1. No new primary endpoints — harden schedule, LinkedIn publish, and claim/stale/reclaim paths

US-034 is enforced on:

- `schedule_linkedin_distribution` / `POST /schedule-linkedin-distribution` (`linkedin_distribution_schedule.py`)
- LinkedIn queue / publish-due services and HTTP routes (`linkedin_publication_flow.py` and related)
- `detect_stale_flow_a_execution` / `claim_flow_a_execution` reclaim path (`flow_a_operational_queue.py`) and callers that surface outcomes (connector, operational status, recovery resume as consumers — not new APIs)

Alternatives considered:

- New `/flow-a/reclaim-*` or `/concurrency-*` diagnostic endpoint: rejected — acceptance criteria are prevention and reclaim outcomes on existing vocabulary; operational-status and claim results already can surface state.
- n8n-only single-flight: rejected — worker must fail closed under overlapping HTTP (ADR-0001).

### 2. Duplicate scheduling = existing idempotency + CAS on first-time schedule apply

Preserve sequential rules:

- Matching schedule idempotency proof on `distribution_scheduled` → completed, no duplicate history, no rewrite of `scheduled_at_utc`.
- Mismatch → `linkedin_schedule_metadata_mismatch`.

Harden first-time apply (`derivatives_generated` → `distribution_scheduled`):

1. Read campaign metadata and record content fingerprint (reuse `campaign_metadata_content_fingerprint` / `write_campaign_metadata_cas` from US-033).
2. Decide eligibility and compute schedule.
3. Persist transition + schedule metadata only if fingerprint still matches; on concurrent update, re-read and either return completed idempotent outcome (peer already scheduled with matching proof) or fail closed (`linkedin_schedule_metadata_mismatch` or already-scheduled completed — prefer existing codes; do not invent a second operator-facing ontology unless tests require distinguishing transient CAS exhaustion).

Under concurrent first schedule attempts: at most one successful transition/write; losers must short-circuit as completed idempotent or fail closed without a second schedule set or duplicate `state_history` entry for the same identity.

Alternatives considered:

- Process-wide lock only: insufficient across worker processes/containers.
- Defer race closing: rejected — duplicate scheduling is explicitly US-034.

### 3. Duplicate LinkedIn publication = existing once-only + contention-safe evidence check

Preserve and scenario-test:

- Already `published` with stored `linkedin_post_urn` → no LinkedIn API call; `linkedin_publish_already_published`; URN/`published_at` preserved (including `publish_now` and `auto_queue_pending`).
- Enablement / OAuth / dry-run guards remain fail-closed without marking `failed` incorrectly.
- BL-008 uncertain / absence-verified recovery remains the authority for post-timeout duplicate risk — US-034 MUST NOT redefine that taxonomy.

Harden concurrent first publish for the same variant:

1. Immediately before the LinkedIn API call, re-read variant publication evidence; if already published with URN, short-circuit as already-published.
2. Persist successful publish evidence with CAS (or equivalent atomic write) so two overlapping successes cannot both leave distinct URNs / double API success paths without detection.
3. If a peer already wrote URN evidence between API success and local persist, prefer fail-closed retention of the durable peer evidence over inventing a second published identity (do not call LinkedIn again; do not clear peer URN). Exact tie-break: keep first durable on-disk URN evidence; surface a stable operator-visible conflict/already-published outcome without secret leakage.

Dry-run paths MUST NOT mutate publication state or call LinkedIn.

Alternatives considered:

- Variant-level lock store separate from campaign metadata: deferred — campaign CAS + pre-API re-check is smallest coherent fix; revisit only if tests prove dual API calls after CAS.
- Treating all concurrent publish races as BL-008 uncertain: rejected for the clear already-published and first-success durable-evidence cases; BL-008 remains for true uncertain API outcomes.

### 4. Abandoned-claim recovery = existing stale detect + reclaim as US-034 deliverable

Do **not** invent new states. Reuse:

- Stale when `execution_state=processing` and `now >= last_progress_at + SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS`.
- `detect_stale_flow_a_execution` → `execution_state=stale`, `recovery_classification=retryable`, no file moves.
- Reclaim via `claim_flow_a_execution` from `stale` (or detect-then-claim) → new `execution_attempt_id`, `reclaimed_from_stale=true` semantics.
- Non-stale active claim → `flow_a_execution_already_claimed` + `manual_intervention_required`.

US-034 deliverable focus:

- Operator-visible outcomes for detect completed / skipped (not yet stale) / failed.
- Operator-visible reclaim completed vs already-claimed block.
- Reclaim MUST resume using existing campaign evidence and completed-stage markers (no duplicate schedule slots, no duplicate LinkedIn publish when evidence already exists — inherits Decisions 2–3 and US-033).
- Prefer CAS for stale-mark writes if apply-time races on detect are demonstrated; otherwise document sequential detect + claim CAS (already present) as sufficient.

Alternatives considered:

- Auto-reclaim cron inside worker: out of scope — deliver reclaim semantics and visibility; orchestration may call helpers later; no production n8n activation here.
- Clearing claims without stale TTL: rejected — would break US-033 non-stale protection.

### 5. Operator-visible outcomes and fail-closed communication

Every US-034 contention, idempotent-complete, or reclaim path MUST surface:

- Stable codes/status: schedule completed vs `linkedin_schedule_metadata_mismatch`; `linkedin_publish_already_published`; `flow_a_execution_already_claimed`; stale detect completed/skipped; reclaim `reclaimed_from_stale` when applicable.
- `recovery_classification` where claim/stale vocabulary already requires it.
- Secret-safe JSON only (no tokens, absolute base paths, Markdown/draft bodies, raw provider payloads).

Prefer clarifying existing result fields over new response schemas.

### 6. Preserve US-033, BL-012, and BL-008; docs/status only after demonstration

- Do not weaken claim CAS, image skip, or blog `already_published` / `blog_publish_target_exists`.
- Incomplete-campaign recovery resume continues to respect non-stale claim rejection and may reclaim when stale per existing rules.
- LinkedIn publication recovery confirmation / uncertain classification unchanged.
- Update CURRENT-STATE after demonstrated implementation; keep US-033 accepted; leave US-035 and BL-013 open; do not mark US-034 accepted from code alone.

## Risks / Trade-offs

- **[Risk] Schedule CAS changes first-write timing under load** → Mitigation: bounded CAS retry loop mirroring claim; fail closed to mismatch/already-scheduled rather than partial writes.
- **[Risk] LinkedIn API called twice before either URN is durable** → Mitigation: pre-API evidence re-check + CAS persist; if dual API success is still possible under extreme races, retain first durable URN and fail closed on conflicting second persist; BL-008 remains for uncertain outcomes without URN.
- **[Risk] Aggressive stale reclaim duplicates downstream work** → Mitigation: reclaim inherits schedule/LinkedIn/blog idempotency; tests must prove no duplicate schedule slots or LinkedIn posts when evidence exists.
- **[Risk] Scope creep into US-035 restart semantics** → Mitigation: explicit non-goal; no restart/crash-recovery scenarios in this change’s acceptance tests beyond stale TTL reclaim.
- **[Trade-off] Reusing campaign-level CAS vs finer-grained locks** → Accept campaign CAS for smallest coherent diff aligned with US-033; document if apply finds hot-spot contention.

## Migration Plan

1. Implement behind existing endpoints/helpers; no schema migration of campaign JSON required beyond optional additive operator-visible fields if design requires them.
2. Ship automated concurrent/repeated-trigger tests for schedule, LinkedIn once-only, and stale detect/reclaim.
3. Update CURRENT-STATE to “implemented / automated-tested” only after tests pass; product story acceptance remains a separate operator/validation step.
4. Deploy only with explicit user approval (not part of this change’s definition of done).
5. Rollback: revert worker image/commit; on-disk campaign documents remain compatible with prior readers because no new required lifecycle states are introduced.

## Open Questions

- Whether stale **detect** writes need CAS in addition to claim reclaim CAS — resolve at apply time with a focused race test; default to adding CAS only if a demonstrated detect race exists.
- Whether a distinct stable code is needed for schedule CAS contention vs `linkedin_schedule_metadata_mismatch` — prefer reusing existing codes unless operator clarity requires one additive code mapped to the same fail-closed guidance.
