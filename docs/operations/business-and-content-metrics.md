# Business and content metrics (US-053 / US-054)

**Scope:** BL-022 — operator-facing definition of **business and content metrics**:
- **US-053 (Story 1):** blog traffic; LinkedIn reach and engagement; profile visits and audience growth.
- **US-054 (Story 2):** recruiter and executive conversations; job and consulting opportunities; high-performing topics and formats.

Includes intended sources, measurement period, tracking procedure, blocked/unavailable vocabulary (with US-054-specific none-recorded vs zero-measured guidance), and supporting reuse of existing publication evidence as **eligibility context only**.
**Status:** Definition published (documentation/contract) for US-053 and US-054. Automated collection (**BL-023**), analytics platforms, and metrics dashboards are **not** implemented by this document. **US-053 Story accepted, US-054 Story accepted, and BL-022 closure require operator review beyond this docs change.** This document does **not** close BL-020 / US-049–US-050.
**Authority:** Complements [GLOSSARY.md](../GLOSSARY.md), [CURRENT-STATE.md](../CURRENT-STATE.md), [user-stories.md](../product/user-stories.md) US-053 / US-054, and publication honesty in Silverman Authority Manager (US-083 **Live on LinkedIn** / **Published on blog**).
**OpenSpec:** capability `business-and-content-metrics` (`define-business-and-content-metrics-us-053`; `define-business-outcome-metrics-us-054`).
**Operator log template:** [business-and-content-metrics-log-TEMPLATE.md](business-and-content-metrics-log-TEMPLATE.md).

This document is the shared written meaning of BL-022 metrics for the business owner and content operator. It does **not** change Flow A publish/package/schedule, Flow B discover/draft/gap-trigger/promote, n8n, LinkedIn publish-due cron, OAuth, or `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`. Metrics presence or freshness (including US-054 outcome rows) MUST NOT gate those pipelines.

---

## 1. What this is (and is not)

| This document | MUST NOT mean |
|---------------|---------------|
| Named metric families, plain-language definitions, intended sources, review cadence | An analytics warehouse, BI dashboard, or required GA/LinkedIn Analytics API worker |
| Manual-first tracking procedure + durable log template | Automated periodic collection, theme/variant comparison engines, or planning-automation feed (that is **BL-023**) |
| Eligibility context from campaign/calendar/Authority Manager honesty | A second publication pipeline that “produces” impressions or invents conversations |
| US-053 traffic/reach/audience-growth definition **and** US-054 outcome definition | CRM/ATS as system of record; ranks invented from schedule/pending/package-complete |
| Definition published in CURRENT-STATE | Story accepted (US-053 or US-054) or BL-022 closed |

**Operational metric chips are not business metrics.** Authority Manager at-a-glance counts (upcoming, pending, due soon, deferred, blocked, failed, recently published) are **triage for publication operations**. They answer “what needs attention in the console,” not “did the content program attract traffic, grow the audience, or produce professional outcomes.” See [GLOSSARY.md](../GLOSSARY.md) (**business and content metrics** vs **operational metric chips**).

**One-way engagement is not a conversation.** LinkedIn reactions, likes, and one-way comments without a two-way exchange remain **US-053 engagement** — they do **not** count as US-054 conversations.

---

## 2. Measurement period and timezone

| Parameter | Normative default |
|-----------|-------------------|
| **Default period** | **Calendar month** (operator-local) |
| **Operator-facing dates** | **America/Bogota** (consistent with publishing-window guidance) |
| **Optional windows** | Per-post or per-campaign window **after** the content is eligible: **Published on blog** (site live / confirmed public URL) for blog traffic; **Live on LinkedIn** (or an explicitly documented manual-post exception) for LinkedIn post metrics. Outcome metrics (conversations / opportunities) use the **same period label** in the log; optional per-campaign notes when attribution is known. |

Record the period label in the operator log (e.g. `2026-07`) and the timezone used for period boundaries. US-053 and US-054 rows for a period share that label.

**MUST NOT:** Treat blog handoff alone as measured live traffic. **MUST NOT:** Treat `distribution_scheduled`, package-complete, `pending`, `queued`, or unqualified “Flow A complete” / `flow_a_complete` as LinkedIn reach, engagement, or high-performing evidence.

---

## 3. Blog traffic metrics

**Intent:** Did published blog content attract attention?

