# Flow B simplified policy (US-074 / US-075)

**Status:** Policy defined 2026-07-19 (documentation). **US-076** gap operator settings persistence is **implemented and deployed**. **US-077** next-week gap **detect** is **implemented and deployed** (authenticated `GET /flow-b/calendar-gaps`; not Story accepted). **US-078** AI topic **discovery** is **implemented and deployed** (authenticated `POST /flow-b/discover-topics`; not Story accepted). **US-079** AI blog **draft generation** is **implemented and deployed** (authenticated `POST /flow-b/generate-blog-drafts` → `blog-posts/pending-approval/`; not Story accepted). **US-080** blog draft **approve/reject presentation** is **implemented and deployed** (authenticated `GET`/`POST /flow-b/pending-approval-drafts…` + Authority Manager **Flow B drafts** panel; not Story accepted). **US-081–US-082** (promote + spill A, gap trigger) remain **not** implemented.
**Story IDs:** renumbered 2026-07-19 to match apply order (settings=076 … trigger=082).
**Product surface:** **Silverman Authority Manager**
**Planning authority:** [planning-notes-flow-b-simplification.md](../product/planning-notes-flow-b-simplification.md)
**Stories:** BL-016 — [US-074](../product/user-stories.md), [US-075](../product/user-stories.md); settings SoT — [US-076](../product/user-stories.md); gap detect — [US-077](../product/user-stories.md); topic discovery — [US-078](../product/user-stories.md); draft generation — [US-079](../product/user-stories.md); approve/reject presentation — [US-080](../product/user-stories.md)
**OpenSpec:** `openspec/changes/define-simplified-flow-b-us-074-075` (capability `flow-b-simplified-process`); settings capability `flow-b-gap-operator-settings` (US-076); detect capability `flow-b-calendar-gap-detect` (US-077); discovery capability `flow-b-topic-discovery` (US-078); draft capability `flow-b-blog-draft-generation` (US-079); approve capability `flow-b-blog-draft-approval` (US-080)

This document is the operator-facing normative policy for simplified Flow B. Editable gap operator settings are persisted via **Postgres `silverman_linkedin_db` + Silverman Authority Manager UI** (US-076 / `GET`+`PUT /flow-b/gap-operator-settings`), with documented defaults including `gap_trigger_enabled=false`. **Runtime next-week LinkedIn gap detection** is provided by capability `flow-b-calendar-gap-detect` (US-077): authenticated detect-only `GET /flow-b/calendar-gaps` returns `gaps[]` / no-gap for the next operator-local week using settings from US-076, without mutating campaigns or starting drafts. Detect **MAY** run for inspection when `gap_trigger_enabled=false`; auto-trigger remains a separate fail-closed capability (US-082). **Runtime AI topic discovery** is provided by capability `flow-b-topic-discovery` (US-078): authenticated `POST /flow-b/discover-topics` returns authority-aligned topic choices (DeepSeek v1; provider-pluggable seam) without writing draft packages. **Runtime AI blog draft generation** is provided by capability `flow-b-blog-draft-generation` (US-079): authenticated `POST /flow-b/generate-blog-drafts` accepts US-078 topic payloads, generates Markdown + hero image pairs into `blog-posts/pending-approval/` (same pair rules as `ready/`), applies editorial canon and blocking anti-AI-writing rules, and records durable sidecar metadata — without writing `blog-posts/ready/` or invoking Flow A publish/package/schedule or LinkedIn API publish. **Runtime blog draft approve/reject presentation** is provided by capability `flow-b-blog-draft-approval` (US-080): authenticated worker HTTP plus Silverman Authority Manager UI that lists/presents drafts from `pending-approval/`, supports approve and reject, keeps rejected drafts non-publishable, and records approve decisions without promoting to `ready/`. This document does **not** implement promote/spill (US-081) or gap trigger (US-082).

---

## 1. Process boundary (US-074)

Flow B:

```text
weekly gap or explicit trigger
  → AI topic discovery (DeepSeek v1)
  → AI blog draft in blog-posts/pending-approval/
  → operator approve/reject in Silverman Authority Manager
  → on approve: promote to blog-posts/ready/
  → same path as Flow A (publish → package → schedule → optional LinkedIn supervision)
```

| Rule | Normative |
|------|-----------|
| Only mandatory human gate | **Blog approval** for AI-authored posts |
| After blog approval | **No** mandatory LinkedIn review (optional Flow A supervision only) |
| Operator UI | **Extend Silverman Authority Manager** — not a separate Flow B-only app |
| Positioning | Authority / **referent** (≥ ~USD 7,000 leadership / architecture / transformation / AI) — **not** news spreader |

