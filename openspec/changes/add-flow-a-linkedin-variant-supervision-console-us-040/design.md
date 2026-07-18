## Context

BL-015 / US-040 (Story 3) builds on the US-038/US-039 supervision console already implemented in the worker:

| Surface | Path | Posture |
|---------|------|---------|
| Pending list API | `GET /flow-a/linkedin-variants/pending-supervision` | Read-only aggregation; nullable `draft_content`; enablement flag; `auto_queue_eligible` / last action |
| Operator console | `GET /flow-a/console/linkedin-variant-supervision` | Static HTML; session API key; Edit + Defer (US-039) |
| Cancel mutation | `POST /cancel-linkedin-publication` | US-017 — implemented for `pending` and `queued` |
| Defer mutation | `POST /defer-linkedin-variant` | US-017 — already wired in console |

CURRENT-STATE records US-038 + US-039 as implemented in the worker (not Story accepted; BL-015 open). Cancel remains out of band; blocked-state communication is partial (enablement banner + row eligibility fields exist but are not framed as the US-015 blocked/deferred table).

Stakeholders: content operator (primary); implementer under OpenSpec approval.

## Goals / Non-Goals

**Goals:**

- Add **Cancel** on the existing static console for pending rows, persisting only through authenticated `POST /cancel-linkedin-publication` (`dry_run` default `true`).
- Keep **Defer** from US-039 as the defer half of “cancel or defer before queue” (policy-aligned gaps only — do not rebuild defer).
- Surface blocked/deferred context: publication enablement, deferred/`auto_queue_eligible` effects, and integration-failure context operators need without raw mount inspection.
- After real cancel, refresh the list so the variant leaves the `pending` window; explain eligibility exclusion clearly.
- Communicate cancel failures with existing stable codes; preserve edit/defer failure UX.
- Secrets stay out of committed HTML (extend secrets audit).

**Non-Goals:**

- New mutation endpoints or changing US-017 cancel/defer contracts.
- Changing BL-007 auto-queue implementation (consume eligibility effects only).
- LinkedIn API publish; enablement bypass; Flow B; closing BL-015 / Story accepted from apply alone.
- Full failed-variant recovery console (BL-008 paths remain separate).
- Frontend framework introduction (static HTML remains the surface).

## Decisions

### Decision 1: Extend static HTML — call existing cancel POST

**Choice:** Keep `GET /flow-a/console/linkedin-variant-supervision` as the single operator surface. Add per-row **Cancel** control that `fetch`es same-origin:

- `POST /cancel-linkedin-publication` with `{ campaign_id, variant, dry_run, reason?, idempotency_key? }`

Reuse the US-039 sessionStorage API-key pattern (`Authorization: Bearer <key>`). Do **not** add wrapper mutation routes on `/flow-a/...`.

**Why:** Proposal requires reuse of US-017 cancel SoT; ADR-0001 places authority on worker HTTP. Parallel cancel endpoints would drift from `linkedin-publication-integration` / mechanics docs.

**Alternatives considered:**

| Alternative | Rejected because |
|-------------|------------------|
| New `POST /flow-a/console/.../cancel` proxy | Duplicate mutation SoT |
| Out-of-band curl only | Fails “console” Story 3 acceptance |
| SPA/React | Over-scope; no frontend toolchain |

### Decision 2: Dry-run default and confirm for cancel (match Story 2)

**Choice:** Cancel MUST expose dry-run default **on**, with an explicit confirm before real cancel. Success copy MUST distinguish “validated (dry-run, no mutation)” from “cancelled (real)”. Real cancel MUST NOT claim LinkedIn API published; MUST state the variant leaves the pending supervision window and is not strategy-driven auto-queue eligible.

**Why:** Fail-safe operator posture; matches US-017 `dry_run` default and US-039 edit/defer UX.

### Decision 3: Blocked-state surfacing — enrich read context, not a second console

**Choice:** Strengthen operator-visible blocked/deferred context on the existing pending-supervision GET + console:

1. **Publication enablement** — keep response `linkedin_publication_enabled`; console banner remains display-only (MUST NOT hide pending rows; MUST NOT change the env flag).
2. **Deferred capabilities** — for each pending row, present existing `operator_supervision_last_action` and `auto_queue_eligible` with clear copy (defer → not eligible until due per US-017; cancel outcome explained after action). Optionally expose nullable `operator_supervision_reason` from campaign metadata when present (minimal field add).
3. **Integration failures** — while scanning campaigns for pending rows, collect a compact read-only `integration_failures[]` (or equivalent) of sibling variants in the same campaign documents with `publish_state=failed` (include `campaign_id`, `variant_id`, `publish_state`, and available secret-safe failure fields such as `last_error_code` / `http_status` when present). Display as blocked context; do **not** offer cancel/edit/defer on failed rows in this story; do **not** call LinkedIn.

