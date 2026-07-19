## Why

Flow B weekly cadence needs a **detect-only** next-week LinkedIn gap sensor so operators (and later n8n) can see empty Mon–Sun coverage before the week starts. US-076 settings persistence is implemented, synced, archived, pushed, and deployed on `192.168.0.194:8010` (`BUILD_REVISION` `b89c429…`); US-074/US-075 policy is Story accepted and BL-016 is closed. US-077 is the next apply-order runtime step before discovery/draft/trigger stories.

## Goals

- Expose an authenticated worker gap-detect endpoint and/or dry-run diagnostic that scans the **next** operator-local week (Mon–Sun).
- Define a gap day as **0** LinkedIn posts in `pending` / `queued` / `published`; days with ≥1 are **not** gaps.
- Apply configurable `min_lead_days` (default **5**) from `load_gap_operator_settings()` (US-076 DB row when present; documented defaults when missing).
- Return a clear orchestration-friendly result: `gaps[]` / no-gap, target ISO week, operator timezone used.
- Detect-only MUST NOT mutate campaigns, calendar rows, drafts, or start discovery/draft generation.
- Treat empty coverage as a **proxy** for needing upstream content (not a filesystem inventory of `ready/` or `pending-approval/`).
- Document that detect MAY run for inspection even when `gap_trigger_enabled=false`; fail-closed auto-trigger semantics remain for US-082.
- Update CURRENT-STATE as **implemented** (not Story accepted without operator walkthrough); do **not** close BL-019.

## Non-goals

- Gap **trigger** / n8n Schedule activation / draft batch start (US-082).
- AI topic discovery or blog draft generation (US-078 / US-079).
- Blog approve/reject UI or promote-to-`ready/` / spill algorithm A (US-080 / US-081).
- Redefining gap as density (US-040K max-2 remains a scheduling capacity ceiling elsewhere — not the gap definition).
- Changing US-041 calendar SoT contracts for schedule rows.
- LinkedIn API publication or mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- n8n Execute Command (ADR-0001 unchanged — orchestration remains HTTP-only).
- Closing BL-019 or marking US-077 Story accepted without operator walkthrough.

## What Changes

- Add a detect-only gap sensor service that loads operator settings, resolves the next local Mon–Sun week, counts LinkedIn coverage per local day from existing calendar/campaign schedule visibility sources (US-041 SoT for schedule identity; LinkedIn `publish_state` membership aligned with pending/queued/published), applies `min_lead_days` / `gap_posts_threshold`, and returns structured gaps.
- Add an authenticated worker HTTP endpoint (and dry-run / diagnostic semantics as needed) under a Flow B path so operators can inspect the next-week gap result without triggering drafts.
- Document detect-vs-trigger: inspection allowed when `gap_trigger_enabled=false`; auto-trigger remains fail-closed until US-082.
- Update ops / CURRENT-STATE to record gap detect as implemented (not Story accepted / BL-019 still open).
- Tests covering gap/no-gap, lead-day filtering, settings defaults, auth, and non-mutation.

## Capabilities

### New Capabilities

- `flow-b-calendar-gap-detect`: Authenticated detect-only next-week LinkedIn calendar gap sensor; settings-driven timezone / `min_lead_days` / threshold; structured `gaps[]` result; no campaign/draft mutation; detect allowed when trigger disabled.

### Modified Capabilities

- `flow-b-simplified-process`: Cross-link that US-077 runtime detect now exists as a separate capability (policy gap semantics unchanged; docs MUST NOT claim trigger/discovery/draft implemented).
- `flow-b-gap-operator-settings`: Clarify that `load_gap_operator_settings()` is consumed by the gap-detect path; settings persist/UI contracts unchanged; detect MUST NOT require `gap_trigger_enabled=true`.

## Impact

- **Code:** New gap-detect module (reuse settings loader + existing LinkedIn/schedule coverage enumeration patterns such as schedule-visibility / local-day bucketing); authenticated route in `main.py`; unit/API tests with fixtures (no real LinkedIn/DeepSeek/ComfyUI).
- **APIs:** New authenticated Flow B detect endpoint (e.g. `GET` or `POST /flow-b/calendar-gaps`); settings GET/PUT unchanged; no trigger route.
- **Deps:** Existing Postgres calendar + settings stores; no new external services.
- **Ops:** CURRENT-STATE + Flow B policy note that detect is implemented; Story accepted / BL-019 close remain operator gates.
- **Product:** **BL-019 / US-077** primary. Does not close BL-019; does not implement US-078–US-082.
- **Acceptance criteria addressed (US-077):** Next-week scan; gap=0 vs ≥1; `min_lead_days`; clear result shape; settings load; empty coverage as proxy (docs); authenticated inspect endpoint; non-mutation; US-040K density not redefined as gap.
- **Acceptance criteria excluded / deferred:** Operator walkthrough “outcome visible” Story accepted gate; US-082 trigger; discovery/draft/approve/promote; LinkedIn API publish.

## Related backlog / stories

| ID | Role |
|----|------|
| **BL-019 / US-077** | Primary — detect upcoming LinkedIn calendar gaps |
| US-076 | Prerequisite — settings persistence (deployed; Story accepted pending walkthrough) |
| US-074 / US-075 / BL-016 | Prerequisite policy (Story accepted; closed) |
| US-082 | Later — trigger on gaps (out of scope) |
| US-078–US-081 | Later — discovery/draft/approve/promote (out of scope) |
| US-041 / BL-031 | Calendar SoT remains authoritative for schedule rows — untouched contracts |
| US-040K | Max-2 density ceiling elsewhere — not the gap definition |
