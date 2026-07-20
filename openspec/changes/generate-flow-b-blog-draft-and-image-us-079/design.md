## Context

US-078 shipped authenticated `POST /flow-b/discover-topics` on `192.168.0.194:8010` (`BUILD_REVISION=18b6bec…`): DeepSeek v1 topic discovery with a provider-pluggable seam (`topic_discovery_provider.py`), authority brief + editorial canon inputs, batch cap from `load_gap_operator_settings().max_drafts_per_weekly_run`, optional gap context (`target_week`, `empty_days[]`), and no draft filesystem writes. US-076 settings and US-077 gap detect are deployed. There is still no runtime step that turns discovered topics into approval-ready blog packages.

Existing building blocks:

- **Topic payload** — `DiscoveredTopic` in `flow_b_topic_discovery.py` (`thesis`, `referent_positioning`, `rationale`, `topic_id`, optional `pillar_hints`).
- **DeepSeek** — `deepseek_config`, `deepseek_client.generate_linkedin_draft_content` (chat completions pattern).
- **Provider seam** — `TopicDiscoveryProvider` / `create_topic_discovery_provider` (mirror for blog draft generation).
- **Path writing** — `draft_writer.py` (collision-safe exclusive create, sanitize segments, UTC timestamps); adapt prefix to `blog-posts/pending-approval/`.
- **Hero image** — `blog_image_generation.py` + `comfyui_client` (ComfyUI enablement flags, `dry_run`, editorial remediation path).
- **Editorial canon** — `content-strategy/silverman-editorial-system.md` packaged in Docker at `/app/content-strategy/`; `#anti-ai-writing-rules` specifies **blocking** rules for future Flow B generated content.
- **Flow B auth** — same API-key pattern as `/flow-b/*` routes in `main.py`.

Constraints: ADR-0001 (n8n → HTTP only); write only `pending-approval/`; no Flow A publish/package/schedule; no LinkedIn API publish; do not change US-078/US-077/US-076 HTTP contracts; batch ≤ `max_drafts_per_weekly_run`; BL-017 remains open until operator gates satisfied.

Stakeholders: content operator (inspectable draft packages for US-080 approve UI); system operator (authenticated HTTP, dry-run); future US-082 implementer (stable batch + gap metadata contract).

## Goals / Non-Goals

**Goals:**

- Authenticated HTTP generation of complete blog Markdown + hero image pairs in `blog-posts/pending-approval/` from US-078 topic objects.
- DeepSeek-only v1 with an explicit provider-pluggable seam (parallel to topic discovery).
- Reuse ComfyUI blog image path with enablement guards and dry-run semantics.
- Durable metadata sidecar linking `topic_id`, optional `target_week` / `empty_days[]`, generation provenance.
- Editorial canon in prompts; anti-AI-writing heuristics at draft time (blocking per canon for Flow B).
- Batch up to effective `max_drafts_per_weekly_run`; fail closed with operator-visible errors.
- Update CURRENT-STATE as implemented (not Story accepted); leave BL-017 open.

**Non-Goals:**

- Writes to `blog-posts/ready/` or `blog-posts/processed/`.
- Auto-publish blog, Git handoff, Flow A lifecycle, LinkedIn package/schedule/publish.
- US-080/081 approve/promote UI; US-082 gap trigger orchestration.
- Changing `discover-topics`, `calendar-gaps`, or settings GET/PUT contracts.
- Mandatory BL-020 backlog; RSS/news as primary driver.

## Decisions

### D1 — HTTP surface: authenticated `POST /flow-b/generate-blog-drafts`

**Choice:** Authenticated `POST /flow-b/generate-blog-drafts` with JSON body. Generation is side-effecting (filesystem + external AI/ComfyUI), so POST is appropriate.

Request fields (v1):

| Field | Required | Meaning |
|-------|----------|---------|
| `topics` | Yes | Array of US-078 topic objects (`thesis`, `referent_positioning`, `rationale`, `topic_id`; optional `pillar_hints`). Length 1..effective max after clamp. |
| `target_week` | No | ISO week string (`YYYY-Www`) for gap-batch metadata |
| `empty_days` | No | List of local `YYYY-MM-DD` gap days (informational metadata; MUST NOT imply filesystem inventory) |
| `dry_run` | No | When true: assemble prompts, validate inputs, run anti-AI checks on stub or provider output if feasible; MUST NOT write `.md`/`.png` under `pending-approval/`; ComfyUI path MUST NOT mutate production image files (mirror existing `dry_run` semantics) |

Response fields (success):

| Field | Meaning |
|-------|---------|
| `status` | `drafts_generated` (or `draft_generation_dry_run` when `dry_run=true`) |
| `provider` | e.g. `deepseek` |
| `drafts` | Array of per-topic results |
| `max_drafts_per_weekly_run` | Effective ceiling applied |
| `settings_source` | `defaults` \| `database` |
| `gap_context` | Echo of optional `target_week` / `empty_days` when provided |
| `observed_at_utc` | Observation timestamp |