| Metric | Definition | Why it matters | Intended source (manual-first) |
|--------|------------|----------------|--------------------------------|
| **Page views** | Count of page views for the site (or scoped posts) in the measurement period | Overall attention to published blog content | Hosting / GitHub Pages analytics, or a configured web analytics product if the operator installs one later |
| **Unique visitors** | Distinct visitors in the period **when the source provides them** | Reach breadth vs raw view volume | Same as above — omit or mark **unavailable** if the source does not provide uniques |
| **Top posts by views** | Ranked list of posts by views in the period | Which topics/posts drew attention | Same analytics source; list slug/title + views |
| **Referral / landing context** | Referrers or landing pages **when available** | Whether LinkedIn (or other channels) drove visits | Same analytics source — omit or mark **unavailable** when not provided |

**Eligibility:** Prefer measuring posts that are **Published on blog** / site live (public HTTP reachability). Blog handoff to the public checkout is **not** equivalent to measured live traffic.

**Until analytics is configured:** status is **not configured** (or **unavailable** if access is temporarily broken) — **not** a measured zero.

---

## 4. LinkedIn reach and engagement metrics

**Intent:** Did distribution assets get seen and interacted with?

| Metric | Definition | Why it matters | Intended source (manual-first) |
|--------|------------|----------------|--------------------------------|
| **Impressions / reach** | How many times the post was shown (impressions) or unique accounts reached (reach), per LinkedIn’s labels | Visibility of the distribution asset | LinkedIn native post analytics (or equivalent UI) |
| **Reactions** | Reaction count on the post | Lightweight engagement signal | Same |
| **Comments** | Comment count | Deeper engagement / conversation seed | Same |
| **Shares / reposts** | Share or repost count | Amplification beyond the immediate feed | Same |
| **Engagement rate** | `(reactions + comments + shares/reposts) ÷ impressions` when **both** engagements and impressions are known | Normalize engagement vs reach | Computed by the operator from recorded values; leave blank if impressions unknown |

### Eligibility (publication honesty)

LinkedIn **post** reach/engagement metrics apply only when the post is eligible as published for measurement:

- **Live on LinkedIn** (API-published with evidence, Authority Manager primary label), **or**
- An **explicitly documented manual-post exception** (operator records that the post was published manually on LinkedIn outside the guarded API path, with enough identity to find analytics).

| State | Eligible for LinkedIn reach/engagement? |
|-------|----------------------------------------|
| **Live on LinkedIn** / API `published` with evidence | Yes |
| Explicit manual-post exception (documented in the log) | Yes |
| `distribution_scheduled` / package-complete / `flow_a_complete` | **No** — **blocked by publication honesty** |
| `pending` / Scheduled / Waiting to send (`queued`) | **No** — **blocked by publication honesty** |
| Failed / Cancelled | **No** — **not applicable** (or blocked honesty if someone tries to count schedule intent) |

**MUST NOT** invent impressions from schedule metadata. Campaign metadata, calendar, and Authority Manager honesty answer **what was eligible to measure**, not how many impressions occurred.

One-way likes/reactions/comments without a two-way exchange remain in this family — they are **not** US-054 conversations (§6).

---

## 5. Profile visits and audience growth

**Intent:** Is the audience finding the profile and growing?

| Metric | Definition | Why it matters | Intended source (manual-first) |
|--------|------------|----------------|--------------------------------|
| **Profile views** | Profile view count for the measurement period | Whether content/program activity draws people to the profile | LinkedIn profile analytics UI |
| **Follower count (period end)** | Follower count at the end of the period | Audience size baseline | LinkedIn profile / followers UI |
| **Net follower change** | Period-end follower count minus prior period-end (or start-of-period) count | Growth (or decline) over time | Computed from successive log entries |

Automated LinkedIn Analytics API ingestion is **not** required for US-053 or US-054.

---

## 6. Recruiter and executive conversations (US-054)

**Intent:** Did the content program start (or meaningfully advance) professional dialogue?

### What counts as a conversation

A **recruiter or executive conversation** is a **two-way professional exchange** (message thread, email thread, call, or meeting) that was initiated or meaningfully advanced in the measurement period and related to Silverio’s professional positioning (roles, consulting, technical leadership).

| Counts | Does **not** count |
|--------|---------------------|
| Reply thread with a recruiter or hiring manager | One-way LinkedIn reaction / like alone |
| Email exchange about a role or consulting interest | Profile view alone |
| Call or meeting booked and held (or scheduled as a concrete next step after exchange) | Broadcast comment with no reply (operator judgment: if no two-way exchange, keep as US-053 engagement) |
| Warm intro that becomes a dialogue | Vague “someone might message someday” |

