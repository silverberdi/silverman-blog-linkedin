## Context

BL-015 / US-039 (Story 2) builds on the US-038 read-only supervision console already implemented in the worker:

| Surface | Path | Posture |
|---------|------|---------|
| Pending list API | `GET /flow-a/linkedin-variants/pending-supervision` | Read-only aggregation |
| Operator console | `GET /flow-a/console/linkedin-variant-supervision` | Static HTML; session API key prompt |
| Edit mutation | `POST /correct-linkedin-variant` | US-017 — implemented |
| Defer mutation | `POST /defer-linkedin-variant` | US-017 — implemented |

CURRENT-STATE records US-038 as implemented in the worker (not Story accepted; BL-015 open). Operators can list `pending` variants but cannot edit text or reschedule from the console; they must call US-017 POSTs out-of-band or edit mount files. US-039 wires the existing console to those POSTs so corrections persist via `operator_supervision` and artifact writes without a parallel SoT.

Stakeholders: content operator (primary); implementer under OpenSpec approval.

## Goals / Non-Goals

**Goals:**

- Extend the existing static console so operators can edit draft content and defer/reschedule while `publish_state` is `pending`.
- Persist exclusively through authenticated US-017 POSTs (`dry_run` default `true`, stable error codes, idempotency as already specified).
- Refresh the console view after actions so schedule / last supervision action / eligibility context are visible.
- Communicate auth, validation, dry-run vs real, and US-017 failure codes clearly on the page.
- Keep secrets out of committed HTML/docs (extend US-038 secrets audit).

**Non-Goals:**

- Cancel UI or cancel-driven eligibility surfaces (US-040).
- New mutation endpoints or duplicate persistence paths.
- Changing US-017 request/response contracts beyond console consumption.
- Changing BL-007 auto-queue implementation (edit/defer already affect eligibility per US-017).
- LinkedIn API publish; enablement bypass; Flow B; closing BL-015 / Story accepted from apply alone.
- Frontend framework introduction unless design is overturned during apply (default remains static HTML).

## Decisions

### Decision 1: Extend the US-038 static HTML — call existing US-017 POSTs

**Choice:** Keep `GET /flow-a/console/linkedin-variant-supervision` as the single operator surface. Add per-row (or detail-panel) **Edit** and **Defer** controls that `fetch` same-origin:

- `POST /correct-linkedin-variant` with `{ campaign_id, variant, draft_content, dry_run, reason?, idempotency_key? }`
- `POST /defer-linkedin-variant` with `{ campaign_id, variant, new_scheduled_at_utc, dry_run, reason?, idempotency_key? }`

Use the same sessionStorage API-key pattern as Story 1 (`Authorization: Bearer <key>`). Do **not** add wrapper mutation routes on `/flow-a/...`.

**Why:** Proposal and backlog require persistence via existing US-017 mechanics; ADR-0001 already places SoT on worker HTTP. Duplicate endpoints would drift from `linkedin-publication-integration` / mechanics docs.

**Alternatives considered:**

| Alternative | Rejected because |
|-------------|------------------|
| New `POST /flow-a/console/...` proxies | Duplicate mutation SoT; extra auth/error mapping |
| n8n form calling POSTs | Wrong host for operator console; still needs UI; out of BL-015 Story 2 surface |
| SPA/React app | Over-scope; repo has no frontend toolchain; US-038 static HTML is sufficient |

### Decision 2: Dry-run vs real mutation is explicit in the UI

**Choice:** Console actions MUST expose an explicit dry-run control that defaults to **on** (aligned with US-017 `dry_run` default `true`). Real mutation requires the operator to turn dry-run off (and SHOULD use a confirm step for real writes). Success copy MUST distinguish “validated (dry-run, no mutation)” from “persisted (real)”.

**Why:** Fail-safe operator posture; matches worker contract; reduces accidental artifact/metadata writes.

**Alternatives considered:** Always real write (unsafe); always dry-run only (fails “persist” acceptance).

### Decision 3: Minimal read-path extension for draft content

**Choice:** Extend `GET /flow-a/linkedin-variants/pending-supervision` rows with nullable `draft_content` read from the existing artifact path `linkedin-posts/generated/<campaign_id>/<variant_id>.md` (same path US-017 correction writes). When the artifact is missing or unreadable, set `draft_content` to `null` and append a structured `issues[]` entry; still list the pending row so defer remains possible.

The GET remains **read-only** (no campaign/calendar writes; still MUST NOT call US-017 mutation routes server-side). The **console page** (browser) MAY call mutation POSTs — that is Story 2, not a server-side read-path side effect.

