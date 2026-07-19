## Context

US-074/US-075 locked simplified Flow B policy (weekly next-week gap sensor, Friday-local run intent, fail-closed `gap_trigger_enabled`, max 2 drafts). Runtime settings do not exist yet; density and console paths today use request `operator_timezone` or env `SILVERMAN_OPERATOR_TIMEZONE` only.

Postgres database `silverman_linkedin_db` already hosts the editorial calendar (US-041 / `editorial_calendar_store`). Silverman Authority Manager is the Vite React console at `GET /flow-a/console/linkedin-variant-supervision`, authenticated via the same API-key session pattern as other worker routes.

Constraints: ADR-0001 (n8n → HTTP only); no secrets in responses; `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` remains the LinkedIn publish guard; calendar item SoT unchanged; no deploy in this change; US-077+ consume settings but are out of scope.

Stakeholders: content operator (edit Friday/look-ahead knobs in Authority Manager); system operator (DB schema on same Postgres); future US-077/US-082 implementers (stable read helper).

## Goals / Non-Goals

**Goals:**

- Durable single-row (or keyed singleton) operator-settings document in `silverman_linkedin_db`.
- Documented defaults applied when no row exists; DB values win when present.
- Authenticated HTTP GET + PUT (or PATCH) with validation.
- Authenticated Authority Manager UI to view/update settings with clear errors.
- Internal `load_gap_operator_settings()` (name flexible) used by HTTP handlers and ready for US-077+.
- Fail-closed defaults: `gap_trigger_enabled=false`; save MUST NOT flip LinkedIn publish enablement.

**Non-Goals:**

- Gap detect, trigger, discovery, draft, approve/promote (US-077–US-082).
- Changing calendar tables or US-041 load/save semantics.
- Dual-write to env as SoT; env remains optional bootstrap fallback for timezone only where existing density APIs already allow it.
- Deploy / live Story acceptance walkthrough.

## Decisions

### D1 — Same database `silverman_linkedin_db`, new table

**Choice:** Store settings in Postgres database **`silverman_linkedin_db`** (same as calendar) in a new table e.g. `flow_b_gap_operator_settings` (singleton `settings_id='default'`), reusing `SILVERMAN_CALENDAR_DATABASE_URL` (or an alias env that MUST target the same DB name). Document that a sibling DB on the same deployment is only allowed if explicitly named and justified; default is same DB.

**Why:** US-076 AC allows `silverman_linkedin_db` or documented sibling; same DB avoids a second secret/URL, shares backup runner, and matches operator planning notes.

**Alternatives:**

| Option | Rejected because |
|--------|------------------|
| Env-only long-term SoT | Violates US-076 AC |
| Separate sibling DB by default | Extra ops without benefit for a singleton row |
| Filesystem JSON under editorial mount | Same wipe class as pre-US-041 calendar |

### D2 — Singleton document + typed columns / JSONB extras

**Choice:** One row with explicit columns (or JSONB payload validated at the boundary) for:

| Key | Default | Validation |
|-----|---------|------------|
| `operator_timezone` | Prefer existing `SILVERMAN_OPERATOR_TIMEZONE` if valid IANA when seeding first save; otherwise require valid IANA on write; read-with-defaults MAY surface env as effective timezone when row missing | IANA zoneinfo |
| `gap_trigger_enabled` | `false` | boolean |
| `gap_scan_mode` | `next_week` | enum (`next_week` only in v1) |
| `weekly_run_local_day` | `friday` | enum Mon–Sun lowercase |
| `weekly_run_local_time` | `15:00` | `HH:MM` 24h |
| `min_lead_days` | `5` | non-negative int |
| `gap_posts_threshold` | `0` | non-negative int |
| `max_drafts_per_weekly_run` | `2` | non-negative int (≥1 recommended but AC says non-negative) |
| `density_max_per_local_day` | `2` | non-negative int |

Include `updated_at_utc` and optional `row_version` for optimistic concurrency on PUT.

**Why:** Matches locked planning-notes key list; validates at HTTP edge; mirrors calendar store patterns.

### D3 — Defaults when row missing (not fail-closed empty)

**Choice:** `load_gap_operator_settings()` returns a fully populated settings object: if no row, apply documented defaults (`gap_trigger_enabled=false`, etc.). Store unavailability (misconfigured/unreachable DB) fails closed for **write** and for GET that requires live store when configured; for unit tests use `memory://` like calendar. When DB URL is unset in test/dev, memory store or in-process defaults are allowed.