Operator judgment applies. Record enough identity to review later **without** committing secrets or third-party PII into git (use initials, company-only labels, or private tracker IDs).

### Recording fields (per period)

| Field | Required? | Notes |
|-------|-----------|-------|
| **Count** of qualifying conversations in the period | Yes | Use vocabulary in §11 when none |
| **Channel** (optional per row) | Optional | LinkedIn message, email, call, meeting, other |
| **Content / campaign attribution** | Optional | When known — which Published on blog / Live on LinkedIn item or theme sparked the exchange |
| **Brief note** | Optional | Non-sensitive; no secrets/PII in git-tracked logs |

### Intended sources (manual-first)

Operator-owned records: LinkedIn inbox, email, calendar notes, personal tracker, or memory — **no required CRM**.

### Review cadence

Same as US-053: at least once per calendar month after the period closes (America/Bogota), optionally sooner after a notable Live on LinkedIn / Published on blog wave or a notable conversation.

---

## 7. Job and consulting opportunities (US-054)

**Intent:** Did dialogue convert toward concrete professional prospects?

### What counts as an opportunity

A **job or consulting opportunity** is a **concrete professional prospect** the business owner is tracking (role/requisition, consulting brief, warm intro toward a scoped engagement). Vague “someone might hire me someday” without a recordable prospect is **not** an opportunity.

| Counts | Does **not** count |
|--------|---------------------|
| Named role / requisition under consideration | Unscoped “maybe someday” interest |
| Consulting brief or scoped engagement discussion | One-way recruiter InMail with no prospect identity |
| Warm intro that names a concrete opportunity path | Aspiration without a recordable prospect |

Stages are **operator labels for review**, not a CRM workflow engine.

### Recording fields (per period)

| Field | Required? | Notes |
|-------|-----------|-------|
| **Count** of opportunities in the period | Yes | Use vocabulary in §11 when none |
| **Type** | Per row when recorded | `job` / `consulting` / `other` |
| **Stage** (optional) | Optional | `identified` / `exploring` / `interview` / `offer` / `closed-won` / `closed-lost` / `not tracked` |
| **Content / campaign attribution** | Optional | When known |
| **Brief note** | Optional | Non-sensitive; no secrets/PII in git-tracked logs |

### Intended sources (manual-first)

Operator-owned records: LinkedIn inbox, email, calendar, personal tracker — **no required ATS/CRM**.

### Review cadence

Same default as conversations and US-053: at least once per calendar month after the period closes.

---

## 8. High-performing topics and formats (US-054)

**Intent:** Which themes and formats appear worth repeating?

This is **thin, operator-applied criteria** — not a BI platform, statistical comparison engine, or automated theme/variant ranking (**BL-023** owns consistent collection and comparison loops later).

### Criteria (at least one)

For a measurement period, a topic or format **MAY** be labeled high-performing when **at least one** of:

1. **Relative US-053 strength** — Among eligible **Published on blog** / **Live on LinkedIn** items, it is in the **top tier by the operator’s chosen US-053 signal** for that period (e.g. top posts by views; top posts by engagement rate or reactions when impressions are known). **Document which signal was used.**
2. **Outcome linkage** — One or more recorded conversations or opportunities in the period are **attributed** (operator judgment) to that topic/format.
3. **Qualitative note when quantitative sources are missing** — When US-053 sources are **not configured**, **unavailable**, or **not applicable**, the operator MAY still note a topic/format as noteworthy with that blocked state labeled explicitly.

### Forbidden

- **MUST NOT** invent numeric ranks from `distribution_scheduled`, package-complete, `pending`, `queued`, or unqualified Flow A completion language.
- **MUST NOT** require a comparison engine, statistical significance, or automated variant A/B.
- **MUST NOT** treat Authority Manager operational metric chips as high-performing evidence.

When using LinkedIn post metrics as evidence, **blocked by publication honesty** still applies (same eligibility as §4).

---

## 9. Operator tracking procedure

Manual recording from external UIs and operator-owned records is the first tracking method. Automation is owned by a later change (**BL-023**), not this definition.

