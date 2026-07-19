# Planning notes — Flow B simplification

**Status:** All P4 planning decisions **locked 2026-07-19**. US-074/US-075 normative policy applied: [flow-b-simplified-policy.md](../operations/flow-b-simplified-policy.md). OpenSpec `define-simplified-flow-b-us-074-075` tasks complete (Story accepted pending operator review).  
**Product surface name:** **Silverman Authority Manager**.  
**Canonical executables:** [backlog.md](backlog.md) P4 (BL-016–BL-019), [user-stories.md](user-stories.md) **US-074–US-082**, [progress-checklist.md](progress-checklist.md).

## Agreed direction (normative for P4)

**Flow B = AI discovers topics → AI generates the blog → operator approves the blog → from then on, same path as Flow A.**

- One hard human gate: **blog content** (AI-authored).
- No mandatory LinkedIn review path for Flow B after blog approval.
- No mini-CMS (structured feedback / revision history) as P4 scope.
- After approval: publish → package → schedule → optional LinkedIn supervision (existing Flow A behavior).
- Operator UI: **extend Silverman Authority Manager** (no separate Flow B app).

## Calendar / gap sensor (BL-019 / US-080–US-081) — locked

Calendar is a **weekly gap sensor**, not a daily “is tomorrow empty?” ping.

```text
Typical run: Friday afternoon (operator-local), configurable
  → Scan Mon–Sun of the NEXT operator-local week
  → Gap day = local day with 0 LinkedIn posts (pending / queued / published)
  → Days with 1–2 posts are NOT gaps (US-040K max 2 still caps scheduling)
  → If gaps[] empty → no-op
  → Else (idempotent per ISO week) → Flow B up to max_drafts_per_weekly_run blogs
       → operator approves → Flow A packages / schedules
       → surplus LinkedIn publications spill (algorithm A below)
```

| Knob | Locked default |
|------|----------------|
| Gap definition | **0** LinkedIn posts that local day |
| Scan window | Next operator-local week (Mon–Sun) |
| Typical cron | Friday afternoon → build following week |
| `min_lead_days` | **5** (DB/UI) |
| `max_drafts_per_weekly_run` | **2** |
| Idempotency | `flow_b_gap_week:{operator_tz}:{YYYY}-W{ww}` |
| Orchestration | **n8n Schedule → worker HTTP** (ADR-0001); worker reads DB settings and no-ops outside window |
| Draft layout | **`blog-posts/pending-approval/`** → on approve → **`blog-posts/ready/`** |
| Spill | **Algorithm A:** target-week gap days → other days in week with capacity → forward day-by-day |

### Operator settings (Postgres `silverman_linkedin_db` + UI) — US-082

| Key | Default | Role |
|-----|---------|------|
| `operator_timezone` | IANA | Local week / Friday run / density days |
| `gap_trigger_enabled` | `false` until validated | Fail-closed auto trigger |
| `gap_scan_mode` | `next_week` | Weekly scan |
| `weekly_run_local_day` | `friday` | When the sensor typically runs |
| `weekly_run_local_time` | `15:00` | Local clock |
| `min_lead_days` | `5` | Lead before a gap day is actionable |
| `gap_posts_threshold` | `0` | Only zero-count days are gaps |
| `max_drafts_per_weekly_run` | `2` | Upstream blogs per weekly batch |
| `density_max_per_local_day` | `2` | Mirror US-040K until BL-021 |

### Spill algorithm A (US-079) — locked

When placing LinkedIn variants after Flow B approve + Flow A package:

1. Fill **target-week gap days** (had 0 posts) chronological, up to density max 2 each.
2. Then other days **in the target week** with remaining capacity.
3. Then **forward** day-by-day after the week (“siguiente(s) día disponible”) under max 2.

### Draft filesystem (US-077 / US-079) — locked option A

- Unapproved AI blogs live in **`blog-posts/pending-approval/`** (same Markdown + image pair rules as `ready/`).
- Flow A MUST NOT consume `pending-approval/` as publishable input.
- On approve: promote/move into **`blog-posts/ready/`**, then Flow A path.
- Persist gap batch / ISO week metadata with the draft when created from US-081.

## Discovery / models (US-076 / US-077) — locked

**Positioning:** authority / referent — not news spreader. No “X vs Y”, “what’s new”, or headline rebroadcast as the discovery objective.

**Models:**

- **v1:** **DeepSeek only** for discovery + draft (already in stack).
- **Soon:** provider-pluggable interface so additional models (EU/CN/other) can be enabled without rewriting Flow B — do not hard-wire US-only vendors.

**v1 discovery inputs:**

1. Career / authority brief (canonical positioning ≥ ~USD 7,000 leadership/architecture/transformation/AI).
2. Editorial canon topic spaces (durable themes, not trends).
3. Soft anti-dup against recent published blogs (titles/themes).
4. Optional light signal from durable primary material (standards, architecture references, long-form essays) used to **form a thesis**, not to summarize today’s news.

**Out of v1:** RSS/news APIs as primary driver; “top stories this week” prompts; comparative product hot-takes.

## Apply order (OpenSpec)

```text
US-074 → US-075 → US-082 → US-080 → US-076 → US-077 → US-078 → US-079 → US-081
```

First OpenSpec change (artifacts complete — awaiting approval before `/opsx-apply`): `openspec/changes/define-simplified-flow-b-us-074-075/` (US-074 + US-075 docs/policy). Runtime stories follow in separate approved changes.

## Topics

**North star:** Attract senior leadership / Solutions Architect / digital transformation / AI roles at **≥ ~USD 7,000** — authority, not “senior developer.”

BL-020 hand-curated backlog is optional enrichment, not a prerequisite.

## Story ID note

Executable P4 stories: **US-074–US-082**. Do not collide with BL-031 **US-041** (calendar DB).

## Explicitly deferred / out of early Flow B

- Second mandatory LinkedIn approval gate after blog OK.
- CMS-like revision history and structured feedback loops.
- Rich calendar intelligence (thematic engines, audience-balancing schedulers) inside P4.
- Full metrics loop (BL-022 / BL-023) as Flow B prerequisites.
- Hand-maintained topic CMS (BL-020) as a hard dependency.
- Multi-model routing beyond DeepSeek in the first implementation slice (interface may be prepared; enabling other models is a follow-on).