### P4 non-goals

- Revision-history CMS / structured multi-round feedback loops  
- Thematic duplication engines / audience-balancing schedulers inside P4  
- BL-020 hand-curated topic backlog as a **prerequisite**  
- News-spreader discovery (“X vs Y”, “what’s new”, headline rebroadcast)  
- Second mandatory LinkedIn approval after blog OK  

Cross-links (runtime, not this doc): operator settings **US-076**; detect **US-077**; trigger **US-082**; discovery/draft **US-078/US-079**; approve/promote **US-080/US-081**.

---

## 2. Eligibility (US-075)

| Location | Meaning |
|----------|---------|
| `blog-posts/pending-approval/` | Unapproved AI blog Markdown + image pairs (same pair rules as `ready/`) |
| `blog-posts/ready/` | Flow A–eligible inbox **after** recorded approve + promote |

- Unapproved drafts in `pending-approval/` **MUST NOT** publish blog or LinkedIn.  
- Flow A **MUST NOT** consume `pending-approval/` as publish input.  
- On approve: promote/move to `ready/`, then Flow A **MAY** run.  
- Empty calendar days are a **proxy** for needing upstream content — not a filesystem inventory of `ready/` or `pending-approval/`.

---

## 3. Weekly calendar gap sensor (US-075 policy + US-077 detect)

Calendar is a **weekly gap sensor** (not a daily “is tomorrow empty?” ping).

```text
Typical run: Friday afternoon (operator-local), configurable via DB+UI (US-076)
  → Scan Mon–Sun of the NEXT operator-local week
  → Gap day = 0 LinkedIn posts (pending / queued / published)
  → Days with ≥1 are NOT gaps
  → If gaps[] empty → no-op (for later trigger)
  → Else (ISO-week idempotent) → up to max_drafts_per_weekly_run blog drafts (US-082)
```

| Knob | Default | Notes |
|------|---------|--------|
| Gap definition | **0** LinkedIn posts that local day | ≥1 → not a gap for trigger |
| Scan window | Next operator-local week (Mon–Sun) | |
| Typical cron intent | Friday afternoon → following week | Clock truth in DB/UI (US-076) |
| `min_lead_days` | **5** | Do not target a gap day closer than this lead |
| `max_drafts_per_weekly_run` | **2** | Upstream blogs per weekly batch |
| `gap_trigger_enabled` | **false** until validated | Fail-closed for **auto-trigger** (US-082); detect MAY still run for inspection |
| Idempotency key | `flow_b_gap_week:{operator_tz}:{YYYY}-W{ww}` | Re-run → no-op if batch pending/completed |
| Orchestration | **n8n Schedule → worker HTTP** (ADR-0001) | Worker no-ops outside window / when disabled; no Execute Command |

**Runtime detect (US-077):** authenticated `GET /flow-b/calendar-gaps` (optional `now_utc` for diagnostics) is the worker sensor. It loads knobs via `load_gap_operator_settings()`, returns `status` (`gaps_found` / `no_gap`), `gaps[]`, target ISO week, operator timezone, settings source, effective `min_lead_days` / `gap_posts_threshold`, `read_only=true`. Empty coverage is a **proxy** for needing upstream content — not a filesystem inventory of `ready/` or `pending-approval/`. Detect does **not** start discovery, draft generation, or trigger. **Detect vs trigger:** inspection is allowed when `gap_trigger_enabled=false`; auto-trigger remains US-082 and stays fail-closed when the flag is false.

Full settings key list and defaults: see planning notes / US-076. **Runtime SoT for those knobs:** Postgres table `flow_b_gap_operator_settings` in `silverman_linkedin_db` (same `SILVERMAN_CALENDAR_DATABASE_URL` as US-041 calendar), edited via authenticated Authority Manager **Gap settings** UI. When no row exists, documented defaults apply (`gap_trigger_enabled=false`, friday/`15:00`, etc.). Saving settings does **not** enable LinkedIn API publish. Trigger remains a separate story (US-082).

---

## 4. Spill algorithm A (US-081 — policy recorded here)

After approve + Flow A package, when placing LinkedIn variants:

1. Fill **target-week gap days** chronological (up to density max 2).  
2. Then other days **in the target week** with remaining capacity.  
3. Then **forward** day-by-day after the week (“siguiente(s) día disponible”) under US-040K max 2.

Runtime scheduling behavior is owned by **US-081**; this section locks the algorithm for implementers.

---

## 5. Discovery posture (US-078 — policy + runtime)