Per-draft object (success item):

| Field | Meaning |
|-------|---------|
| `topic_id` | From input topic |
| `blog_relative_path` | e.g. `blog-posts/pending-approval/<slug>.md` |
| `image_relative_path` | Matching `.png` sibling |
| `metadata_relative_path` | Sidecar JSON path (e.g. same stem `.flow-b.json` or under `metadata/` — lock: **sibling** `blog-posts/pending-approval/<slug>.flow-b.json` for operator visibility) |
| `title` / `slug` | Derived from generated front matter |
| `image_status` | `generated` \| `dry_run` \| `skipped` \| `failed` (with `image_error_code` when failed) |
| `anti_ai_status` | `passed` \| `blocked` (with `anti_ai_violations[]` when blocked) |

Fail-closed: structured JSON with `error` / `error_code` (e.g. `draft_generation_failed`, `draft_config_invalid`, `anti_ai_blocked`, `pending_approval_dir_not_ready`, `comfyui_disabled`, `deepseek_*`); HTTP 4xx/5xx as appropriate. Partial batch failure: return per-item errors in `drafts[]` and overall `status: drafts_partial` when some succeed and some fail — **prefer all-or-nothing within a single topic** (if image fails after markdown written, record error and leave operator-visible state; do not promote to `ready/`).

**Why:** Matches Flow B route naming; clear handoff to US-080 list endpoint; ADR-0001 HTTP boundary.

**Alternatives rejected:** Reusing `POST /flow-b/discover-topics` with a flag (mixes discovery and draft concerns); writing directly to `ready/` (violates policy).

### D2 — Provider-pluggable seam; DeepSeek only in v1

**Choice:** Introduce `BlogDraftGenerationProvider` Protocol + `DeepSeekBlogDraftGenerationProvider` wrapping existing chat-completions helpers. Factory `create_blog_draft_provider()` with env default `SILVERMAN_FLOW_B_BLOG_DRAFT_PROVIDER=deepseek` (or reuse a shared `SILVERMAN_FLOW_B_*_PROVIDER` pattern). Unsupported providers fail closed.

**Why:** US-079 AC + consistency with US-078 seam; US-082 can call the same orchestration later.

### D3 — Prompt assembly and editorial canon

**Choice:** Build system/user prompts from:

1. Editorial canon sections: `#brand-positioning`, `#content-pillars`, `#topic-boundaries`, `#blog-post-rules`, `#flow-a-vs-flow-b`, `#anti-ai-writing-rules` (instruct model to avoid forbidden patterns).
2. Topic object: `thesis`, `referent_positioning`, `rationale`, `pillar_hints`.
3. Optional gap context as scheduling hints only (not filesystem inventory).
4. Output contract: valid Markdown with YAML front matter (`title`, `date` placeholder or generation date, `image` pointing to sibling `.png`, `flow: flow_b`, `topic_id`).

Require structured blog shape per `#blog-post-rules` (title, sections, practical senior tone). Do not call RSS/news APIs.

**Why:** Matches planning notes and US-079 AC; aligns with editorial system mapping table (`Future Flow B review` → anti-AI blocking).

### D4 — Anti-AI-writing gate at draft time (blocking)

**Choice:** After provider returns Markdown, run heuristic checks derived from `#anti-ai-writing-rules` (forbidden openings/transitions/endings, title-as-first-sentence, generic template phrases). On violation:

- **Default:** fail closed for that topic with `anti_ai_blocked` and do **not** leave a publishable pair (if markdown was written, mark metadata `blocked` or delete partial files — prefer **validate before write** when possible; if post-write validation fails, write metadata with `status: blocked` and keep files for operator inspection with clear error in HTTP response).

Canon says Flow B generated content uses **rewrite/blocking** rules. v1: **block and surface violations** (no automatic rewrite loop in this change).

**Why:** US-079 AC; editorial canon explicitly labels Future Flow B as blocking.

**Alternatives rejected:** Warnings-only (Flow A user blog default); unbounded rewrite retries (scope creep).

### D5 — Filesystem layout: `pending-approval/` pair rules

**Choice:**

- Prefix: `blog-posts/pending-approval/` (constant `PENDING_APPROVAL_RELATIVE`).
- Pair rule: for slug `my-post`, write `my-post.md` + `my-post.png` as direct children (same as `ready/` pair convention).
- Slug derivation: sanitize thesis/title via `draft_writer.sanitize_filename_segment`; collision handling via timestamp + `topic_id` suffix (reuse `generate_draft_relative_path` pattern adapted for pending prefix).
- Sidecar metadata: `blog-posts/pending-approval/<slug>.flow-b.json` with `topic_id`, `thesis`, `referent_positioning`, `rationale`, optional `target_week`, `empty_days`, `generated_at_utc`, `provider`, `flow: flow_b`, `status: pending_approval`.

