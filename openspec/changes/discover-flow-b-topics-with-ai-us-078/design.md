## Context

US-074/US-075 locked Flow B discovery posture (authority/referent, DeepSeek v1, provider-pluggable later, non-news inputs). US-076 shipped `load_gap_operator_settings()` including `max_drafts_per_weekly_run` (default 2). US-077 shipped authenticated `GET /flow-b/calendar-gaps` (detect-only). There is still no runtime worker step that proposes objective-aligned topics for draft packages.

Existing building blocks: DeepSeek config + chat client (`deepseek_config` / `deepseek_client`) used for LinkedIn draft generation; editorial canon (`content-strategy/silverman-editorial-system.md`) with `#brand-positioning`, `#content-pillars`, `#topic-boundaries`, `#flow-a-vs-flow-b`; `blog-posts/processed/` as the post-Flow-A source archive for soft anti-dup signals; Flow B auth patterns on `/flow-b/*`.

Constraints: ADR-0001 (n8n → HTTP only); discovery-only (no `pending-approval/` / `ready/` writes); BL-020 not required; no RSS/news as primary driver; do not implement US-079–US-082; do not change US-076/US-077 HTTP contracts beyond consuming settings knobs.

Stakeholders: content operator (inspectable topic choices for later draft review); system operator (authenticated HTTP); future US-079/US-082 implementers (stable topic payload + optional gap context).

## Goals / Non-Goals

**Goals:**

- Authenticated HTTP discovery that returns up to N distinct authority-aligned topic choices (N ≤ `max_drafts_per_weekly_run`).
- DeepSeek-only v1 with an explicit provider-pluggable seam.
- Inputs: authority brief + canon topic spaces + soft anti-dup; optional durable primary material; optional gap context (`target_week`, `empty_days[]`).
- Fail closed with operator-visible errors when no objective-aligned topic can be produced.
- Update CURRENT-STATE as implemented (not Story accepted); leave BL-017 open.

**Non-Goals:**

- Draft Markdown/image generation or any write under `blog-posts/pending-approval/` or `ready/`.
- Approve/promote/trigger/LinkedIn API publish.
- Hard anti-dup engine or BL-020 CMS.
- Changing gap-detect or settings persist/UI contracts.

## Decisions

### D1 — HTTP surface: authenticated `POST /flow-b/discover-topics`

**Choice:** Authenticated `POST /flow-b/discover-topics` with JSON body. Discovery is a side-effecting external AI call (not a pure inspect GET), so POST is appropriate. Response is structured topics or a fail-closed error; MUST NOT write draft files.

Request fields (v1):

| Field | Required | Meaning |
|-------|----------|---------|
| `count` | No | Requested topic count; clamped to `1..max_drafts_per_weekly_run` (effective settings). When omitted, default to effective max (or 1 — lock in implementation as: omit ⇒ min(effective max, 2) matching settings default path; prefer **omit ⇒ effective `max_drafts_per_weekly_run`** so a weekly batch gets a full set). |
| `target_week` | No | ISO week string (informational gap context) |
| `empty_days` | No | List of local `YYYY-MM-DD` gap days (informational; MUST NOT imply filesystem inventory) |
| `dry_run` | No | When true, assemble prompts / validate inputs and return a diagnostic without calling the provider (or with a stub) — optional nicety; if present MUST NOT write files |

Response fields (success):

| Field | Meaning |
|-------|---------|
| `status` | `topics_discovered` |
| `provider` | e.g. `deepseek` |
| `topics` | Array of topic objects (length 1..N) |
| `max_drafts_per_weekly_run` | Effective ceiling applied |
| `settings_source` | `defaults` \| `database` |
| `gap_context` | Echo of optional `target_week` / `empty_days` when provided |
| `observed_at_utc` | Observation timestamp |

Topic object (normative for US-079 attachment):

| Field | Meaning |
|-------|---------|
| `thesis` | Clear topic thesis / working title framing |
| `referent_positioning` | Why this positions Silverio as a referent (authority angle) |
| `rationale` | Brief discovery rationale (operator-readable) |
| `pillar_hints` | Optional list of editorial pillars touched |
| `topic_id` | Stable opaque id for this discovery result item (UUID or hash) |

Fail-closed errors: structured JSON with operator-visible `error` / `error_code` (e.g. `discovery_failed`, `discovery_not_objective_aligned`, `deepseek_*`, `discovery_config_invalid`); HTTP 4xx for client/auth/validation, 5xx/502 for provider failures as appropriate — never invent a news-chase topic to satisfy the count.

**Why:** Matches ADR-0001 HTTP boundary; mirrors Flow B route naming; gives US-079 a clear attachable payload without writing drafts yet.

### D2 — Provider-pluggable seam; DeepSeek only in v1

**Choice:** Introduce a small internal interface (Protocol / ABC) e.g. `TopicDiscoveryProvider` with `discover_topics(messages|prompt_bundle, *, count) -> DiscoveryProviderResult`. Ship `DeepSeekTopicDiscoveryProvider` wrapping existing chat-completions helpers (`load_deepseek_settings`, HTTP client patterns from `deepseek_client`). Factory selects provider from a constant/env default of `deepseek` only; unknown providers fail closed.

**Why:** Satisfies “pluggable without rewriting Flow B” without adding unused vendor SDKs. LinkedIn draft generation can keep its existing function; Flow B discovery owns its seam so US-079 can reuse the same pattern later.

