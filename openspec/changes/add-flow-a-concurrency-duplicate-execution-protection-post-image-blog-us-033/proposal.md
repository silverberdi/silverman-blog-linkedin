## Why

BL-013 / US-033 requires that simultaneous or repeated Flow A triggers cannot process the same content twice for post processing, image generation, and blog publication. Worker claim, ComfyUI skip, and `already_published` idempotency already exist and are unit-tested for sequential re-runs, but true concurrent HTTP races (especially non-atomic campaign claim writes) and operator-visible concurrency outcomes are not yet a single, story-scoped contract. Without hardening and proving that surface, overlapping calendar/n8n/manual calls can still risk duplicate claims, duplicate ComfyUI work, or ambiguous blocked outcomes even when sequential idempotency passes.

## What Changes

- Add a worker-side concurrency and duplicate-execution protection capability scoped to **US-033 only**: post processing, image generation, and blog publication under concurrent or repeated triggers.
- Harden execution claiming so a second concurrent claim for the same campaign fails closed with the existing `flow_a_execution_already_claimed` / `manual_intervention_required` vocabulary (close read-modify-write races on campaign metadata without inventing a parallel queue ontology).
- Keep and strengthen image-generation and blog-publication duplicate prevention so concurrent or repeated publish paths cannot invoke ComfyUI twice or write duplicate blog artifacts when durable evidence already exists; preserve fail-closed `blog_publish_target_exists` when identity is unproven.
- Make concurrency outcomes operator-visible and understandable via structured, secret-safe status codes, `recovery_classification`, and skip/already-complete results — without new lifecycle states.
- Prefer additive contracts on existing claim / publish / handoff paths; **do not** introduce parallel endpoints unless design proves an unavoidable gap after inspecting `src/` and `tests/`.
- Update CURRENT-STATE and product progress only to the demonstrated implementation level; do not mark US-033 accepted, US-034/US-035 started, or BL-013 closed from proposal or code alone.

## Goals

- Satisfy US-033 acceptance criteria: prevent duplicate post processing; prevent duplicate image generation; prevent duplicate blog publication; make outcomes visible; communicate failures/blocks clearly; avoid duplicating or unintentionally changing completed work.
- Reuse existing claim / stale / reclaim / idempotency vocabulary from `flow-a-operational-queue-lifecycle`, `flow-a-lifecycle`, blog publish, and image handoff specs.
- Prefer ADR-0001 HTTP worker enforcement over relying solely on n8n single-flight (n8n guard remains complementary defense-in-depth; worker must remain safe if orchestration overlaps).
- Fail closed on ambiguous identity or concurrent claim contention; secret-safe responses.
- Keep scope to the smallest coherent worker capability for US-033 only.

## Non-goals

- **US-034:** prevent duplicate scheduling; prevent duplicate LinkedIn publication; recover abandoned processing claims (stale detect / reclaim as a story deliverable).
- **US-035:** validate behavior during restarts.
- Changing BL-012 / US-031–US-032 incomplete-campaign recovery contracts except where a narrow, documented dependency on shared claim rejection is required.
- Reworking LinkedIn publication recovery (BL-008 / US-021–US-022).
- Broad metadata locking for unrelated campaign fields, new queue folders, or a second claim ontology.
- Git push, live-site mutation, LinkedIn API publish, deploy, or production n8n activation as part of this change.
- Marking US-033 accepted or BL-013 closed from proposal/code alone.

## Acceptance Criteria Coverage

- **Prevent duplicate post processing:** concurrent or repeated claim/accept/process paths for the same campaign/source must not create a second active non-stale processing claim or duplicate queue acceptance; second contender fails closed with stable already-claimed / already-queued outcomes.
- **Prevent duplicate image generation:** concurrent or repeated publish/image paths must not call ComfyUI when a reusable active-folder or public asset already satisfies the image prerequisite; skip/reuse outcomes remain durable and operator-visible.
- **Prevent duplicate blog publication:** concurrent or repeated `publish_blog_post` for matching publish identity returns `already_published` (or equivalent completed short-circuit) without overwriting; unproven target collision continues to fail closed without overwrite.
- **Visible and understandable outcome:** structured JSON / result fields expose claim status, skip/already-complete reasons, `recovery_classification` where applicable, and safe identity fields — no secrets or content bodies.
- **Failures or blocked states clearly communicated:** stable codes for already-claimed, already-queued, target-exists without proof, image skip vs failure, auth/validation failures.
- **Existing completed work not duplicated or unintentionally changed:** completed blog publish evidence and existing image assets are preserved; re-runs short-circuit rather than rewrite.

US-034 criteria (scheduling / LinkedIn publish / abandoned-claim recovery) and US-035 (restart validation) are intentionally excluded.

## Capabilities

### New Capabilities

- `flow-a-concurrency-duplicate-execution-protection`: Worker-side concurrency and duplicate-execution protection for Flow A under simultaneous or repeated triggers. This change defines the US-033 slice only (post processing, image generation, blog publication): atomic/safe claim contention handling, no duplicate ComfyUI generation, no duplicate blog publication, operator-visible outcomes, and fail-closed blocked states. Later BL-013 stories (US-034 / US-035) MAY extend this capability; they are out of scope here.

### Modified Capabilities

- `flow-a-operational-queue-lifecycle`: Narrow hardening so concurrent claim/acceptance contention fails closed with existing `flow_a_execution_already_claimed` / `skipped_already_queued` / `manual_intervention_required` vocabulary, including closing non-atomic claim write races for the US-033 post-processing surface. Stale reclaim as a deliverable remains US-034.
- `worker-blog-publishing-endpoint`: Narrow clarification/hardening that concurrent or repeated publish requests honor `already_published` short-circuits and fail-closed target collision without duplicate public artifacts or unintentional metadata mutation.
- `blog-image-public-asset-handoff`: Narrow clarification/hardening that concurrent or repeated image paths do not invoke ComfyUI when reusable public/active assets already exist, with visible skip/reuse outcomes.

## Impact

- **API:** no new primary endpoints expected; strengthen behavior and response clarity on existing claim helpers, queue acceptance, `POST /publish-blog-post`, and calendar connector claim→publish sequencing. Any additive response fields must be secret-safe and non-breaking.
- **Worker:** claim/metadata write path may gain compare-and-swap or equivalent atomic claim semantics; publish and image handoff paths remain the stage executors; incomplete-campaign recovery and LinkedIn publication recovery stay intact.
- **Data:** no new lifecycle states; optional additive operator-visible concurrency outcome fields only if design proves they are required without overlapping US-034 reclaim semantics.
- **n8n:** orchestration single-flight (US-010) remains complementary; this change does not ship or activate production workflows.
- **Tests and docs:** concurrent/repeated-trigger behavioral tests for claim contention, image skip, blog already-published; CURRENT-STATE / operator docs / product progress updated only after demonstrated implementation.
- **Out of scope systems:** no LinkedIn API publish path changes; no Git/live-site mutation; no deploy as part of this change.