**Why:** Locked option A in planning notes; US-080 can read folder + sidecar.

### D6 — Hero image via existing ComfyUI blog path

**Choice:** After Markdown is validated and written, call `blog_image_generation` entry suitable for editorial folder (e.g. `_ensure_editorial_blog_image_impl` or a thin wrapper) with `source_relative_path` under `pending-approval/`, respecting:

- ComfyUI enablement env flags (fail closed or `image_status: failed` with `comfyui_disabled` when disabled and image required).
- `dry_run` passthrough — no production PNG write when dry-run.
- No public-repo handoff or Flow A campaign side effects for Flow B draft path.

Image prompt context: blog title + thesis + first ~500 chars of body (reuse blog image prompt builders if available).

**Why:** Reuse tested ComfyUI integration; US-079 AC explicitly names this path.

**Alternatives rejected:** Placeholder PNG only (AC requires hero image generation); separate ComfyUI workflow fork (unnecessary).

### D7 — Batch size ceiling from settings

**Choice:** `load_gap_operator_settings()`; clamp `len(topics)` to `[1, max_drafts_per_weekly_run]`. Process topics sequentially (simpler failure isolation) or limited parallelism — **prefer sequential** for v1 to avoid ComfyUI contention.

Empty `topics` → validation error. Duplicate `topic_id` in one request → validation error or dedupe (prefer **reject duplicates**).

**Why:** US-079 AC + US-082 future batch.

### D8 — No publication side effects

**Choice:** Orchestration module MUST NOT import or invoke: `publish_blog_post`, `generate_linkedin_package`, `schedule_linkedin_distribution`, LinkedIn publication routes, `complete_flow_a_ready_path`, or GitHub Pages git publication. No campaign metadata creation for Flow A. `flow: flow_b` in front matter and sidecar.

**Why:** Explicit user non-goals; Flow B guardrails in specs.

### D9 — Module layout

**Choice:**

- `flow_b_blog_draft_generation.py` — validation, settings load, prompt assembly, provider call, anti-AI gate, filesystem writes, image orchestration, response shaping.
- `blog_draft_generation_provider.py` — Protocol + DeepSeek adapter (mirror `topic_discovery_provider.py`).
- `flow_b_pending_approval_writer.py` (or functions in draft module) — path generation + atomic pair writes under `pending-approval/`.
- Thin FastAPI route in `main.py` under `/flow-b/generate-blog-drafts`.

**Why:** Smallest coherent diff; mirrors `flow_b_topic_discovery.py`.

### D10 — Auth, secrets, dry-run

**Choice:** Same worker API-key auth as other Flow B routes. Never return API keys. DeepSeek/ComfyUI missing config → fail closed with actionable codes. `dry_run=true` MUST NOT create durable `.md`/`.png` in `pending-approval/` (may return diagnostic paths that would have been used).

### D11 — Tests

**Choice:** Unit/API tests with mocked DeepSeek + ComfyUI:

- Happy path: topic → md + png + sidecar in `pending-approval/`.
- Batch clamp; gap metadata persisted.
- Anti-AI blocked → no successful draft status.
- ComfyUI disabled → structured failure.
- `dry_run` → no filesystem pair.
- Auth required; no writes under `ready/`; no Flow A/LinkedIn calls (monkeypatch guards).

### D12 — Docs / product status

**Choice:** Update `docs/CURRENT-STATE.md`, Flow B policy draft-generation cross-link, user-story automated AC only. Leave Story accepted unchecked; BL-017 open; US-080–US-082 unchecked.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Anti-AI heuristics false positives | Block with explicit violations list; operator can inspect blocked files; no auto-publish path |
| ComfyUI failure after Markdown write | Per-draft `image_status: failed`; metadata records state; do not write to `ready/` |
| Slug collisions | Timestamp + topic_id suffix retries (reuse draft_writer collision pattern) |
| Provider seam over-engineered | Protocol + one adapter only |
| Confusion with discovery | Separate endpoint; specs forbid discover-topics writes |
| Gap context treated as inventory | Spec + metadata echo only |
| ComfyUI load on batch | Sequential processing; cap at max_drafts=2 |

## Migration Plan

1. Implement modules + provider seam + HTTP + tests after explicit approval (`/opsx-apply`).
2. `/opsx-verify` → implementation commit → sync → archive (separate commits).
3. Deploy only with explicit approval; ensure Docker image includes `content-strategy/` (already true from US-078).
4. Rollback: revert worker build; generated `pending-approval/` files remain for operator cleanup (no DB migration).

## Open Questions

None blocking. Resolved by AC/proposal:

- Endpoint name: `POST /flow-b/generate-blog-drafts` (D1).
- Metadata location: sibling `.flow-b.json` under `pending-approval/` (D5).
- Anti-AI: blocking at draft time, no rewrite loop in v1 (D4).
- Image path: reuse `blog_image_generation` + ComfyUI flags (D6).
