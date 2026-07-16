# Proposal: implement-scheduled-linkedin-publication-execution-us-018

## Why

Flow A campaigns now finish with all LinkedIn variants in `publish_state` `pending` (BL-005 validated 2026-07-16), and BL-006 (US-015/US-016/US-017) established the strategy-driven publication default plus operator supervision overrides (`operator_supervision`, `auto_queue_eligible`). But nothing identifies due variants and moves them through queue → publish: BL-002 proved one controlled real publish and its sibling variants remain `pending` indefinitely. Canonical operation today requires the operator to compose two manual HTTP calls (`POST /queue-linkedin-publication` per variant, then `POST /publish-linkedin-due-variants`).

This change delivers **US-018** (BL-007 story 1 of 3): identify due variants, move only eligible variants to queued state, and publish each once — with clear operator-visible outcomes. It also formalizes the uncommitted `auto_queue_pending` construction WIP documented in [bl-007-auto-queue-pending-handoff.md](../../../docs/product/bl-007-auto-queue-pending-handoff.md) so it can be absorbed under an approved change instead of merged as a drive-by.

**Backlog / stories:** BL-007 — Implement Scheduled LinkedIn Publication Execution (P2); this change addresses **US-018 only**. US-019 (publication identifier / failure evidence polish) and US-020 (audience cadence and sequence) remain open.

## Goals

- Add opt-in `auto_queue_pending` (default `false`) to `POST /publish-linkedin-due-variants`: in one worker call, identify due `pending` variants, queue only eligible ones, then run the existing publish-due path.
- Define "due" for auto-queue as variant `scheduled_at_utc <= now_utc`, composed with the existing `publish_after_utc` safety delay and `publish_now` semantics.
- Honor US-017 supervision exclusions: never auto-queue `cancelled` variants, variants with `operator_supervision.auto_queue_eligible` `false`, variants not in `pending`, or variants not yet due.
- Define bounded cross-campaign scan behavior when `campaign_id`/`variant` are omitted, with an operator-understandable response summary (queued / published / skipped with reasons).
- Preserve once-only publication: no duplicate queue metadata for already-`queued` variants, idempotent already-`published` behavior unchanged, dry-run default `true`, fail-closed on `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- Absorb the WIP operator script (`deploy/server/run-publish-pending-linkedin-variants.sh`), helper (`deploy/server/finish-pending-linkedin-publication.sh`), and manual **inactive** n8n workflow (`n8n/workflows/silverman-blog-linkedin-publish-pending.json`) under the approved contract.

## Non-goals (explicit)

- Closing BL-007 or accepting US-019 / US-020; no normative cross-audience cadence/sequence contract (US-020) and no deeper failure taxonomy or retry evidence polish (US-019) beyond what publish-due already records.
- Permanent LinkedIn enablement; activating the publish-pending n8n workflow as an unattended production schedule (import ≠ unattended; requires separate approval).
- BL-008 retry/recovery rules — auto-queue does **not** automatically re-queue `failed` variants (manual re-queue via `POST /queue-linkedin-publication` remains as-is).
- BL-009 article preview validation; BL-015 supervision console UI.
- Changing US-015/US-016 policy substance, US-017 supervision mechanics, Flow A ready-path completion, or US-011 publication guard semantics.
- n8n Execute Command (ADR-0001 — orchestration stays worker HTTP only).

## Acceptance criteria addressed (US-018)

1. **Identify due variants** — auto-queue scan finds `pending` variants with `scheduled_at_utc <= now_utc` (or all eligible `pending` under explicit `publish_now` operator override).
2. **Move only eligible variants to queued state** — US-017 exclusions enforced; ineligible variants are skipped with stable reason codes, never mutated.
3. **Publish each variant once** — existing publish-due idempotency preserved; no double queue, no duplicate LinkedIn API post.
4. **Outcome visible and understandable** — response summarizes queued/published/skipped per variant with reasons; operator script prints the same.
5. **Failures or blocked states clearly communicated** — stable error/warning codes for enablement-off, not-due, supervision-excluded, and API failures.
6. **Existing completed work not duplicated or unintentionally changed** — default `auto_queue_pending=false` preserves the canonical two-step contract byte-for-byte; already `queued`/`published`/`cancelled` variants untouched.

Intentionally excluded criteria: none within US-018; US-019 and US-020 criteria are deliberately out of scope (see Non-goals).

## What Changes

- `POST /publish-linkedin-due-variants` request gains optional `auto_queue_pending` (default `false`). When `true`, the worker first queues eligible due `pending` variants (same rules as the queue service), then evaluates publish-due as today.
- Publish-due service (`linkedin_publication_flow.py`) gains pending-target collection and auto-queue helpers with eligibility exclusions from US-017 supervision metadata.
- Response includes per-variant results for both the queue phase and publish phase, plus skip reasons (stable codes).
- New operator script `deploy/server/run-publish-pending-linkedin-variants.sh` (dry-run default; `--real`, `--respect-schedule`, optional campaign/variant filters) and Mac-side helper `finish-pending-linkedin-publication.sh`.
- New manual n8n workflow `n8n/workflows/silverman-blog-linkedin-publish-pending.json`, repo export `"active": false` (HTTP-only per ADR-0001).
- Tests in `tests/test_linkedin_publication.py` for auto-queue eligibility, exclusions (cancel/defer/`auto_queue_eligible=false`), not-due skip, no-duplicate publish, dry-run no-mutation, and HTTP contract.
- Docs: operator documentation for the combined path; `docs/CURRENT-STATE.md` and product progress updates only when acceptance criteria are demonstrated.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `linkedin-publication-integration`:
  - `POST /publish-linkedin-due-variants` endpoint contract gains opt-in `auto_queue_pending` (MODIFIED endpoint requirement).
  - New requirements for auto-queue eligibility/due semantics, supervision exclusions, bounded cross-campaign pending scan, operator-visible outcome summary, publish-pending operator script, and manual inactive publish-pending n8n workflow (ADDED requirements).
  - Safety and orchestration boundaries requirement updated: this change adds one **inactive** n8n workflow file but still forbids activation, background triggers, and any publication without an explicit HTTP request (MODIFIED requirement).
  - Test coverage requirement extended with auto-queue scenarios (MODIFIED requirement).

No requirement-level changes to `linkedin-distribution-scheduling-model` (due semantics consume existing `scheduled_at_utc`) or `linkedin-variant-review-process` (its BL-007 eligibility documentation is implemented, not altered).

## Impact

- **Worker code:** `src/silverman_blog_linkedin/linkedin_publication_flow.py`, `src/silverman_blog_linkedin/main.py` (request model + logging).
- **Tests:** `tests/test_linkedin_publication.py`.
- **Deploy tooling:** `deploy/server/run-publish-pending-linkedin-variants.sh`, `deploy/server/finish-pending-linkedin-publication.sh` (new, absorbed from WIP).
- **n8n:** `n8n/workflows/silverman-blog-linkedin-publish-pending.json` (new, `"active": false`; import/activation are separate gated operational steps).
- **Docs:** LinkedIn publication operator docs, `docs/CURRENT-STATE.md`, `docs/product/user-stories.md` / `progress-checklist.md` (only when US-018 criteria demonstrated).
- **No changes** to campaign lifecycle states, scheduling model, supervision endpoints, blog handoff, or ComfyUI/DeepSeek paths.
- **Deployment note:** implementation ≠ deployed ≠ operationally validated. A server image may already contain construction WIP; server presence is not product completion. Controlled operational validation is a separate gated step after implementation commit, requiring explicit approval for real publish windows.
