## Context

BL-013 / US-035 asks the worker to **validate behavior during restarts** so mid-flight worker/process interruption does not create duplicate artifacts or external publications when work resumes. US-033 (accepted for fixture evidence) covers claim CAS, ComfyUI skip/reuse, and blog handoff idempotency. US-034 (accepted for fixture evidence) covers schedule first-write CAS, LinkedIn once-only URN evidence, and stale detect + reclaim. Neither story treated process restart / crash-recovery as its deliverable.

Current evidence (`docs/CURRENT-STATE.md`, `src/`, `tests/`):

| Surface | After mid-flight crash | Gap for US-035 |
|---------|------------------------|----------------|
| Claim left `processing` | No startup auto-clear; stays `processing` until TTL stale or allowlisted BL-012 repair | Need explicit restart scenarios proving pre-TTL block + post-TTL reclaim are operator-visible and non-duplicating |
| Image / blog / schedule / LinkedIn | Durable stage evidence + US-033/US-034 idempotency | Need fixtures that interrupt mid-stage, then reclaim/resume without second ComfyUI call, second checkout apply, second schedule set, or second LinkedIn API post when evidence exists |
| LinkedIn mid-API | BL-008 uncertain / confirmation taxonomy | Must remain BL-008-owned — restart validation must not auto-republish |
| BL-012 recovery | Inspect/resume/repair/cancel already block non-stale claims and reclaim when stale | Must be exercised under restart fixtures without contract changes |
| Tests | `tests/test_flow_a_concurrency_us033.py`, `us034.py`, incomplete-campaign recovery | No dedicated restart/crash interruption suite |

Orchestration-side n8n idle restart (other stories) is complementary and does **not** satisfy worker mid-pipeline crash validation. Per ADR-0001, the **worker** MUST remain safe if overlapping HTTP calls occur after restart.

Constraints: reuse claim / stale / reclaim / BL-012 / stage-idempotency vocabulary; no parallel queue ontology; fail closed on ambiguity; secret-safe responses; preserve US-033, US-034, BL-012, and BL-008; no Git push / live-site / deploy / production n8n activation; no new primary endpoints unless unavoidable.

## Goals / Non-Goals

**Goals:**

- Satisfy US-035 acceptance criteria on the worker HTTP / helper surface with automated restart-interruption evidence.
- Prove mid-flight interruption + post-restart re-entry does not duplicate claim, image, blog, schedule, or LinkedIn side effects when durable evidence exists.
- Keep pre-TTL stuck `processing` blocked (`flow_a_execution_already_claimed` / BL-012 active-claim codes + `manual_intervention_required`).
- Reuse US-034 stale detect + reclaim as the clock-based recovery path after interruption (same vocabulary; not a second reclaim mechanism).
- Prefer existing endpoints and helpers; leave US-033/US-034 intact except narrow shared dependencies for fixtures.

**Non-Goals:**

- Auto-clear non-stale `processing` on worker/process/Docker start.
- Auto LinkedIn API republish after mid-publish crash.
- Re-implementing US-033/US-034 protections as new deliverables.
- New lifecycle states, new folders, new primary HTTP routes, or a parallel claim ontology.
- Changing BL-012 last-valid-stage / repair allowlist / cancel contracts.
- Changing BL-008 uncertain-outcome taxonomy.
- Marking US-035 accepted or BL-013 closed from proposal/code alone; do not un-accept US-033/US-034.

## Decisions

### 1. No new primary endpoints — validate existing claim, stage, reclaim, and recovery paths

US-035 is enforced and evidenced on:

- `claim_flow_a_execution` / `detect_stale_flow_a_execution` / `record_flow_a_progress` / `release_flow_a_execution` (`flow_a_operational_queue.py`)
- Mid-pipeline orchestration (`editorial_calendar_flow_a_execute.py` and related publish → package → schedule path)
- Blog handoff (`publish_blog_post` / `blog_publish_flow.py`)
- Schedule (`schedule_linkedin_distribution` / `linkedin_distribution_schedule.py`)
- LinkedIn queue / publish-due (`linkedin_publication_flow.py`) — for already-published / once-only and BL-008 uncertain boundaries only
- Incomplete-campaign recovery inspect / resume / repair (`flow_a_incomplete_campaign_recovery.py`)
- Operator visibility via existing operational-status / recovery response fields