**Why:** US-076: “documented defaults apply when a row is missing.” Sensor paths (US-077) must not crash on first boot before an operator saves.

**Note:** This differs from calendar’s “no invent items” rule — settings are a closed known key set with policy defaults, not open-ended schedule data.

### D4 — HTTP surface

**Choice:**

- `GET /flow-b/gap-operator-settings` — authenticated; returns effective settings + metadata (`source: defaults|database`, `updated_at_utc` nullable when defaults-only).
- `PUT /flow-b/gap-operator-settings` — authenticated; full-document replace of known keys; validation errors → 422 with stable codes; success returns saved document.
- Optional: `If-Match` / `expected_row_version` for concurrency (prefer if cheap; otherwise last-write-wins with `updated_at_utc` visible).

No gap-detect or trigger routes in this change.

**Why:** Clear Flow B namespace; ADR-0001; console uses same-origin typed client + existing auth injection.

### D5 — Authority Manager UI extension

**Choice:** Add a settings surface inside the existing console package (`frontend/linkedin-variant-supervision-console`): e.g. header control or secondary view “Gap settings” / “Flow B settings” that loads GET and saves PUT. Reuse session/`canMutate` patterns. Do **not** create a separate SPA or route tree outside the worker-served console.

**Why:** Glossary: Silverman Authority Manager extends the supervision console; US-076 forbids a separate Flow B app.

**UX:** Plain labels for timezone, enable auto-trigger (default off warning), Friday/time, lead days, caps. Show validation errors inline; never show API keys or LinkedIn tokens. Saving with `gap_trigger_enabled=true` MUST show a clear warning that detect/trigger are separate capabilities and LinkedIn publish remains guarded by env — but MUST NOT claim trigger is live until US-082.

### D6 — Relationship to `SILVERMAN_OPERATOR_TIMEZONE` and density

**Choice:** DB `operator_timezone` becomes the preferred SoT for Flow B gap settings consumers. Existing US-040K density mutation APIs keep request-field-or-env behavior unchanged in this change (no requirement to rewrite every density call). Optional small improvement: console may prefill mutation `operator_timezone` from loaded settings — nice-to-have, not required for US-076 AC.

**Why:** Avoid scope creep into US-040K contracts; US-077 will read settings helper.

### D7 — LinkedIn publish and secrets

**Choice:** Settings handlers MUST NOT read/return LinkedIn tokens, DeepSeek keys, or DB passwords. PUT MUST NOT set or imply `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`. Response MAY include a read-only boolean echo of current publish-guard state from env for operator clarity (optional); MUST NOT allow changing it via this API.

**Why:** Explicit US-076 AC and project secret rules.

### D8 — Schema ensure

**Choice:** `ensure_schema()` on first store access (same pattern as calendar store), idempotent `CREATE TABLE IF NOT EXISTS`. No Alembic required for a singleton table unless project already mandates it for calendar (calendar uses inline SCHEMA_SQL — match that).

**Why:** Smallest coherent diff consistent with existing Postgres adapter.

### D9 — Tests

**Choice:** Unit tests for validation (IANA, time, enums, non-negative ints), defaults-when-missing, round-trip save/load with memory store, auth required, secret-free responses, PUT does not enable LinkedIn publish flag. Frontend tests for settings form validation and error display. No real Postgres required in CI if memory store covers contracts; optional Postgres mark if already available in suite.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Operators enable `gap_trigger_enabled` before US-082 exists | Default false; UI warns; no trigger route in this change — enablement is inert until US-082 |
| Confusion between DB timezone and env timezone | Document precedence: DB row > documented defaults; density APIs unchanged; ops doc notes dual paths until US-077+ |
| Same DB URL used for calendar + settings — calendar misconfig blocks settings | Shared fail-closed when URL invalid; memory store for tests; health MAY report settings store readiness additively |
| Scope creep into gap detect | Specs/tasks explicitly forbid US-077 routes |

## Migration Plan

1. Implement store + HTTP + UI + tests locally.
2. `/opsx-verify` → implementation commit → sync → archive (separate commits).
3. Deploy (out of scope): ensure `SILVERMAN_CALENDAR_DATABASE_URL` reaches `silverman_linkedin_db`; schema auto-ensures; no data migration (empty → defaults).
4. Rollback: revert worker build; table may remain unused; no calendar impact.

## Open Questions

None blocking. Resolved by proposal/AC:

- DB name: prefer `silverman_linkedin_db` (D1).
- UI host: existing Authority Manager console (D5).
- Concurrency: optional `row_version`; implement if low cost during apply.
