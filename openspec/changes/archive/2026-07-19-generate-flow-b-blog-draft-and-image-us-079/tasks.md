## 1. Provider seam and draft generation core

- [x] 1.1 Add a provider-pluggable blog-draft generation seam (`BlogDraftGenerationProvider` Protocol/ABC + result types) with a DeepSeek-only v1 adapter reusing existing DeepSeek settings/client patterns; unsupported providers fail closed; never expose API keys
- [x] 1.2 Add `flow_b_blog_draft_generation` orchestration that accepts US-078 topic payloads (`thesis`, `referent_positioning`, `rationale`, `topic_id`; optional `pillar_hints`) and optional gap context (`target_week`, `empty_days[]`); assemble prompts from editorial canon + topic; generate Markdown with YAML front matter (`flow: flow_b`, `topic_id`, sibling `image` reference)
- [x] 1.3 Cap batch size with `load_gap_operator_settings().max_drafts_per_weekly_run` (default 2); validate topic array (non-empty, clamp/reject above ceiling, reject duplicate `topic_id` in one request); process topics sequentially for v1
- [x] 1.4 Apply blocking anti-AI-writing heuristics per editorial canon (`#anti-ai-writing-rules`) at draft time; fail closed with operator-visible violations when blocked
- [x] 1.5 Ensure orchestration never writes under `blog-posts/ready/`, never invokes Flow A publish/package/schedule, Git publication, or LinkedIn API publish, and never enables LinkedIn publication

## 2. Pending-approval filesystem and hero image

- [x] 2.1 Add `pending-approval/` path writer (extend/reuse `draft_writer` patterns): direct-child `.md` + `.png` pair under `blog-posts/pending-approval/`; collision-safe exclusive create; slug from thesis/title with timestamp/topic_id suffix retries
- [x] 2.2 Write durable sidecar metadata (e.g. `blog-posts/pending-approval/<slug>.flow-b.json`) linking `topic_id`, discovery fields, optional `target_week` / `empty_days[]`, `generated_at_utc`, `provider`, `flow: flow_b`, `status: pending_approval`
- [x] 2.3 Integrate hero image via existing `blog_image_generation` / ComfyUI client for the pending-approval Markdown path; respect ComfyUI enablement flags; honor `dry_run` (no durable `.md`/`.png` writes when dry-run)
- [x] 2.4 Handle partial failures per topic (e.g. image failure after Markdown) with structured per-draft `image_status` / error codes without promoting to `ready/`

## 3. Authenticated HTTP API

- [x] 3.1 Add authenticated `POST /flow-b/generate-blog-drafts` returning `status`, `provider`, `drafts[]` (paths, topic_id, image_status, anti_ai_status), effective `max_drafts_per_weekly_run`, settings source, echoed gap context when present, `observed_at_utc`; reject unauthenticated callers; secret-safe structured errors
- [x] 3.2 Confirm no US-080/081 approve/promote or US-082 trigger routes are added; `discover-topics`, `calendar-gaps`, and settings GET/PUT contracts unchanged; no n8n Execute Command (ADR-0001)
- [x] 3.3 Expose endpoint in OpenAPI alongside existing Flow B routes

## 4. Tests

- [x] 4.1 Unit/API tests (mocked DeepSeek + ComfyUI): happy path topic → md + png + sidecar in `pending-approval/`; batch clamp to `max_drafts_per_weekly_run`; gap metadata persisted; anti-AI blocked → not successful package; ComfyUI disabled → structured failure; `dry_run` → no durable pair; missing DeepSeek config → fail closed; auth required; no writes under `ready/`; no Flow A / LinkedIn publish calls
- [x] 4.2 Run targeted pytest for new module/route; fix warnings attributable to this change; `git diff --check` clean

## 5. Docs and product status

- [x] 5.1 Update `docs/operations/flow-b-simplified-policy.md` (and glossary/planning notes if needed) so US-079 draft generation is the runtime step into `pending-approval/`, and approve/promote/trigger are not claimed implemented
- [x] 5.2 Update `docs/CURRENT-STATE.md` to record blog draft generation **implemented** (not Story accepted / not deployed unless separately approved)
- [x] 5.3 After demonstrated automated AC, update `docs/product/user-stories.md` US-079 and `docs/product/progress-checklist.md` only to the validated state — do not mark Story accepted without operator walkthrough; do not close BL-017; leave US-080–US-082 unchecked

## 6. Business validation gate

- [x] 6.1 Walk US-079 acceptance criteria against local worker evidence (complete draft + hero image, `pending-approval/` only, DeepSeek v1 + seam, gap metadata, batch ≤ max drafts, editorial canon + anti-AI blocking, no auto-publish / no Flow A / no LinkedIn API, ADR-0001 HTTP)
- [x] 6.2 Record any remaining gaps explicitly; leave US-080–US-082 and BL-017 close unchecked

### Remaining gaps (explicit)

- Operator walkthrough / “outcome visible” AC → Story accepted still open
- Deploy to `192.168.0.194` not done (requires separate approval)
- US-080 / US-081 approve-promote and US-082 gap trigger not implemented
- BL-017 remains open until US-078+US-079 Story accepted (and business outcome validated)