Alternatives considered:

- New `/flow-a/restart-*` or startup reclaim endpoint: rejected — acceptance criteria are restart-safe behavior on existing vocabulary; startup auto-clear would bypass non-stale claim protection.
- n8n-only restart evidence: rejected — worker mid-flight crash is the US-035 target (ADR-0001).

### 2. Restart contract = stuck claim until stale (or allowlisted repair), then reclaim + stage idempotency

After worker/process interruption mid-Flow A:

1. Campaign remains `execution_state=processing` with the prior `execution_attempt_id` and `last_progress_at` frozen at the last progress boundary (no in-stage heartbeat assumed).
2. **Pre-TTL / non-stale:** any claim, calendar execute, or BL-012 resume MUST fail closed with already-claimed / active non-stale claim semantics and `recovery_classification=manual_intervention_required` (or the canonical BL-012 `flow_a_recovery_active_non_stale_claim` reason). No second pipeline run.
3. **Post-TTL:** `detect_stale_flow_a_execution` → `stale` + `retryable`; `claim_flow_a_execution` reclaim → new `execution_attempt_id` + `reclaimed_from_stale`; resume via connector execute and/or BL-012 resume using existing durable milestones and US-033/US-034 idempotency.
4. **Allowlisted repair:** `clear_stale_execution_claim` remains the explicit operator path to `idle` when stale rules allow — not an automatic restart hook.

This distinguishes US-035 (validate interruption + re-entry) from US-034 (deliver stale detect + reclaim) without inventing a second reclaim ontology: US-035 **exercises** US-034 reclaim under restart fixtures.

Alternatives considered:

- Auto-release on worker lifespan/startup: rejected — unsafe if a peer process still holds a live claim; breaks BL-012 active-claim gate.
- Immediate force-reclaim without TTL: rejected — would weaken US-033 non-stale protection.

### 3. Mid-flight interruption scenarios (evidence matrix)

Automated fixtures MUST cover at least these interruption points (simulate crash by leaving metadata/files mid-flight, then re-enter):

| # | Interrupt after | Expected post-restart behavior |
|---|-----------------|--------------------------------|
| A | Claim only (before publish) | Pre-TTL block; post-TTL reclaim → resume from empty/partial milestones without duplicate campaign |
| B | Image (ComfyUI done or partial PNG; handoff incomplete) | Reclaim/resume reuses/skips ComfyUI when reusable PNG exists; no second generation overwrite of readable public asset |
| C | Blog handoff (partial or complete checkout evidence) | `already_published` or fail-closed `blog_publish_target_exists` / BL-012 evidence ambiguity — never invent success |
| D | Schedule (during/after first schedule apply) | At most one durable schedule set; matching proof completed idempotent; mismatch fail-closed |
| E | LinkedIn publish (URN durable vs mid-API uncertain) | Durable URN → already-published, no API recall; missing URN after suspected API success → BL-008 uncertain path, **not** Flow A auto-publish |

Also cover: concurrent calendar/n8n-style re-trigger **immediately after restart** while claim still non-stale (must lose with already-claimed).

Test technique: prefer deterministic fixtures that set `last_progress_at` relative to a shortened `SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS` rather than real process kill; optional subprocess kill only if fixtures cannot express the state. Do not call real ComfyUI/LinkedIn.

### 4. Operator-visible outcomes and fail-closed communication

Every US-035 restart path MUST surface existing stable codes/fields:

