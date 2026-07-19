## Why

Simplified Flow B needs an authenticated worker step that proposes **authority-aligned** blog theses (leadership / architecture / transformation / AI referent) before draft generation. US-077 gap detect and US-076 settings are implemented and deployed on `192.168.0.194:8010`; discovery is the next apply-order runtime capability so a future gap batch (US-082) can request topics without a mandatory BL-020 CMS or news-chase RSS feeds.

## Goals

- Provide an authenticated worker AI topic-discovery capability constrained by the career/authority objective; MUST NOT optimize for “X vs Y”, “what’s new”, or headline rebroadcast.
- v1 uses **DeepSeek only** for discovery calls; leave a clear **provider-pluggable** client seam so later models can be enabled without rewriting Flow B.
- Discovery inputs v1: authority brief + editorial canon topic spaces + soft anti-dup vs recent published blogs; optional durable primary material for thesis formation — **not** RSS/news APIs as primary driver.
- Do **not** require a hand-curated BL-020 backlog to run.
- Accept optional gap-batch context (target ISO week + `empty_days[]`) as informational for future US-082 callers; MUST NOT invent filesystem inventory requirements.
- Support producing up to N distinct topic choices in one batch (N ≤ `max_drafts_per_weekly_run` from `load_gap_operator_settings()`, default 2).
- Surface each chosen topic (thesis + why it positions as referent + brief rationale) in a shape suitable for attachment to each draft package (US-079).
- Fail closed with a clear operator-visible error when discovery cannot produce an objective-aligned topic.
- ADR-0001: n8n → worker HTTP only; no Execute Command.
- Update CURRENT-STATE as **implemented** (not Story accepted without operator walkthrough); do **not** close BL-017.

## Non-goals

- Blog draft generation or hero image creation (US-079).
- Writing to `blog-posts/ready/` or `blog-posts/pending-approval/` (discovery only — no draft filesystem writes).
- Approve/reject UI or promote-to-`ready/` / spill algorithm A (US-080 / US-081).
- Gap trigger / n8n Schedule activation / draft batch orchestration (US-082).
- Changing US-077 gap-detect or US-076 settings persist/UI contracts (consume `max_drafts_per_weekly_run` only).
- Hard anti-dup engine, thematic duplication engines, or audience-balancing schedulers.
- RSS/news APIs as primary discovery driver; “top stories this week” prompts.
- LinkedIn API publication or mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- Closing BL-017 or marking US-078 Story accepted without operator walkthrough.

## What Changes

- Add an authenticated Flow B topic-discovery worker HTTP endpoint that runs AI discovery (DeepSeek v1), returns structured topic choices (or a clear fail-closed error), and does not write draft packages to disk.
- Introduce a small **provider-pluggable** discovery client seam; wire DeepSeek as the only v1 implementation; reuse existing DeepSeek config/env loading patterns where practical.
- Assemble discovery prompts from authority brief + editorial canon topic spaces + soft anti-dup signals from recent published blogs; optionally include durable primary material when present; never require BL-020 backlog files.
- Cap batch size with `max_drafts_per_weekly_run` from `load_gap_operator_settings()` (default 2); accept optional `target_week` / `empty_days[]` context without treating them as filesystem inventory.
- Update ops / CURRENT-STATE / Flow B policy cross-links so discovery is recorded as implemented (not Story accepted / BL-017 still open).
- Tests covering authority constraint, batch cap, optional gap context, BL-020-not-required, fail-closed paths, auth, and no draft-folder writes (mock DeepSeek; no real external calls).

## Capabilities

### New Capabilities

- `flow-b-topic-discovery`: Authenticated worker AI topic discovery for Flow B; DeepSeek v1 with provider-pluggable seam; authority-constrained thesis outputs (not news chase); optional gap-batch context; batch size ≤ `max_drafts_per_weekly_run`; fail-closed operator-visible errors; no draft filesystem writes.

### Modified Capabilities

- `flow-b-simplified-process`: Cross-link that US-078 runtime discovery now exists as a separate capability (policy discovery posture unchanged; docs MUST NOT claim draft/approve/trigger implemented).
- `flow-b-gap-operator-settings`: Clarify that `max_drafts_per_weekly_run` (via `load_gap_operator_settings()`) is consumed as the discovery batch ceiling; settings persist/UI contracts unchanged.

## Impact

- **Code:** New topic-discovery module + provider seam (DeepSeek adapter); authenticated route in `main.py`; prompt assembly from editorial/authority sources; soft anti-dup read of recent published blogs; unit/API tests with mocked DeepSeek.
- **APIs:** New authenticated Flow B discovery endpoint (e.g. `POST /flow-b/discover-topics`); gap-detect and settings GET/PUT unchanged; no draft/trigger routes.
- **Deps:** Existing DeepSeek env config; settings loader; no new mandatory external services beyond DeepSeek already used for LinkedIn drafts.
- **Ops:** CURRENT-STATE + Flow B policy note that discovery is implemented; Story accepted / BL-017 close remain operator gates.
- **Product:** **BL-017 / US-078** primary (discovery half only). Does not close BL-017; does not implement US-079–US-082.
- **Acceptance criteria addressed (US-078):** Authority-constrained discovery; DeepSeek v1 + pluggable seam; inputs (brief/canon/anti-dup/optional primary); BL-020 not required; optional gap context; batch ≤ max drafts; topic surface for draft attachment; fail closed; ADR-0001 HTTP; no unintended change to gap detect/settings contracts.
- **Acceptance criteria excluded / deferred:** Operator walkthrough “outcome visible” Story accepted gate; US-079 draft package write; US-080/081 approve/promote; US-082 trigger; LinkedIn API publish.

## Related backlog / stories

| ID | Role |
|----|------|
| **BL-017 / US-078** | Primary — discover current objective-aligned topics with AI |
| US-076 | Prerequisite — settings (`max_drafts_per_weekly_run`) |
| US-077 | Prerequisite — gap detect (optional context shape for later US-082) |
| US-074 / US-075 / BL-016 | Prerequisite policy (Story accepted; closed) |
| US-079 | Later — draft generation into `pending-approval/` (out of scope) |
| US-080 / US-081 | Later — approve/promote (out of scope) |
| US-082 | Later — gap trigger invoking discovery (out of scope) |
| BL-020 | Optional enrichment only — MUST NOT be required |