1. **Pick the period** — default calendar month in **America/Bogota**; optionally add per-post/per-campaign rows after Live on LinkedIn / Published on blog.
2. **Confirm eligibility context** — use Authority Manager / campaign / calendar to list what was **Published on blog** and **Live on LinkedIn** (or document a manual-post exception). Do not invent zeros for ineligible items.
3. **Read US-053 values** from the intended sources above (hosting/web analytics; LinkedIn post analytics; LinkedIn profile analytics).
4. **Record US-053** into a durable operator log using [business-and-content-metrics-log-TEMPLATE.md](business-and-content-metrics-log-TEMPLATE.md) (copy a period section into an operator-owned log file or spreadsheet as preferred; keep secrets out of git).
5. **Record US-054 outcomes** — conversations and opportunities for the same period (count + optional fields); then write topic/format high-performing notes using US-053 signals where available and/or outcome attribution.
6. **Label blocked states** with the vocabulary in §11 — never substitute measured **zero** for **not configured**, **unavailable**, **not applicable**, or **not applicable — none recorded**.
7. **Review cadence** — at least once per calendar month after the period closes (or sooner after a notable Live on LinkedIn / Published on blog wave or a notable conversation).

Empty or missing metrics (including empty outcome rows) MUST NOT change Flow A or Flow B success paths.

---

## 10. Supporting evidence reuse (context only)

MAY reuse without building a second pipeline:

- Campaign metadata (`metadata/campaigns/<campaign-id>.json`)
- Editorial calendar / schedule-visibility
- Authority Manager publication honesty (**Live on LinkedIn**, **Published on blog**, Waiting to send, Scheduled)
- US-053 traffic / reach / engagement rows for the same period (supporting high-performing criteria)

These answer **eligibility** (“what shipped when”) and provide **supporting signals** for high-performing notes. They are **not** substitutes for impressions, page views, follower counts, conversations, or opportunities.

---

## 11. Blocked / unavailable vocabulary

Distinguish these classes — they are **not** interchangeable:

| State | Meaning | Example |
|-------|---------|---------|
| **Not configured** | Analytics product / access not set up (US-053); rare for conversations/opportunities (no external analytics product required) — may apply if a future private tracker is planned but not adopted | No web analytics on the blog yet |
| **Unavailable** | Source temporarily inaccessible or analytics lag | LinkedIn analytics UI down; cannot access inbox archive for the period |
| **Not applicable** | No eligible published content in the period (US-053); or outcome tracking not meaningful for a chosen signal | No Live on LinkedIn posts that month |
| **Not applicable — none recorded** | No conversation or opportunity **rows** because none occurred **or** the operator did not operate an outcome log that period — **not** the same as measured zero | Period closed without reviewing inbox / without writing outcome rows |
| **Zero (measured)** | Source returned an actual numeric zero (US-053), **or** the operator affirmatively reviewed intended sources for the period and found no qualifying conversations/opportunities | Post went live; analytics shows 0 reactions — **or** operator reviewed inbox/email/calendar and found no qualifying conversations |
| **Blocked by publication honesty** | Scheduled / pending / package-complete / `distribution_scheduled` must not be counted as LinkedIn reach or as high-performing reach evidence | Operator tries to record impressions or invent a “top post” rank for a Scheduled variant |

**Numeric zero MUST NOT mean “we did not track.”** Prefer **not applicable — none recorded** when tracking was not performed; use **zero (measured)** only after affirmative review of intended sources.

---

## 12. Non-goals (this definition)

- **BL-023 / US-055–US-056** — consistent automated collection; theme/variant comparison; feeding insights into planning.
- Analytics platform, warehouse, BI dashboard, or required GA / LinkedIn Analytics API auto-fetch worker routes.
- Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, auto-publishing LinkedIn, or treating package/schedule as API-published.
- Gating Flow A publish/package/schedule or Flow B discover/draft/gap-trigger/promote on metrics presence or freshness (including US-054 outcome rows).
- Closing **BL-020 / US-049–US-050** or marking them Story accepted.
- Closing **BL-022**, marking US-053 or US-054 Story accepted, or deploying by documentation alone.
- Inventing a CRM/ATS as the system of record in this definition.

---

## 13. Preserved behavior

- ADR-0001 (n8n → worker HTTP only) and ADR-0002 (blog canonical) unchanged.
- LinkedIn publication enablement guard unchanged.
- Flow A / Flow B pipelines remain independent of metrics collection.
- BL-020 editorial backlog remains implemented-but-open (optional enrichment only).
- US-053 Story accepted remains a separate operator gate from US-054 definition publish.
