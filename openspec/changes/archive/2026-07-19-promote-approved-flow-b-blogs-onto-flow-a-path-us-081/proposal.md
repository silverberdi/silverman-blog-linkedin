## Why

US-080 is implemented and deployed: operators can approve/reject Flow B drafts in Silverman Authority Manager, but approve only records sidecar `status=approved` with `promoted:false` / `promotion_pending:true` — files stay under `blog-posts/pending-approval/`. Without US-081 promote, approved AI blogs never become Flow A–eligible, and LinkedIn scheduling never applies locked spill algorithm A under US-040K max 2.

## Goals

- Authenticated **promote** action for already-approved pending-approval drafts: confirm/complete durable approval metadata (who/when/draft id) and move the Markdown + image pair (plus appropriate Flow B metadata) from `blog-posts/pending-approval/` → `blog-posts/ready/`.
- After promotion, blog publish / LinkedIn package / schedule / optional supervision MUST **reuse Flow A** behavior — no second mandatory LinkedIn approval queue for Flow B.
- When scheduling LinkedIn variants from an approved Flow B blog, apply **spill algorithm A**: (1) target-week gap days chronological (max 2) → (2) other days in target week with remaining capacity → (3) forward day-by-day after the week under US-040K max 2.
- Unapproved drafts in `pending-approval/` MUST NOT be accepted by Flow A publish paths.
- ADR-0001: n8n → worker HTTP only.
- Tests + CURRENT-STATE as **implemented** (not Story accepted); do **not** close BL-018 without US-080+US-081 Story accepted.

## Non-goals

- US-082 gap trigger orchestration.
- Auto-publish blog or LinkedIn without Flow A guards / enablement flags.
- Revision-history CMS or multi-round feedback (US-080 non-goals remain).
- Re-implementing US-080 approve/reject presentation or decision-only approve semantics.
- Marking US-081 Story accepted without operator walkthrough.
- Closing BL-018; changing US-076–US-079 generation/detect/settings contracts beyond consuming their artifacts.
- Redefining gap detection (gap=0 remains US-077; US-040K max 2 is scheduling capacity only).

## What Changes

- Add authenticated worker HTTP **promote** for approved drafts under `blog-posts/pending-approval/` that moves `.md` + `.png` (+ Flow B sidecar/provenance metadata) into `blog-posts/ready/` and records durable promotion evidence (who/when/draft id; completes US-080 approve handoff).
- Extend Silverman Authority Manager so operators can promote an approved draft (clear promoted vs approved-but-not-promoted vs rejected states); do not replace US-080 approve/reject.
- Ensure Flow A publish/package/schedule/supervision paths consume promoted `ready/` content as Flow A — no mandatory second LinkedIn review queue for Flow B origin.
- Extend LinkedIn distribution scheduling so Flow B–origin campaigns with gap context apply spill algorithm A under US-040K local-day density max 2.
- Explicitly reject Flow A publish (and related ready-inbox acceptance) of paths under `blog-posts/pending-approval/` or unapproved drafts.
- Update ops / CURRENT-STATE / Flow B policy cross-links so promote + spill A runtime is recorded as implemented (not Story accepted); BL-018 remains open until US-080+US-081 Story accepted.
- Tests covering promote move + metadata, Flow A reuse, spill A placement, pending-approval rejection, auth, and failure communication (no real LinkedIn/Git publish calls).

## Capabilities

### New Capabilities

- `flow-b-blog-draft-promotion`: Authenticated promote of approved `pending-approval/` packages to `blog-posts/ready/`; durable approval/promotion metadata; Authority Manager promote affordance; Flow A path reuse after promotion (no second mandatory LinkedIn gate); spill algorithm A when scheduling LinkedIn variants from Flow B–origin blogs under US-040K max 2; fail-closed rejection of unapproved `pending-approval/` by Flow A publish paths; ADR-0001 HTTP-only.

### Modified Capabilities

- `flow-b-blog-draft-approval`: Complete the US-080 → US-081 handoff — approve remains decision-only; promote is a separate authenticated action; UI/docs communicate approved-not-promoted vs promoted; no re-implementation of list/approve/reject core.
- `flow-b-simplified-process`: Cross-link that US-081 runtime promote + spill A now exists as a separate capability (policy algorithm A unchanged; docs MUST NOT claim US-082 trigger implemented).
- `linkedin-distribution-scheduling-model`: When scheduling variants for a Flow B–origin promoted blog (gap context present), apply spill algorithm A under US-040K density max 2 instead of (or as the selected strategy for) default Flow A stagger-only placement for that origin; campaign remains Flow A lifecycle (`flow_a`) after promotion.
- `worker-blog-publishing-endpoint`: Fail closed when `source_relative_path` (or equivalent) targets `blog-posts/pending-approval/` or otherwise unapproved Flow B drafts — MUST NOT publish from that folder.

## Impact

- **Code:** New Flow B promote module(s); thin FastAPI promote route under `/flow-b/…`; schedule-strategy / density integration for spill A; Authority Manager promote control; tests; explicit pending-approval rejection on publish/queue acceptance paths as needed.
- **APIs:** New authenticated promote endpoint; existing approve/reject/list/generate/detect/settings contracts unchanged in purpose; Flow A publish/package/schedule reused (no parallel Flow B LinkedIn approval API).
- **Deps:** US-080 sidecar approve fields; US-079 pair + `.flow-b.json` (including optional `target_week` / `empty_days[]`); US-040K `local_day_density`; US-076 `density_max_per_local_day` default 2; same worker API-key auth.
- **Ops:** CURRENT-STATE + Flow B policy note promote + spill A implemented; Story accepted / BL-018 close remain operator gates.
- **Product:** **BL-018 / US-081** primary (promote + spill A). Does not close BL-018; does not implement US-082.
- **Acceptance criteria addressed (US-081):** Record approval metadata; promote to `ready/`; reuse Flow A after promotion; spill algorithm A; unapproved pending-approval rejected by Flow A publish; outcome and failures communicated; no unintended duplication of Flow A guards / density.
- **Acceptance criteria excluded / deferred:** Operator walkthrough Story accepted gate; US-082 gap trigger; auto-publish without Flow A guards; closing BL-018.

## Related backlog / stories

| ID | Role |
|----|------|
| **BL-018 / US-081** | Primary — promote approved Flow B blogs onto Flow A path + spill A |
| US-080 | Prerequisite — approve/reject presentation (deployed; not Story accepted) |
| US-079 | Prerequisite — packages in `pending-approval/` |
| US-077 / US-076 | Gap context + density knobs when present |
| US-074 / US-075 / BL-016 | Prerequisite policy (Story accepted; closed) |
| US-040K | Authoritative local-day density max 2 after promotion |
| US-082 | Later — gap trigger (out of scope) |
