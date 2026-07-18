## Context

BL-015 / US-038 asks for an operator-facing view of Flow A LinkedIn variants while they remain in the optional supervision window (`publish_state=pending`). Policy (US-015), quality criteria (US-016), and worker mutation mechanics (US-017) already exist. Auto-queue (BL-007 / US-018) is implemented separately. CURRENT-STATE records BL-015 as backlog-defined and not implemented.

Today the only related read surfaces are:

| Endpoint | What it returns | Gap for US-038 |
|----------|-----------------|----------------|
| `GET /flow-a/operational-status` | Aggregate LinkedIn `publish_state` counts per campaign | No per-variant rows with audience / `scheduled_at_utc` |
| `GET /editorial-calendar/status` | Calendar presence + item counts by status | No variant list; no campaign join |
| US-017 POSTs | Edit / defer / cancel | Mutation only — out of US-038 scope |

There is no frontend framework or HTML operator console in the repo. Source of truth remains campaign metadata (`metadata/campaigns/<id>.json`) and `editorial-calendar/calendar.json` on the worker mount. Per ADR-0001, the console MUST obtain data via worker HTTP — not by scraping mounts from the browser.

Stakeholders: content operator (primary user); implementer applying this change under OpenSpec approval.

## Goals / Non-Goals

**Goals:**

- Smallest coherent **read-only** supervision view satisfying US-038 acceptance criteria.
- Per-pending-variant display: `campaign_id`, variant id, `audience`, `scheduled_at_utc`, `publish_state`.
- Calendar alignment where a calendar item shares `campaign_id` (show calendar `item_id`, `title`, `due_at_utc`, `status` when present).
- Clear communication of read/display failures (missing/invalid calendar, unreadable campaign JSON, empty result set) and display-only context for publication enablement off.
- Same-origin UI so the operator does not paste mount paths into a file editor.

**Non-Goals:**

- Edit / defer / cancel UI or any call to US-017 mutation routes (US-039 / US-040).
- New LinkedIn publish/queue paths or enablement bypass.
- Flow B console.
- Closing BL-015 or marking US-038 Story accepted from apply alone.
- Changing US-015 strategy-driven default or US-017 contracts.
- Expanding `GET /flow-a/operational-status` into a supervision API (keep observability and supervision concerns separate).

## Decisions

### Decision 1: Thin authenticated GET for pending supervision rows

**Choice:** Add the fixed path `GET /flow-a/linkedin-variants/pending-supervision` (Flow A operator read surface, parallel to `/flow-a/operational-status`; not under flat LinkedIn mutation routes). Protected by existing API-key auth. Read-only: no filesystem writes, no campaign mutation, no LinkedIn/DeepSeek/ComfyUI/Git calls.

**Response shape (normative intent):**

- Top-level status (`ok` | `partial` | error equivalents for total failure).
- `variants[]` rows, each with at least: `campaign_id`, `variant_id` (or `variant`), `audience`, `scheduled_at_utc`, `publish_state` (`pending` only in the primary list).
- Optional calendar join fields when matched: `calendar_item_id`, `calendar_title`, `calendar_due_at_utc`, `calendar_status`.
- Optional display-only fields when already on the variant (do not invent): e.g. `operator_supervision.last_action`, `auto_queue_eligible` — visible for context, not actionable in Story 1.
- Structured `issues[]` / errors for unreadable campaigns, calendar missing/invalid, unknown `publish_state` values encountered while scanning (report, do not rewrite).
- Display-only `linkedin_publication_enabled` boolean (env flag presence as true/false) so operators see technical block context without secrets.

**Why not reuse existing GETs alone:** Operational status and calendar status lack the required per-variant field set. Composing them client-side still cannot invent missing variant rows without a new aggregation or mount scrape.

**Alternatives considered:**

| Alternative | Rejected because |
|-------------|------------------|
| Extend `GET /flow-a/operational-status` | Couples observability aggregates to a supervision UI contract; risk of regressing US-026/US-027 |
| Client reads mount files / static JSON export | Violates ADR-0001 SoT boundary; browser cannot safely access Docker mounts |
| CLI-only table in docs | Weaker “visible and understandable” operator console for BL-015; still useful as secondary smoke helper if needed |
| `GET /linkedin-variants/pending-supervision` (no `/flow-a` prefix) | Less aligned with Flow A operator reads; easier to confuse with OAuth `/linkedin/...` and mutation POSTs |

**Apply gate:** Confirm no existing undocumented GET already returns the field list. If one exists, prefer it and drop the new route from implementation — otherwise implement the fixed path above.

### Decision 2: Minimal same-origin static operator page

