## Context

BL-013 / US-033 asks the worker to ensure simultaneous or repeated Flow A triggers cannot process the same content twice for **post processing**, **image generation**, and **blog publication**. Adjacent stories (US-034 scheduling / LinkedIn publish / abandoned-claim reclaim; US-035 restart validation) are out of scope.

Current evidence (`docs/CURRENT-STATE.md`, `src/`, `tests/`):

| Surface | Existing contract | Gap for true concurrency |
|---------|-------------------|---------------------------|
| Post processing | `claim_flow_a_execution` rejects non-stale `processing` with `flow_a_execution_already_claimed` + `manual_intervention_required`; queue acceptance has `skipped_already_queued` | Claim uses read → mutate → `write_campaign_metadata` with **no compare-and-swap**; two overlapping claims can both observe `idle` and both write `processing` |
| Image generation | Public/active PNG reuse skips ComfyUI (`blog-image-public-asset-handoff`); retries covered in tests | Concurrent first-time generation can race the existence check before either asset is durable |
| Blog publication | `already_published` short-circuit; `blog_publish_target_exists` fail-closed overwrite refusal | Sequential idempotency is strong; concurrent first publish still relies on target-existence fail-closed and needs explicit US-033 scenarios |

Orchestration-side single-flight (`flow-a-n8n-workflow-activation`) is complementary defense-in-depth. Per ADR-0001 and product intent, the **worker** MUST remain safe if overlapping HTTP calls occur.

Constraints: reuse claim / stale / reclaim / idempotency vocabulary; no parallel queue ontology; fail closed on ambiguity; secret-safe responses; preserve BL-012 incomplete-campaign recovery and BL-008 LinkedIn publication recovery; no Git push / live-site / LinkedIn API / deploy / production n8n activation in this change.

## Goals / Non-Goals

**Goals:**

- Satisfy US-033 acceptance criteria on the worker HTTP surface.
- Close claim TOCTOU races with an additive compare-and-swap (or equivalent) patterned after calendar fingerprint protection.
- Keep image and blog duplicate prevention durable under concurrent/repeated triggers with operator-visible outcomes.
- Prefer existing endpoints and helpers; no new primary HTTP routes unless apply-time inspection proves an unavoidable gap.
- Keep incomplete-campaign recovery and LinkedIn publication recovery intact.

**Non-Goals:**

- US-034: duplicate scheduling prevention, duplicate LinkedIn API publication prevention, abandoned-claim reclaim as a story deliverable.
- US-035: restart validation evidence.
- Global campaign-metadata locking for unrelated writers.
- New lifecycle states, new `blog-posts/processing/` folder, or a second claim ontology.
- Weakening n8n single-flight or replacing it; both layers remain.
- Marking US-033 accepted or BL-013 closed from proposal/code alone.

## Decisions

### 1. No new primary endpoints — harden existing claim / publish / handoff paths

US-033 is enforced on:

- `claim_flow_a_execution` / queue acceptance helpers (`flow_a_operational_queue.py`)
- Calendar connector claim → `publish_blog_post` sequencing (propagate already-claimed visibly)
- `publish_blog_post` / blog publish idempotency (`blog_publish_flow.py`)
- Editorial image ensure + public asset handoff (ComfyUI skip/reuse)

Alternatives considered:

- New `/flow-a/concurrency-*` diagnostic endpoint: rejected — acceptance criteria are prevention outcomes, not a new operator console; operational-status already surfaces claim/stale fields.
- n8n-only single-flight: rejected — worker must fail closed under overlapping HTTP (ADR-0001; n8n is not the sole safety net).

### 2. Atomic claim via campaign-metadata compare-and-swap (CAS)

Introduce an additive write path for **execution claim transitions** that:

1. Reads campaign metadata and records a content fingerprint (SHA-256 of on-disk JSON bytes, same idea as `calendar_fingerprint`).
2. Decides claim eligibility (`idle`/`stale` → `processing`; reject non-stale `processing`).
3. Writes only if the on-disk fingerprint still matches; on mismatch, re-read and either treat as successful peer claim contention (`flow_a_execution_already_claimed`) or retry once within a small bounded loop.

Stable outcomes:

- Winner: `status=completed`, `execution_state=processing`, attempt metadata set.
- Loser: `status=failed`, `errors` include `flow_a_execution_already_claimed`, `already_claimed=true`, `recovery_classification=manual_intervention_required`.
- Optional additive code for CAS conflict after re-read still shows peer processing (e.g. reuse `flow_a_execution_already_claimed` — prefer **not** inventing a second operator-facing code unless tests need to distinguish transient CAS retry exhaustion; if needed, use one additive code such as `flow_a_execution_claim_conflict` that maps to the same recovery classification and operator guidance as already-claimed).

Scope CAS to claim (and, if apply proves necessary, queue-acceptance destination collision) — **not** every campaign metadata write in this change.

Alternatives considered:

- Process-wide `threading.Lock` only: insufficient across multiple worker processes/containers.
- Filesystem flock on campaign JSON: viable, but CAS fingerprint matches an existing calendar pattern operators already understand; flock may still be used internally as an implementation detail if CAS alone is insufficient on the filesystem.
- Defer race closing to US-034: rejected — duplicate post processing is explicitly US-033.

**US-034 boundary:** existing stale detection/reclaim helpers remain; this change MUST NOT expand reclaim semantics, TTL policy, or abandoned-claim recovery as deliverables. Non-stale contention rejects; stale reclaim behavior stays as already specified for later story validation.

### 3. Duplicate post processing = claim + already-queued identity

“Post processing” for US-033 means:

1. Queue acceptance cannot create a second campaign or duplicate queued Markdown for the same identity (`skipped_already_queued` / idempotent accept).
2. Only one non-stale `processing` claim may exist per campaign.
3. Connector / recovery resume paths that call `claim_flow_a_execution` inherit the same rejection (BL-012 already requires this; keep intact).

Direct `POST /publish-blog-post` without a prior claim remains allowed for existing clients; it MUST still be safe via Decision 5 (blog idempotency) and MUST NOT create a second campaign document.

### 4. Duplicate image generation = pre-ComfyUI existence re-check + no overwrite

Before invoking ComfyUI:

1. Re-check active-folder sibling PNG and public `assets/images/<public_slug>.png`.
2. If either reusable asset exists, skip generation with durable `blog_image_generation.status=skipped` (or existing equivalent) and proceed to handoff/backfill rules already specified.
3. MUST NOT overwrite an existing readable public asset solely because a concurrent attempt also entered generation.

Under an active Flow A claim (connector path), image work runs only for the claim holder; a second concurrent connector execution is blocked at claim (Decision 2), which is the primary concurrency gate for calendar-driven Flow A.

Alternatives considered:

- Separate ComfyUI job lock store: deferred — claim gate + existence re-check is smallest coherent fix for US-033; revisit only if tests prove dual ComfyUI calls after CAS claim.

### 5. Duplicate blog publication = existing idempotency + explicit concurrency scenarios

Preserve and scenario-test:

- Matching identity → `already_published` completed short-circuit (no validation/image/public writes).
- Targets exist without matching identity proof → `blog_publish_target_exists` (or existing equivalent), no overwrite.
- Concurrent first publish: at most one successful publish apply; loser must short-circuit or fail closed without corrupting the winner’s artifacts or inventing a second campaign.

Do **not** require Git push or live-site confirmation for US-033; handoff / checkout write idempotency is in scope; remote Git publication remains separately guarded elsewhere.

### 6. Operator-visible outcomes and fail-closed communication

Every US-033 contention or skip path MUST surface:

- Stable error or status code (`flow_a_execution_already_claimed`, `skipped_already_queued`, `already_published`, image `skipped` + `skip_reason`, `blog_publish_target_exists`, auth/validation codes).
- `recovery_classification=manual_intervention_required` when an active non-stale claim blocks a second execution.
- Secret-safe JSON only (no tokens, absolute base paths, Markdown/draft bodies, provider payloads).

Prefer clarifying connector item `errors` / status fields over new response schemas.

### 7. Preserve BL-012 and BL-008; additive docs/status only after demonstration

Incomplete-campaign recovery continues to reject non-stale processing claims. LinkedIn publication recovery is untouched. CURRENT-STATE and product checklist updates record implemented/tested US-033 work without claiming acceptance, deployment, US-034/US-035, or BL-013 closure.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| CAS retries under heavy contention cause latency | Bound retries (small fixed N); after exhaustion fail closed as already-claimed / claim conflict; no busy spin |
| Flock + CAS over-complicates apply | Prefer fingerprint CAS first; add flock only if tests show lost updates on the target FS |
| Direct publish without claim still races ComfyUI | Existence re-check immediately before provider call; no public overwrite; claim remains primary gate for connector Flow A |
| Scope creep into US-034 reclaim/schedule/LinkedIn | Explicit non-goals; tasks and specs omit reclaim/schedule/LinkedIn publish requirements |
| Breaking existing sequential claim tests | Keep sequential rejection semantics identical; add concurrent tests as net-new |
| False sense of “Flow A complete” | Use GLOSSARY layers; never claim unattended/live/LinkedIn from this change |

## Migration Plan

1. Implement CAS claim write + behavioral concurrent tests locally (Mac).
2. Extend image/blog concurrency scenarios without changing happy-path sequential contracts.
3. Run targeted then full pytest; update CURRENT-STATE / progress only after demonstrated outcomes.
4. Deploy only after explicit user approval (not part of propose/apply by default).
5. Rollback: revert claim write helper to prior non-CAS path if production anomaly; sequential idempotency remains as safety net.

## Open Questions

None blocking propose. Apply-time verification only:

1. Whether a distinct `flow_a_execution_claim_conflict` code is needed vs reusing `flow_a_execution_already_claimed` after CAS mismatch — default to reuse unless test clarity requires the additive code.
2. Whether queue-acceptance needs the same CAS fingerprint (likely only if concurrent accepts for identical ready identity still race after claim CAS); inspect during apply before expanding CAS beyond claim.
