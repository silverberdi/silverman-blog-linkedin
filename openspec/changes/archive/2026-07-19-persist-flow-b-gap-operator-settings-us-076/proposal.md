## Why

Flow B weekly gap cadence (Friday-local look-ahead, lead days, draft caps, fail-closed auto-trigger) is locked in policy (US-074/US-075) but has no durable operator-editable SoT yet. Env-only knobs bury Friday/look-ahead behavior and cannot be safely tuned from Silverman Authority Manager. Why now: US-074/US-075 are Story accepted and BL-016 is closed; US-076 is the next apply-order step before gap detect (US-077) and later trigger/discovery/approve stories.

## Goals

- Persist Flow B gap operator settings in Postgres (`silverman_linkedin_db` or a documented sibling store on the same deployment), not as long-term env-only SoT.
- Expose authenticated GET/PUT (or equivalent) worker HTTP APIs and an Authority Manager UI to view/update the locked key set with validation.
- Ensure worker/sensor read paths resolve DB settings when present and documented defaults when a row is missing.
- Keep `gap_trigger_enabled` default **false** (fail-closed); saving settings MUST NOT enable LinkedIn API publish or bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- Ship local implementation + full OpenSpec cycle only — no deploy in this change.

## Non-goals

- Gap detect endpoint / sensor logic (US-077).
- n8n Schedule trigger or auto draft generation (US-082).
- AI topic discovery or draft writing (US-078 / US-079).
- Blog approve/reject UI or promote-to-`ready/` (US-080 / US-081).
- Spill algorithm A runtime scheduling (US-081).
- Changing calendar SoT / US-041 contracts for schedule rows.
- Enabling LinkedIn API publication; mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- Deploy to `192.168.0.194` or live activation.
- n8n Execute Command (ADR-0001 unchanged — any future orchestration remains HTTP-only).

## What Changes

- Add a Postgres-backed operator-settings store (table/document in `silverman_linkedin_db` or documented sibling) for the US-076 key set with documented defaults.
- Add authenticated worker HTTP read/update endpoints for those settings (secret-safe responses; structured validation errors).
- Extend **Silverman Authority Manager** (existing LinkedIn supervision console product surface) with an authenticated settings view/edit UI — not a separate Flow B app.
- Provide an internal read helper so future sensor/trigger paths (US-077+) load DB settings with defaults; this change wires the helper and may optionally prefer DB `operator_timezone` where density already resolves timezone, without implementing gap detect.
- Update CURRENT-STATE / ops docs to record settings persistence as implemented (not Story accepted until operator AC walk); product checklist remains in-progress for US-076 until demonstrated.

## Capabilities

### New Capabilities

- `flow-b-gap-operator-settings`: Persist, validate, authenticate, and UI-edit Flow B gap operator settings in Postgres; documented defaults; fail-closed `gap_trigger_enabled`; secret-safe; no LinkedIn publish enablement by save; read helper for worker/sensor consumers.

### Modified Capabilities

- `flow-b-simplified-process`: Clarify that US-076 runtime settings store/UI now exists as a separate capability (policy remains authoritative for defaults/semantics; cross-link no longer “intent only”).
- `linkedin-variant-supervision-console`: Extend Silverman Authority Manager shell with authenticated access to Flow B gap operator settings (navigation/surface only; no gap detect/approve flows).

## Impact

- **Code:** New settings store module (patterned on `editorial_calendar_store`), validation models, HTTP routes in `main.py`, frontend console settings panel + API client, unit/integration tests with `memory://` or equivalent.
- **APIs:** New authenticated settings GET/PUT under a Flow B / operator-settings path; existing calendar and LinkedIn mutation contracts unchanged.
- **Deps:** Reuse existing `psycopg` + `SILVERMAN_CALENDAR_DATABASE_URL` (or sibling env targeting same DB); no new external services.
- **Ops:** Schema ensure on first use / startup path; secrets remain env-only; no deploy in this change.
- **Product:** **BL-019 / US-076** primary. Does not close BL-019 or advance US-077–US-082 implementation.
- **Acceptance criteria addressed (US-076):** Postgres persistence; full key set + defaults; authenticated Authority Manager UI with validation; worker read path + defaults when missing; no secrets; save does not enable LinkedIn publish; `gap_trigger_enabled=false` fail-closed; calendar SoT unchanged.
- **Acceptance criteria excluded:** Gap detect (US-077); trigger (US-082); discovery/draft (US-078/079); approve/promote (US-080/081); live deploy/Story accepted walkthrough (operator gate after apply).

## Related backlog / stories

| ID | Role |
|----|------|
| **BL-019 / US-076** | Primary — persist/edit gap operator settings |
| US-074 / US-075 / BL-016 | Prerequisite policy (Story accepted; closed) |
| US-077 | Next — reads US-076 settings for gap detect |
| US-041 / BL-031 | Calendar SoT remains authoritative for schedule rows — untouched |
| US-040K | `density_max_per_local_day` mirrors interim max-2 until BL-021 |
