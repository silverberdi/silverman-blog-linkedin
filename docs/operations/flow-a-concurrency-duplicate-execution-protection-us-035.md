# Flow A concurrency and duplicate-execution protection (US-035)

Operator-facing guidance for **BL-013 / US-035** only: validate that
**worker/process interruption mid-Flow A** does not create duplicate artifacts
or external publications when work resumes. Worker HTTP remains the safety net
(ADR-0001). US-035 **exercises** existing US-033 / US-034 / BL-012 / BL-008
paths under restart fixtures — it does not invent a second reclaim ontology.

## Status

- **Implemented, automated-tested, and acceptance criteria validated** against restart-interruption fixture evidence (2026-07-18).
- **Not** deployed or operationally validated on the live worker by this document alone.
- US-033 and US-034 remain accepted. **BL-013 closed 2026-07-18**.

## Restart contract (reuse stale / reclaim vocabulary)

After mid-flight interruption, campaign metadata stays
`execution_state=processing` with the prior `execution_attempt_id` and
`last_progress_at` frozen at the last progress boundary.

| Phase | Behavior | Operator-visible outcome |
|-------|----------|--------------------------|
| **Pre-TTL / non-stale** | Duplicate claim, calendar execute, or BL-012 resume fails closed | `flow_a_execution_already_claimed` and/or `flow_a_recovery_active_non_stale_claim`; `recovery_classification=manual_intervention_required` |
| **Post-TTL** | Same US-034 stale detect + reclaim path | Detect → `stale` + `retryable`; reclaim → `reclaimed_from_stale=true`, new `execution_attempt_id` |
| **Allowlisted repair** | Explicit operator path only | `clear_stale_execution_claim` when stale rules allow → `idle` without erasing durable stage evidence |

**Do not** expect worker/process/Docker start to auto-clear non-stale
`processing` claims. Stuck claims wait for stale TTL or allowlisted repair.

Default TTL is `SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS` (minimum 60;
default 3600). Fixtures use a shortened value; this change does not alter the
default.

## Mid-flight interruption surfaces

| Interrupt after | Expected after reclaim / resume |
|-----------------|----------------------------------|
| Claim only | Resume from evidence; no invented `already_published`, schedule success, or URN |
| Image (reusable PNG present) | ComfyUI skip/reuse; readable public asset not overwritten |
| Blog handoff (matching identity) | `already_published`; unproven targets → `blog_publish_target_exists` / BL-012 evidence ambiguity |
| Schedule | At most one durable matching set; mismatch → `linkedin_schedule_metadata_mismatch` |
| LinkedIn with durable URN | `linkedin_publish_already_published`, zero API calls, URN preserved |
| LinkedIn mid-API without URN | **BL-008 uncertain** — no Flow A auto-republish; confirmation-gated re-queue |

Concurrent calendar/n8n-style re-trigger **immediately after restart** while the
claim is still non-stale loses with already-claimed and does not start a second
pipeline.

## How to operate after a crash

1. Confirm campaign still shows `execution_state=processing` (expected).
2. If still within the stale window: treat duplicate triggers as blocked;
   wait, or use allowlisted `clear_stale_execution_claim` when stale rules allow.
3. After TTL: run stale detect (or let reclaim/resume path detect), then reclaim
   / BL-012 resume. Completed stages short-circuit on durable evidence.
4. For LinkedIn mid-publish without URN: follow
   [linkedin-retry-recovery-classification.md](linkedin-retry-recovery-classification.md)
   (verify on LinkedIn, then repair or attested re-queue) — not Flow A reclaim
   alone.

## Explicit non-goals

| Item | Not delivered by US-035 |
|------|-------------------------|
| Startup auto-clear of non-stale claims | Forbidden |
| Auto LinkedIn API republish after mid-API crash | BL-008 owns uncertain / confirmation |
| New primary endpoints / lifecycle states | Prefer existing helpers |
| Re-implementing US-033 / US-034 | Preserved; exercised under restart fixtures only |
| Git push / live-site mutation / deploy / production n8n activation | Out of scope |

## Secret-safe responses

Already-claimed, reclaim, resume, and fail-closed paths expose stable codes and
recovery classification only. Do not expect tokens, absolute editorial/public
base paths, Markdown/draft bodies, or raw provider payloads.

## Related evidence

- Change: `openspec/changes/add-flow-a-concurrency-duplicate-execution-protection-restart-validation-us-035/`
- Tests: `tests/test_flow_a_concurrency_us035.py`
- Prior stories: [us-033](flow-a-concurrency-duplicate-execution-protection-us-033.md),
  [us-034](flow-a-concurrency-duplicate-execution-protection-us-034.md)
- BL-012: [flow-a-incomplete-campaign-recovery.md](flow-a-incomplete-campaign-recovery.md)
- BL-008: [linkedin-retry-recovery-classification.md](linkedin-retry-recovery-classification.md)
- Status authority: [CURRENT-STATE.md](../CURRENT-STATE.md)