**Choice:** Serve a single static HTML page from the worker at the fixed path `GET /flow-a/console/linkedin-variant-supervision` that fetches `GET /flow-a/linkedin-variants/pending-supervision` with the same-origin API key pattern (browser prompt or documented local-only config — **never** embed secrets in committed page source or docs).

**UI behavior (Story 1):**

- Table and/or sections grouped by `campaign_id` and, where calendar join exists, by calendar item / due date.
- Empty pending set → clear “no pending variants in supervision window” message (not an error).
- Partial failures → show successful rows plus visible issue list.
- Labels distinguish `pending` (supervision window) from LinkedIn API published; do not equate `flow_a_complete` with published.
- Links to docs: review policy, quality criteria, supervision mechanics (read-only guidance).
- No edit/defer/cancel controls (a plain-language note that actions arrive in US-039/US-040 is allowed — without secret-like placeholders).
- Committed HTML MUST NOT contain API keys, bearer tokens, or placeholders that look like secrets (e.g. `CHANGE_ME`, `sk-…`, `Bearer …`, sample key strings). Tests MUST fail the static asset if those patterns appear.

**Why static HTML over a SPA/framework:** Repo has zero frontend stack; adding React/Vite would be over-scope for Story 1. Static page matches “smallest coherent surface.”

**Alternatives considered:**

| Alternative | Trade-off |
|-------------|-----------|
| Markdown-only ops doc | Does not satisfy interactive calendar/campaign view without raw files |
| Separate thin Flask/Node app | Extra deploy topology; violates prefer-worker-HTTP simplicity |
| n8n UI form | Wrong host; ADR-0001 still requires worker for SoT; n8n is orchestrator not console SoT |

### Decision 3: Data aggregation rules

**Choice:** Scan `metadata/campaigns/*.json` under the editorial base path (reuse existing confined path helpers). Include a variant row when `publish_state == "pending"`. Sort primarily by `scheduled_at_utc` ascending, then `campaign_id`, then variant id. Join calendar items by exact `campaign_id` match when calendar loads successfully; if multiple calendar items share a campaign id, attach all matches or the best single match with an issue noting ambiguity — prefer deterministic first-by-`item_id` plus an issue flag rather than silent drop.

**Non-mutation invariant:** Aggregation MUST NOT write campaign or calendar files (mirror operational-status read-only discipline).

### Decision 4: Failure and blocked-state communication (read path only)

| Condition | Operator-visible treatment |
|-----------|----------------------------|
| No pending variants | Empty success with explanatory copy |
| Calendar missing/invalid | Variants still listed from campaigns; calendar join fields null; issue recorded |
| Campaign JSON unreadable | Issue per file; other campaigns still listed (`partial`) |
| Publication enablement false | Banner/context field — not a row filter; pending variants remain listed |
| Variant `failed` / `cancelled` / `queued` | Not in primary pending list (Story 1 scope); do not invent US-040 action panels |
| Auth failure | Existing 401 semantics |

Do not invent new `publish_state` values or treat criteria failure as a technical block.

### Decision 5: Docs and progress discipline

**Choice:** After demonstrated read-path behavior in tests (and optional local smoke), update CURRENT-STATE to record US-038 console **implemented / in progress** (not Story accepted unless operator acceptance is separately recorded). Progress-checklist: may check Story reviewed / Work started / Business outcome demonstrated when true; **MUST NOT** check Story accepted or BL-015 closed in this change.

## Risks / Trade-offs

- [Static page + API key UX] → Operators must supply the key safely (browser prompt / local-only storage). Mitigation: document header usage; never commit keys; prefer same-origin only; automated HTML secrets/placeholder audit in tests.
- [New GET increases API surface] → Mitigation: single read-only route; auth-required; no side effects; tests prove zero mutation.
- [Calendar join ambiguity] → Mitigation: deterministic rule + issue flag; do not invent reconciliation writes (defer calendar write-back remains US-017 note / later stories).
- [Scope creep into US-039/US-040] → Mitigation: UI explicitly omits action controls; tasks forbid calling mutation POSTs.
- [Confusion with operational-status] → Mitigation: separate path and capability name; CURRENT-STATE distinguishes observability vs supervision console.

## Migration Plan

1. Implement aggregation module + GET + static page behind existing Docker image (no new compose service).
2. Deploy only after explicit user approval (standard project discipline) — implementation alone is not live.
3. Rollback: remove route/static mount or revert image; no data migration (read-only).
4. No n8n workflow changes required for Story 1.

## Open Questions

_None._ Paths are fixed:

| Surface | Path |
|---------|------|
| Pending-supervision read API | `GET /flow-a/linkedin-variants/pending-supervision` |
| Operator console (static HTML) | `GET /flow-a/console/linkedin-variant-supervision` |