Pending list remains `publish_state=pending` only. Cancelled variants disappear from the list after refresh — that is the success outcome signal.

**Why:** US-040 AC2 requires enablement, integration failures, and deferred capabilities without turning BL-015 into a general publication-ops dashboard. Sibling-failed summary reuses the same campaign scan already performed for pending aggregation.

**Alternatives considered:**

| Alternative | Trade-off |
|-------------|-----------|
| UI-only banners with no GET change | Weaker “integration failures” evidence; harder to test |
| Separate failed-variants endpoint | Extra surface; out of BL-015 pending-window scope |
| Include `cancelled`/`queued` in main list | Dilutes supervision window contract from US-038 |

### Decision 4: Outcome visibility after cancel

**Choice:** On successful cancel (dry-run or real), show a status banner with campaign/variant, action, `dry_run`. On real success, re-fetch pending-supervision; expect the cancelled variant absent; copy MUST explain `publish_state` moved to `cancelled` (worker truth) and BL-007 auto-queue will not pick it up — without claiming LinkedIn API published or site published.

Retain US-039 defer outcome behavior unchanged.

### Decision 5: Failure communication maps existing cancel / supervision codes

**Choice:** Surface machine-readable errors for cancel attempts, including at least:

| Code / condition | Operator message intent |
|------------------|-------------------------|
| `401` | Auth failed; clear key; re-prompt |
| `422` | Request validation |
| `linkedin_supervision_variant_not_pending` / action-not-allowed family | Variant left window or wrong state; reload |
| `linkedin_publish_cancel_not_allowed` | Cancel not allowed (e.g. already published) |
| `linkedin_supervision_idempotency_conflict` | Same key, different payload |
| Network / non-JSON | Generic request failure |

Do not invent new worker error codes for Story 3. Keep US-039 defer/edit code mapping.

### Decision 6: Scope of actions

**Choice:** Expose cancel only for rows returned by pending-supervision (`pending`). Do not add queued post-queue cancel UI in this story (US-017 supports queued cancel, but BL-015 console scope is the optional pre-send pending window). Do not change edit/defer controls except shared copy/blocked-state framing.

Optional `reason` and auto-generated `idempotency_key` for real cancels (same pattern as Story 2).

### Decision 7: Docs and progress discipline

**Choice:** After demonstrated tests, update CURRENT-STATE for US-040 **implemented / in progress** (not Story accepted unless separately recorded). Progress-checklist: in-progress marks only; **MUST NOT** check Story accepted or BL-015 closed. Cross-link mechanics that Story 3 console exercises cancel — do not rewrite US-017 contracts. Optionally refresh stale “console deferred” wording in policy/mechanics cross-links only.

## Risks / Trade-offs

- [Accidental real cancel] → Dry-run default on; confirm for real writes; clear irreversible-eligibility copy.
- [Operator confuses cancel with LinkedIn unpublish] → Explicit language: cancel is worker `publish_state` / eligibility only; no LinkedIn API call.
- [Integration-failure list noise] → Bound to campaigns that appear in the pending scan (or same directory pass); secret-safe fields only; no full failure history dump.
- [Concurrent auto-queue race] → Rely on US-017 pending checks; show not-pending / not-allowed errors and reload.
- [Scope creep into BL-008 recovery UI] → Specs forbid failed-variant mutation from this console.
- [Secrets in HTML] → Extend secrets audit; sessionStorage only.

## Migration Plan

1. Minimally extend pending-supervision aggregation for blocked-context fields (`integration_failures` and optional reason) — still read-only, no LinkedIn calls.
2. Extend static console HTML/JS: Cancel panel + blocked-state section; wire cancel POST; refresh on real success.
3. Add/extend tests (cancel wiring, dry-run, error display, blocked-state fields, secrets audit, no duplicate mutation routes).
4. Docs: CURRENT-STATE + progress-checklist in-progress only; mechanics cross-link.
5. Deploy only after explicit user approval.
6. Rollback: revert image/static asset; no schema migration (uses existing `operator_supervision` / `cancelled` state).

## Open Questions

_None blocking proposal._ Fixed surfaces:

| Surface | Path |
|---------|------|
| Console (extended) | `GET /flow-a/console/linkedin-variant-supervision` |
| Pending read (blocked-context fields) | `GET /flow-a/linkedin-variants/pending-supervision` |
| Cancel | `POST /cancel-linkedin-publication` (existing) |
| Defer (unchanged wiring) | `POST /defer-linkedin-variant` (existing) |