**Why:** Edit form needs current text without mount scraping. Including draft on the existing pending list avoids a second mutation-adjacent endpoint and matches “necessary console extension” of US-038 read contracts. Pending sets are expected to be small.

**Alternatives considered:**

| Alternative | Trade-off |
|-------------|-----------|
| Separate `GET .../draft` per variant | Cleaner payloads; extra route + auth surface |
| Operator pastes content from files | Fails “without inspecting raw files” |
| Omit draft; empty textarea only | Weakens edit UX; higher risk of accidental full overwrite |

### Decision 4: Outcome visibility after action

**Choice:** On successful edit/defer (dry-run or real), show a clear status banner with campaign/variant, action, `dry_run`, and any returned fields (e.g. new schedule). On real success, automatically re-fetch `GET /flow-a/linkedin-variants/pending-supervision` so updated `scheduled_at_utc`, `operator_supervision_last_action`, and `auto_queue_eligible` appear in the table. Do not claim LinkedIn API published.

**Defer note (existing US-017):** Defer does not auto-update editorial calendar; console MUST NOT invent calendar write-back. Keep calendar join as read-only context (may look stale until manual calendar reconciliation — same as mechanics doc).

### Decision 5: Failure communication maps US-017 codes

**Choice:** When POST returns `status=failed` (or HTTP 401/422), surface machine-readable `errors[]` codes and short operator-facing explanations for at least:

| Code / condition | Operator message intent |
|------------------|-------------------------|
| `401` | Auth failed; clear stored key; re-prompt |
| `422` | Request validation (missing fields, bad types) |
| `linkedin_supervision_variant_not_pending` | Variant left supervision window; reload list |
| `linkedin_supervision_defer_time_invalid` | Schedule must be strictly in the future (UTC) |
| `linkedin_supervision_edit_unchanged` | Content unchanged or empty after normalize |
| `linkedin_supervision_idempotency_conflict` | Same key, different payload |
| `linkedin_supervision_action_not_allowed` | Action not allowed for current state |
| Network / non-JSON | Generic request failure |

Do not invent new error codes in the worker for Story 2.

### Decision 6: Scope of actions on the console

**Choice:** Expose **edit** and **defer** only for rows returned by the pending-supervision list (`publish_state=pending`). Do **not** expose cancel. Do **not** add failed-variant correction UI (US-022 path exists on the same POST but is outside US-039 supervision-window story).

Optional `reason` field MAY be offered (free text / small select including guidance values like `criteria_failure` / `operator_choice` from mechanics — not automatic gates).

Optional `idempotency_key` MAY be auto-generated per submit (UUID) for real mutations so accidental double-clicks replay safely when payload matches.

### Decision 7: Docs and progress discipline

**Choice:** After demonstrated behavior in tests, update CURRENT-STATE for US-039 console actions **implemented / in progress** (not Story accepted unless separately recorded). Progress-checklist: may check reviewed / work started / demonstrated when true; **MUST NOT** check Story accepted or BL-015 closed. Cross-link mechanics doc that Story 2 console now exercises edit/defer — do not rewrite US-017 normative contracts.

## Risks / Trade-offs

- [Accidental real mutation] → Dry-run default on; confirm for real writes; clear banner wording.
- [Large draft payloads on list GET] → Accept for small pending sets; revisit separate draft GET only if operationally painful.
- [Stale calendar after defer] → Document; no silent calendar write (US-017 already states this).
- [Concurrent operator / auto-queue race] → Rely on US-017 pending checks; show not-pending errors and reload.
- [Scope creep into cancel / blocked console] → Tasks and specs forbid cancel UI; US-040 owns it.
- [Secrets in HTML] → Extend Story 1 secrets audit; sessionStorage only; no placeholders that look like keys.

## Migration Plan

1. Extend pending-supervision aggregation with `draft_content` (nullable) + issue on missing artifact.
2. Extend static console HTML/JS for edit/defer panels calling existing POSTs; refresh list on real success.
3. Add/extend tests (action wiring, dry-run, error display, secrets audit, draft_content field).
4. Docs: CURRENT-STATE + progress-checklist in-progress only.
5. Deploy only after explicit user approval — implementation alone is not live.
6. Rollback: revert image/static asset; no schema migration (uses existing `operator_supervision`).

## Open Questions

_None blocking proposal._ Fixed surfaces:

| Surface | Path |
|---------|------|
| Console (extended) | `GET /flow-a/console/linkedin-variant-supervision` |
| Pending read (extended fields) | `GET /flow-a/linkedin-variants/pending-supervision` |
| Edit | `POST /correct-linkedin-variant` (existing) |
| Defer | `POST /defer-linkedin-variant` (existing) |
