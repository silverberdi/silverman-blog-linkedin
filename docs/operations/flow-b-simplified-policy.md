# Flow B simplified policy (US-074 / US-075)

**Status:** Policy defined 2026-07-19 (documentation). **US-076** gap operator settings persistence is **implemented and deployed**. **US-077** next-week gap **detect** is **implemented locally** (authenticated `GET /flow-b/calendar-gaps`; not Story accepted / not deployed as of apply). **US-078–US-082** runtime (discovery, draft, approve, trigger) remains **not** implemented.
**Story IDs:** renumbered 2026-07-19 to match apply order (settings=076 … trigger=082).
**Product surface:** **Silverman Authority Manager**
**Planning authority:** [planning-notes-flow-b-simplification.md](../product/planning-notes-flow-b-simplification.md)
**Stories:** BL-016 — [US-074](../product/user-stories.md), [US-075](../product/user-stories.md); settings SoT — [US-076](../product/user-stories.md); gap detect — [US-077](../product/user-stories.md)
**OpenSpec:** `openspec/changes/define-simplified-flow-b-us-074-075` (capability `flow-b-simplified-process`); settings capability `flow-b-gap-operator-settings` (US-076); detect capability `flow-b-calendar-gap-detect` (US-077)

This document is the operator-facing normative policy for simplified Flow B. Editable gap operator settings are persisted via **Postgres `silverman_linkedin_db` + Silverman Authority Manager UI** (US-076 / `GET`+`PUT /flow-b/gap-operator-settings`), with documented defaults including `gap_trigger_enabled=false`. **Runtime next-week LinkedIn gap detection** is provided by capability `flow-b-calendar-gap-detect` (US-077): authenticated detect-only `GET /flow-b/calendar-gaps` returns `gaps[]` / no-gap for the next operator-local week using settings from US-076, without mutating campaigns or starting drafts. Detect **MAY** run for inspection when `gap_trigger_enabled=false`; auto-trigger remains a separate fail-closed capability (US-082). This document does **not** implement trigger, discovery, draft, or approve endpoints.

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

## 5. Discovery posture (US-078 — policy recorded here)

| Item | Normative |
|------|-----------|
| v1 model | **DeepSeek only** for discovery + draft |
| Later models | Provider-**pluggable** seam (do not hard-wire US-only vendors) |
| Inputs v1 | Authority brief + editorial canon topic spaces + soft anti-dup vs recent blogs; optional durable primary material for **thesis** formation |
| Out of v1 | RSS/news APIs as primary driver; “top stories”; comparative product hot-takes |

---

## 6. Related documents

- [GLOSSARY.md](../GLOSSARY.md) — Flow B, Silverman Authority Manager, `pending-approval`  
- [silverman-editorial-system.md](../../content-strategy/silverman-editorial-system.md) — `#flow-a-vs-flow-b`  
- [linkedin-draft-review-flow.md](../workflows/linkedin-draft-review-flow.md) — superseded LinkedIn-mandatory framing  
- [linkedin-variant-review-policy.md](linkedin-variant-review-policy.md) — Flow A optional LinkedIn supervision (unchanged)  
- Product: [backlog.md](../product/backlog.md) P4, [user-stories.md](../product/user-stories.md) US-074–US-082  
