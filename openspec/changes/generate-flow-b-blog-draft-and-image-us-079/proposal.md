## Why

US-078 topic discovery is implemented and deployed: the worker can return authority-aligned topic choices (`thesis`, `referent_positioning`, `rationale`, `topic_id`) but cannot yet materialize approval-ready blog packages. US-079 is the next apply-order runtime step so operators (and future US-082 gap batches) can receive complete Markdown + hero image pairs in `blog-posts/pending-approval/` without any publication side effects.

## Goals

- Provide an authenticated worker capability to generate a complete blog draft + hero image from discovered topic(s).
- Accept US-078 `topics[]` payload and optional gap context (`target_week`, `empty_days[]`).
- v1 DeepSeek text generation with a provider-pluggable seam consistent with US-078 (`topic_discovery_provider` pattern).
- Hero image via existing ComfyUI blog image path (`blog_image_generation.py` / `comfyui_client`); respect ComfyUI enablement flags; honor `dry_run` when specified.
- Write Markdown + image pair to `blog-posts/pending-approval/` only (same pair rules as `ready/`).
- Include durable metadata linking `topic_id` and optional gap batch / ISO week.
- Batch up to `max_drafts_per_weekly_run` when invoked with multiple topics (future US-082 gap batch).
- Apply editorial canon + anti-AI-writing rules at draft time (warnings or blocking per canon).
- ADR-0001: n8n → worker HTTP only.
- Update CURRENT-STATE as **implemented** (not Story accepted without operator walkthrough); do **not** close BL-017.

## Non-goals

- Writing to `blog-posts/ready/`.
- Auto-publish blog or LinkedIn; Flow A publish/package/schedule; LinkedIn API publish.
- US-080/081 approve/promote UI; US-082 gap trigger.
- Changing US-078 `discover-topics`, US-077 gap-detect, or US-076 settings contracts except consuming shared settings (`max_drafts_per_weekly_run`).
- Closing BL-017 or marking US-079 Story accepted without operator walkthrough.
- US-080–US-082 implementation or checklist closure.

## What Changes

- Add an authenticated Flow B blog-draft-generation worker HTTP endpoint that accepts one or more US-078 topic objects (and optional gap context), generates blog Markdown via DeepSeek v1, requests a hero image via the existing ComfyUI blog image path, and writes `.md` + `.png` pairs under `blog-posts/pending-approval/` with durable sidecar metadata (`topic_id`, optional `target_week` / gap batch fields).
- Introduce a provider-pluggable **blog draft generation** seam (mirroring `TopicDiscoveryProvider`); wire DeepSeek as the only v1 implementation; reuse `deepseek_config` / `deepseek_client` patterns.
- Reuse path-generation conventions from `draft_writer.py` (adapted for `pending-approval/`); reuse `blog_image_generation` for hero images with ComfyUI enablement guards and dry-run semantics.
- Apply editorial canon at prompt assembly; run anti-AI-writing heuristics per canon (blocking for Flow B generated content, not warnings-only).
- Cap batch size with `max_drafts_per_weekly_run` from `load_gap_operator_settings()` (default 2).
- Update ops / CURRENT-STATE / Flow B policy cross-links so draft generation is recorded as implemented (not Story accepted); BL-017 remains open.
- Tests covering happy path, batch cap, gap metadata, editorial/anti-AI gates, ComfyUI disabled/dry-run, auth, no `ready/` writes, no Flow A / LinkedIn publish calls (mock DeepSeek + ComfyUI; no real external calls).

## Capabilities

### New Capabilities

- `flow-b-blog-draft-generation`: Authenticated worker generation of Flow B blog Markdown + hero image pairs into `blog-posts/pending-approval/` from US-078 topic payloads; DeepSeek v1 with provider-pluggable seam; ComfyUI hero image via existing blog image path; editorial canon + anti-AI rules at draft time; durable metadata linking `topic_id` and optional gap context; batch ≤ `max_drafts_per_weekly_run`; fail-closed operator-visible errors; no `ready/` writes or publication side effects.

### Modified Capabilities

- `flow-b-simplified-process`: Cross-link that US-079 runtime blog draft generation now exists as a separate capability (policy process boundary unchanged; docs MUST NOT claim approve/promote/trigger implemented).
- `flow-b-gap-operator-settings`: Clarify that `max_drafts_per_weekly_run` (via `load_gap_operator_settings()`) is also consumed as the draft-generation batch ceiling; settings persist/UI contracts unchanged.

## Impact

- **Code:** New `flow_b_blog_draft_generation` module + blog-draft provider seam (DeepSeek adapter); `pending-approval/` path writer (extend/reuse `draft_writer` patterns); prompt assembly from editorial canon + topic payload; anti-AI validation; thin FastAPI route in `main.py`; unit/API tests with mocked DeepSeek and ComfyUI.
- **APIs:** New authenticated Flow B endpoint (e.g. `POST /flow-b/generate-blog-drafts`); discover-topics, calendar-gaps, and settings GET/PUT unchanged; no approve/trigger routes.
- **Deps:** Existing DeepSeek and ComfyUI config; settings loader; editorial canon in Docker (`content-strategy/silverman-editorial-system.md`); no new mandatory external services.
- **Ops:** CURRENT-STATE + Flow B policy note that draft generation is implemented; Story accepted / BL-017 close remain operator gates.
- **Product:** **BL-017 / US-079** primary (draft half). Does not close BL-017; does not implement US-080–US-082.
- **Acceptance criteria addressed (US-079):** Complete draft + hero image; `pending-approval/` only; DeepSeek v1 + pluggable seam; gap metadata; batch ≤ max drafts; editorial canon + anti-AI rules; no auto-publish / no Flow A / no LinkedIn API; ADR-0001 HTTP.
- **Acceptance criteria excluded / deferred:** Operator walkthrough “outcome visible” Story accepted gate; US-080/081 approve/promote; US-082 gap trigger; LinkedIn API publish.

## Related backlog / stories

| ID | Role |
|----|------|
| **BL-017 / US-079** | Primary — generate Flow B blog draft and image without publishing |
| US-078 | Prerequisite — topic discovery payload (`topics[]`) |
| US-076 | Prerequisite — settings (`max_drafts_per_weekly_run`) |
| US-077 | Prerequisite — gap context shape (optional `target_week`, `empty_days[]`) |
| US-074 / US-075 / BL-016 | Prerequisite policy (Story accepted; closed) |
| US-080 / US-081 | Later — approve/promote (out of scope) |
| US-082 | Later — gap trigger invoking discovery + draft (out of scope) |
