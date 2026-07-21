# Business and content metrics (US-053)

**Scope:** BL-022 / US-053 — operator-facing definition of **business and content metrics**: blog traffic; LinkedIn reach and engagement; profile visits and audience growth. Includes intended sources, measurement period, tracking procedure, blocked/unavailable vocabulary, and supporting reuse of existing publication evidence as **eligibility context only**.
**Status:** Definition published (documentation/contract). Automated collection (**BL-023**), US-054 outcome metrics (conversations, opportunities, high-performing topics/formats), analytics platforms, and metrics dashboards are **not** implemented by this document. **US-053 Story accepted and BL-022 closure require operator review beyond this docs change.** This document does **not** close BL-020 / US-049–US-050.
**Authority:** Complements [GLOSSARY.md](../GLOSSARY.md), [CURRENT-STATE.md](../CURRENT-STATE.md), [user-stories.md](../product/user-stories.md) US-053, and publication honesty in Silverman Authority Manager (US-083 **Live on LinkedIn** / **Published on blog**).
**OpenSpec:** `openspec/changes/define-business-and-content-metrics-us-053` (capability `business-and-content-metrics`).
**Operator log template:** [business-and-content-metrics-log-TEMPLATE.md](business-and-content-metrics-log-TEMPLATE.md).

This document is the shared written meaning of US-053 metrics for the business owner and content operator. It does **not** change Flow A publish/package/schedule, Flow B discover/draft/gap-trigger/promote, n8n, LinkedIn publish-due cron, OAuth, or `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`. Metrics presence or freshness MUST NOT gate those pipelines.

---

## 1. What this is (and is not)

| This document | MUST NOT mean |
|---------------|---------------|
| Named metric families, plain-language definitions, intended sources, review cadence | An analytics warehouse, BI dashboard, or required GA/LinkedIn Analytics API worker |
| Manual-first tracking procedure + durable log template | Automated periodic collection (that is **BL-023**) |
| Eligibility context from campaign/calendar/Authority Manager honesty | A second publication pipeline that “produces” impressions |
| US-053 Story 1 definition | US-054 conversations / opportunities / topic-format performance |
| Definition published in CURRENT-STATE | Story accepted or BL-022 closed |

**Operational metric chips are not business metrics.** Authority Manager at-a-glance counts (upcoming, pending, due soon, deferred, blocked, failed, recently published) are **triage for publication operations**. They answer “what needs attention in the console,” not “did the content program attract traffic or grow the audience.” See [GLOSSARY.md](../GLOSSARY.md) (**business and content metrics** vs **operational metric chips**).

---

## 2. Measurement period and timezone

| Parameter | Normative default |
|-----------|-------------------|
| **Default period** | **Calendar month** (operator-local) |
| **Operator-facing dates** | **America/Bogota** (consistent with publishing-window guidance) |
| **Optional windows** | Per-post or per-campaign window **after** the content is eligible: **Published on blog** (site live / confirmed public URL) for blog traffic; **Live on LinkedIn** (or an explicitly documented manual-post exception) for LinkedIn post metrics |

Record the period label in the operator log (e.g. `2026-07`) and the timezone used for period boundaries.

**MUST NOT:** Treat blog handoff alone as measured live traffic. **MUST NOT:** Treat `distribution_scheduled`, package-complete, `pending`, `queued`, or unqualified “Flow A complete” / `flow_a_complete` as LinkedIn reach or engagement.

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

---

## 5. Profile visits and audience growth

**Intent:** Is the audience finding the profile and growing?

| Metric | Definition | Why it matters | Intended source (manual-first) |
|--------|------------|----------------|--------------------------------|
| **Profile views** | Profile view count for the measurement period | Whether content/program activity draws people to the profile | LinkedIn profile analytics UI |
| **Follower count (period end)** | Follower count at the end of the period | Audience size baseline | LinkedIn profile / followers UI |
| **Net follower change** | Period-end follower count minus prior period-end (or start-of-period) count | Growth (or decline) over time | Computed from successive log entries |

Automated LinkedIn Analytics API ingestion is **not** required for US-053.

---

## 6. Operator tracking procedure

Manual recording from external UIs is the first tracking method. Automation is owned by a later change (**BL-023**), not this definition.

1. **Pick the period** — default calendar month in **America/Bogota**; optionally add per-post/per-campaign rows after Live on LinkedIn / Published on blog.
2. **Confirm eligibility context** — use Authority Manager / campaign / calendar to list what was **Published on blog** and **Live on LinkedIn** (or document a manual-post exception). Do not invent zeros for ineligible items.
3. **Read values** from the intended sources above (hosting/web analytics; LinkedIn post analytics; LinkedIn profile analytics).
4. **Record** into a durable operator log using [business-and-content-metrics-log-TEMPLATE.md](business-and-content-metrics-log-TEMPLATE.md) (copy a period section into an operator-owned log file or spreadsheet as preferred; keep secrets out of git).
5. **Label blocked states** with the vocabulary in §7 — never substitute measured **zero** for **not configured**, **unavailable**, or **not applicable**.
6. **Review cadence** — at least once per calendar month after the period closes (or sooner after a notable Live on LinkedIn / Published on blog wave).

Empty or missing metrics MUST NOT change Flow A or Flow B success paths.

---

## 7. Blocked / unavailable vocabulary

Distinguish these classes — they are **not** interchangeable:

| State | Meaning | Example |
|-------|---------|---------|
| **Not configured** | Analytics product / access not set up | No web analytics on the blog yet |
| **Unavailable** | Source temporarily inaccessible or analytics lag | LinkedIn analytics UI down; export delayed |
| **Not applicable** | No eligible published content in the period | No Live on LinkedIn posts that month |
| **Zero (measured)** | Source returned an actual numeric zero | Post went live; analytics shows 0 reactions |
| **Blocked by publication honesty** | Scheduled / pending / package-complete / `distribution_scheduled` must not be counted as LinkedIn reach | Operator tries to record impressions for a Scheduled variant |

Numeric **zero** MUST NOT be used to mean “not configured” or “not applicable.”

---

## 8. Supporting evidence reuse (context only)

MAY reuse without building a second pipeline:

- Campaign metadata (`metadata/campaigns/<campaign-id>.json`)
- Editorial calendar / schedule-visibility
- Authority Manager publication honesty (**Live on LinkedIn**, **Published on blog**, Waiting to send, Scheduled)

These answer **eligibility** (“what shipped when”) for the measurement period. They are **not** substitutes for impressions, page views, or follower counts.

---

## 9. Non-goals (this change)

- **US-054** — recruiter/executive conversations; job/consulting opportunities; high-performing topics/formats.
- **BL-023 / US-055–US-056** — consistent automated collection; theme/variant comparison; feeding insights into planning.
- Analytics platform, warehouse, BI dashboard, or required GA / LinkedIn Analytics API auto-fetch worker routes.
- Mutating `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, auto-publishing LinkedIn, or treating package/schedule as API-published.
- Gating Flow A publish/package/schedule or Flow B discover/draft/gap-trigger/promote on metrics presence or freshness.
- Closing **BL-020 / US-049–US-050** or marking them Story accepted.
- Closing **BL-022**, marking US-053 Story accepted, or deploying by documentation alone.

---

## 10. Preserved behavior

- ADR-0001 (n8n → worker HTTP only) and ADR-0002 (blog canonical) unchanged.
- LinkedIn publication enablement guard unchanged.
- Flow A / Flow B pipelines remain independent of metrics collection.
- BL-020 editorial backlog remains implemented-but-open (optional enrichment only).