| Item | Normative |
|------|-----------|
| v1 model | **DeepSeek only** for discovery (+ draft in US-079) |
| Later models | Provider-**pluggable** seam (do not hard-wire US-only vendors) |
| Inputs v1 | Authority brief + editorial canon topic spaces + soft anti-dup vs recent blogs; optional durable primary material for **thesis** formation |
| Out of v1 | RSS/news APIs as primary driver; “top stories”; comparative product hot-takes |
| Batch ceiling | ≤ `max_drafts_per_weekly_run` from `load_gap_operator_settings()` (default **2**) |
| BL-020 | Optional enrichment only — **MUST NOT** be required to run discovery |

**Runtime discovery (US-078):** authenticated `POST /flow-b/discover-topics` is the worker topic-discovery step (capability `flow-b-topic-discovery`). It returns structured topic choices (`thesis`, `referent_positioning`, `rationale`, `topic_id`) suitable for later attachment to draft packages (US-079). Optional gap context (`target_week`, `empty_days[]`) is informational only — not a filesystem inventory of `ready/` or `pending-approval/`. Discovery **MUST NOT** write under `blog-posts/ready/` or `blog-posts/pending-approval/`. Fail closed with an operator-visible error when no objective-aligned topic can be produced. **Discovery does not implement** draft generation (US-079), approve/promote (US-080/US-081), or gap trigger (US-082).

---

## 5b. Blog draft generation (US-079 — policy + runtime)

| Item | Normative |
|------|-----------|
| v1 text model | **DeepSeek only** (provider-pluggable seam parallel to US-078) |
| Hero image | Existing ComfyUI blog image path; respect enablement flags; honor `dry_run` |
| Destination | `blog-posts/pending-approval/` Markdown + `.png` sibling pair (+ `.flow-b.json` sidecar) |
| Batch ceiling | ≤ `max_drafts_per_weekly_run` from `load_gap_operator_settings()` (default **2**) |
| Anti-AI | **Blocking** at draft time per `#anti-ai-writing-rules` (Flow B generated content) |
| Forbidden | Writes to `ready/`; Flow A publish/package/schedule; LinkedIn API publish; auto-publish |

**Runtime draft generation (US-079):** authenticated `POST /flow-b/generate-blog-drafts` is the worker step that materializes approval-ready packages from US-078 topic payloads (capability `flow-b-blog-draft-generation`). Optional gap context (`target_week`, `empty_days[]`) is persisted in sidecar metadata when provided. Draft generation **MUST NOT** write under `blog-posts/ready/`, invoke Flow A lifecycle, or enable LinkedIn API publication. **Draft generation does not implement** approve/reject presentation (US-080), promote (US-081), or gap trigger (US-082).

---

## 5c. Blog draft approve/reject presentation (US-080 — policy + runtime)

| Item | Normative |
|------|-----------|
| Operator surface | **Silverman Authority Manager** (extend existing console — not a separate Flow B app) |
| Read surface | `blog-posts/pending-approval/` packages (`.md` + `.png` + `.flow-b.json`) |
| Actions | Authenticated **approve** and **reject** via worker HTTP |
| Approve | Records durable sidecar decision only; **MUST NOT** promote/move to `blog-posts/ready/` |
| Reject | Marks rejected/blocked; **MUST NOT** promote to `ready/`; remains non-publishable |
| Non-goals | Revision-history CMS; structured multi-round feedback; mandatory edit-apply loop; promote/spill A; gap trigger |

**Runtime approve/reject (US-080):** authenticated `GET /flow-b/pending-approval-drafts` (+ detail + confined image) and `POST …/approve` / `…/reject` plus the Authority Manager **Flow B drafts** panel present pending drafts (title/topic, body, image, discovery summary; gap week / empty-days when present). Approve returns `promoted: false` / `promotion_pending: true`. **Approve/reject does not implement** promote-to-`ready/` or spill algorithm A (US-081), or gap trigger (US-082).

---

## 6. Related documents

- [GLOSSARY.md](../GLOSSARY.md) — Flow B, Silverman Authority Manager, `pending-approval`  
- [silverman-editorial-system.md](../../content-strategy/silverman-editorial-system.md) — `#flow-a-vs-flow-b`  
- [linkedin-draft-review-flow.md](../workflows/linkedin-draft-review-flow.md) — superseded LinkedIn-mandatory framing  
- [linkedin-variant-review-policy.md](linkedin-variant-review-policy.md) — Flow A optional LinkedIn supervision (unchanged)  
- Product: [backlog.md](../product/backlog.md) P4, [user-stories.md](../product/user-stories.md) US-074–US-082  