- Already-claimed / active non-stale: `flow_a_execution_already_claimed` and/or `flow_a_recovery_active_non_stale_claim`, `recovery_classification=manual_intervention_required`
- Stale detect completed/skipped; reclaim `reclaimed_from_stale`
- Stage idempotent completes: `already_published`, schedule completed, `linkedin_publish_already_published`
- Fail-closed: `blog_publish_target_exists`, `linkedin_schedule_metadata_mismatch`, BL-012 `flow_a_recovery_evidence_ambiguous`, BL-008 uncertain classes
- Secret-safe JSON only (no tokens, absolute base paths, Markdown/draft bodies, raw provider payloads)

Prefer clarifying existing result fields and operator docs over new response schemas. Do not invent restart-specific lifecycle states.

### 5. Preserve US-033, US-034, BL-012, and BL-008; docs/status only after demonstration

- Do not weaken claim CAS, image skip, blog already_published / target-exists, schedule CAS, LinkedIn once-only, or stale reclaim semantics.
- Incomplete-campaign recovery resume continues to respect non-stale claim rejection and reclaim when stale; repair allowlist unchanged.
- LinkedIn mid-flight crash remains BL-008-owned.
- Update CURRENT-STATE after demonstrated implementation; keep US-033 and US-034 accepted; leave BL-013 open until US-035 acceptance; do not mark US-035 accepted from code alone.
- Product progress checklist: mark story reviewed / criteria agreed when proposal is approved for apply; do not mark accepted from proposal alone.

### 6. Narrow hardening only if restart fixtures expose a real gap

Default implementation posture: **validation + tests + operator documentation**. If a fixture proves an existing path can still duplicate under restart re-entry, apply the smallest hardening that reuses CAS / pre-check / BL-012 patterns — document the gap in CURRENT-STATE if deferred. Do not broaden into new endpoints or ontology.

## Risks / Trade-offs

- **[Risk] Long default stale TTL (3600s) hides restart recovery in ops** → Mitigation: fixtures use shortened TTL; operator docs explain pre-TTL block vs post-TTL reclaim; do not change default TTL in this change unless CURRENT-STATE/ops explicitly require it.
- **[Risk] Treating US-034 reclaim tests as US-035 done** → Mitigation: dedicated restart-interruption scenarios and operator docs that name restart vs stale reclaim.
- **[Risk] Auto-clear temptation for “faster recovery”** → Mitigation: explicit non-goal; fail closed on non-stale claims.
- **[Risk] LinkedIn mid-API duplicate post** → Mitigation: keep BL-008 uncertain / confirmation; restart tests assert no auto-republish without URN evidence.
- **[Risk] Scope creep into new recovery APIs** → Mitigation: Decision 1; only narrow hardening on proven gaps.
- **[Trade-off] Fixture simulation vs real process kill** → Accept deterministic metadata/file fixtures as primary evidence; real kill only if unavoidable for a specific race.

## Migration Plan

1. Add restart-interruption automated tests and any narrow hardening discovered; no campaign JSON schema migration required.
2. Document operator restart guidance (pre-TTL block → wait/stale reclaim or allowlisted repair → resume) without marking BL-013 closed.
3. Update CURRENT-STATE to “implemented / automated-tested” for US-035 only after tests pass; product story acceptance remains a separate validation step.
4. Deploy only with explicit user approval (not part of this change’s definition of done).
5. Rollback: revert worker image/commit; on-disk campaign documents remain compatible because no new required lifecycle states are introduced.

## Open Questions

- Whether any restart fixture exposes a real code gap requiring narrow hardening beyond tests/docs — resolve at apply time; default to validation-only if existing US-033/US-034/BL-012 paths already satisfy scenarios.
- Whether operator docs should live as a new `docs/operations/flow-a-concurrency-duplicate-execution-protection-us-035.md` (preferred, matching US-033/US-034) or an additive section in the incomplete-campaign recovery guide — prefer a dedicated US-035 ops note that links both.
- Whether default `SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS` needs an ops recommendation change — out of code scope unless apply-time evidence shows the default blocks safe recovery guidance; document only.