**Alternatives rejected:** Hard-coding only `generate_linkedin_draft_content` calls inside the route (no seam); adding OpenAI/Anthropic clients in this change (out of scope).

### D3 — Discovery inputs assembly (no BL-020, no RSS primary)

**Choice:** Build system/user prompts from:

1. **Authority brief** — extract from editorial canon `#brand-positioning` + Flow B authority objective text (`#flow-a-vs-flow-b` / policy; leadership / architecture / transformation / AI; ≥ ~USD 7,000 referent framing).
2. **Topic spaces** — `#content-pillars` + `#topic-boundaries` (allowed themes; durable, not trends).
3. **Soft anti-dup** — read recent titles/slugs from `blog-posts/processed/` (bounded N most recent by mtime or name sort); instruct model to prefer distinct themes; hard blocking engine out of scope.
4. **Optional durable primary material** — if a documented path exists under repo or editorial mount (e.g. curated excerpts under `prompts/flow-b/` or content-strategy references), include lightly for thesis formation; absence MUST NOT fail discovery.
5. **Optional gap context** — include `target_week` / `empty_days[]` as scheduling hints only (“week may need upstream blogs”); MUST NOT scan `ready/` / `pending-approval/` as inventory.

Explicitly exclude: RSS/news API fetches; “top stories this week”; requiring BL-020 backlog files.

**Why:** Matches planning notes / policy discovery posture and US-078 ACs.

### D4 — Batch size ceiling from settings

**Choice:** Call `load_gap_operator_settings()`; effective `max_drafts_per_weekly_run` (default 2) is the hard ceiling. Requested `count` is clamped into `[1, max]`. Produce up to that many **distinct** topics in one provider call (preferred) or sequential calls with prior theses fed back for distinctness — prefer **one structured JSON batch call** for determinism and cost.

**Why:** US-078 AC + US-076 knob; weekly gap batch (US-082) will request up to two.

### D5 — Objective-alignment gate (fail closed)

**Choice:** After provider returns candidates, validate structure (required fields present, non-empty thesis/referent/rationale) and apply a lightweight rejection filter for obvious news-chase patterns (e.g. titles dominated by “vs”, “what’s new”, “this week in…”) — heuristic + prompt constraint. If fewer than 1 valid topic remains, fail closed with `discovery_not_objective_aligned` (or `discovery_failed`). Do **not** pad with filler topics.

**Why:** AC requires fail closed when discovery cannot produce an objective-aligned topic; soft heuristics complement the prompt without becoming a full CMS.

### D6 — No filesystem draft writes

**Choice:** Discovery module returns JSON only. MUST NOT create/move files under `blog-posts/ready/`, `blog-posts/pending-approval/`, or `blog-posts/processed/`. Soft anti-dup reads from `processed/` are read-only.

**Why:** Explicit user non-goal; keeps US-079 as the sole writer of draft packages.

### D7 — Module layout

**Choice:**

- `flow_b_topic_discovery.py` — request validation, settings load, input assembly, orchestration, alignment gate, response shaping.
- `topic_discovery_provider.py` (or nested in same module if tiny) — Protocol + DeepSeek adapter.
- Thin FastAPI route in `main.py` under `/flow-b/discover-topics`.
- Optional prompt helpers colocated or `flow_b_discovery_prompt.py` if prompt builders grow.

**Why:** Smallest coherent diff; mirrors `flow_b_calendar_gap_detect.py` pattern.

### D8 — Auth, secrets, dry-run

**Choice:** Same worker API-key auth as other Flow B routes. Never return API keys. DeepSeek missing/invalid config → fail closed (`discovery_config_invalid` / existing deepseek config codes). `dry_run=true` (if supported) MUST NOT call paid APIs when feasible; always MUST NOT write draft folders.

### D9 — Tests

**Choice:** Unit/API tests with mocked DeepSeek HTTP: happy path N topics; clamp to max drafts; optional gap context echoed; BL-020 absence still succeeds; news-chase-only model output → fail closed; auth required; no writes under ready/pending-approval; settings default vs DB max; provider seam selectable as deepseek only. No real DeepSeek/LinkedIn/ComfyUI calls.

### D10 — Docs / product status

**Choice:** Update `docs/CURRENT-STATE.md`, Flow B policy discovery cross-link, and progress/user-story notes for demonstrated automated AC only. Leave Story accepted unchecked; do not close BL-017.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Model returns news-chase topics | Prompt constraints + post-filter; fail closed rather than accept |
| Soft anti-dup misses themes | Bounded recent titles only; hard anti-dup deferred; document soft nature |
| Provider seam over-engineered | Keep Protocol + one adapter; no multi-vendor registry UI |
| Confusion with draft generation | Specs/tasks forbid pending-approval writes; CURRENT-STATE wording “discovery only” |
| Gap context treated as inventory | Spec forbids filesystem inventory; echo-only fields |
| Double-counting vs US-079 | Topic payload designed for attachment; US-079 owns persistence |

## Migration Plan

1. Implement discovery module + provider seam + HTTP + tests after explicit approval (`/opsx-apply`).
2. `/opsx-verify` → implementation commit → sync → archive (separate commits).
3. Deploy only with explicit approval (out of propose scope).
4. Rollback: revert worker build; no DB migration required for discovery-only.

## Open Questions

None blocking. Resolved by AC/proposal:

- Provider v1: DeepSeek only with pluggable seam (D2).
- Draft writes: none in this change (D6).
- BL-020: not required (D3).
- Batch ceiling: `max_drafts_per_weekly_run` (D4).
