# Tasks: confirm-linkedin-preview-rendering-us-024

## 1. Pre-implementation inspection

- [x] 1.1 Re-read canonical specs `linkedin-article-preview-verification` (US-023 boundary and stable codes), `linkedin-article-preview-image-support` (`article_preview` metadata fields), and `linkedin-retry-recovery-classification` (procedure-as-spec precedent and evidence-language conventions) to confirm the new procedure references — and never redefines — their contracts.
- [x] 1.2 Re-read `docs/deployment/linkedin-publication-prerequisites.md` §"Article preview input verification (US-023)" and §"Post format (v1)" to anchor the procedure on the real v1 post shape (text-only, URL in commentary, no `content.article`) and the existing US-024 boundary pointer. Confirm zero changes are needed under `src/`, `tests/`, `n8n/`, `deploy/`.

## 2. Operations procedure document

- [x] 2.1 Create `docs/operations/linkedin-preview-rendering-confirmation.md` with: purpose and US-023/US-025 boundaries; prerequisites (passing US-023 run for the campaign, live-site confirmation, browser access to LinkedIn Post Inspector); the two observation points (pre-publish Post Inspector inspection, post-publish real-post observation with `linkedin_post_urn` reference).
- [x] 2.2 Add the cache-vs-input decision matrix (per design D3) covering all five outcome classes — `preview_confirmed`, `preview_stale_cache`, `preview_inputs_incorrect`, `preview_not_rendered_post_format`, `confirmation_blocked` — with the next action per class and the explicit note that stale-vs-wrong is decided by the US-023 result, never re-derived manually.
- [x] 2.3 Add the safe re-scrape procedure (per design D5): US-023 re-verification before re-scrape; Post Inspector re-inspection as the only refresh mechanism; forbidden actions (publishing test posts, cache-busting URL parameters); non-normative cache-lag context (TTL undocumented); explicit "new posts only — existing posts keep the old card" limit with US-025 boundary for reacting to an already-published stale card.
- [x] 2.4 Add blocked-state table (input verification not run/failed/not trusted, site not live, Post Inspector unavailable, no published variant for post-publish observation) with next action per state, and the per-confirmation evidence-record template (campaign id, `public_url`, US-023 run reference, Post Inspector observation with UTC timestamp, post-publish observation when applicable, outcome label, operator + UTC timestamp; no secrets, no LinkedIn session data, no variant body text; campaign metadata never edited).

## 3. Cross-document updates

- [x] 3.1 Update `docs/deployment/linkedin-publication-prerequisites.md`: in the US-023 section, replace the bare "Those are US-024" boundary sentence with a link to the new rendering-confirmation procedure; add a short pointer from §"Post format (v1)" noting that actual card rendering for v1 text posts is confirmed via the US-024 procedure.
- [x] 3.2 Update `docs/CURRENT-STATE.md`: record the US-024 procedure under a "defined" status with qualified language (procedure defined ≠ operationally validated ≠ accepted; no worker code; BL-009 open), alongside the existing US-023 entry; adjust the canonical spec count if tracked.
- [x] 3.3 Update `docs/product/user-stories.md` US-024: map each acceptance criterion to its mechanism (procedure section / spec requirement) at procedure-defined scope only; state explicitly that acceptance requires operator demonstration on a real campaign and depends on US-023 deploy + operational validation (archived US-023 task 6.2, still pending). Update `docs/product/progress-checklist.md` US-024 rows only for states actually reached (story reviewed, acceptance criteria agreed, work started); leave demonstration/acceptance unchecked; BL-009 stays open.

## 4. Verification

- [x] 4.1 Run `openspec validate "confirm-linkedin-preview-rendering-us-024" --strict` and resolve any findings.
- [x] 4.2 Run `git diff --check` (whitespace) and a secrets scan over the new/changed docs; full pytest not required (docs + spec only, no executable code changed) — record that justification in the verification notes.

## Verification notes (2026-07-17)

- `openspec validate "confirm-linkedin-preview-rendering-us-024" --strict` — **passed** ("Change ... is valid").
- `git diff --check` — **clean** (no whitespace errors).
- Secrets scan over new/changed docs (`linkedin-preview-rendering-confirmation.md`, prerequisites, CURRENT-STATE, user-stories, progress-checklist) — **clean**; only prohibition language ("no secrets / no session cookies") matches, no secret values, tokens, or credentials added.
- **Full pytest not run — justified:** this change is docs + canonical procedure-spec only. Zero changes under `src/`, `tests/`, `n8n/`, `deploy/` (confirmed via `git status --porcelain`: only `docs/` files and this change directory touched). Per engineering standards, full pytest is required only when executable code changes.
- Task 5.1 (operational demonstration) intentionally **not executed** in this apply: approval-gated and dependent on US-023 deploy + operational validation on `192.168.0.194`.

## 5. Business validation gate (post-implementation, approval-gated)

- [ ] 5.1 Operational demonstration (outside this change's implementation commit; requires explicit operator approval and depends on US-023 deploy + operational validation on `192.168.0.194`): execute the procedure end-to-end on a real campaign — passing US-023 real run, Post Inspector confirmation, decision-matrix classification, and a completed evidence record; only then update US-024 acceptance criteria, user-story status, and progress-checklist demonstration items. Do not close BL-009 (US-023 acceptance and US-025 remain open).
