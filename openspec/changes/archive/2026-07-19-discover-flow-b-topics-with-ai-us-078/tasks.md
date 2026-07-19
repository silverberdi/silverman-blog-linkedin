## 1. Provider seam and discovery core

- [x] 1.1 Add a provider-pluggable topic-discovery seam (`TopicDiscoveryProvider` Protocol/ABC + result types) with a DeepSeek-only v1 adapter that reuses existing DeepSeek settings/client patterns; unsupported providers fail closed; never expose API keys
- [x] 1.2 Add `flow_b_topic_discovery` orchestration that assembles authority brief + editorial canon topic spaces + soft anti-dup (recent `blog-posts/processed/` titles read-only) + optional durable primary material; MUST NOT require BL-020 backlog; MUST NOT use RSS/news APIs as primary driver
- [x] 1.3 Cap batch size with `load_gap_operator_settings().max_drafts_per_weekly_run` (default 2); accept optional `target_week` / `empty_days[]` as informational only (no ready/pending-approval inventory); apply objective-alignment gate and fail closed with operator-visible errors when no valid topic remains
- [x] 1.4 Ensure discovery never writes under `blog-posts/ready/` or `blog-posts/pending-approval/`, never starts draft/approve/trigger, and never enables LinkedIn publication

## 2. Authenticated HTTP API

- [x] 2.1 Add authenticated `POST /flow-b/discover-topics` returning `status`, `provider`, `topics[]` (thesis + referent_positioning + rationale + topic_id), effective `max_drafts_per_weekly_run`, settings source, echoed gap context when present, `observed_at_utc`; reject unauthenticated callers; secret-safe structured errors
- [x] 2.2 Confirm no US-079 draft writes, US-080/081 approve/promote, or US-082 trigger routes are added; gap-detect and settings GET/PUT contracts unchanged; no n8n Execute Command (ADR-0001)

## 3. Tests

- [x] 3.1 Unit/API tests (mocked DeepSeek): happy path N distinct topics; clamp to `max_drafts_per_weekly_run`; defaults when settings row missing; DB max honored; optional gap context echoed; runs without BL-020; news-chase-only output → fail closed; missing DeepSeek config → fail closed; auth required; no writes under ready/pending-approval
- [x] 3.2 Run targeted pytest for the new module/route; fix warnings attributable to this change; `git diff --check` clean

## 4. Docs and product status

- [x] 4.1 Update `docs/operations/flow-b-simplified-policy.md` (and glossary/planning notes if needed) so US-078 discovery is the runtime topic-discovery step, DeepSeek v1 + pluggable seam and non-news posture remain visible, and draft/approve/trigger are not claimed implemented
- [x] 4.2 Update `docs/CURRENT-STATE.md` to record topic discovery **implemented** (not Story accepted / not deployed unless separately approved)
- [x] 4.3 After demonstrated automated AC, update `docs/product/user-stories.md` US-078 and `docs/product/progress-checklist.md` only to the validated state — do not mark Story accepted without operator walkthrough; do not close BL-017

## 5. Business validation gate

- [x] 5.1 Walk US-078 acceptance criteria against local worker evidence (authority constraint, DeepSeek v1 + seam, inputs, BL-020 not required, optional gap context, batch ≤ max drafts, topic surface for draft attachment, fail closed, no draft-folder writes)
- [x] 5.2 Record any remaining gaps explicitly; leave US-079–US-082 and BL-017 close unchecked
