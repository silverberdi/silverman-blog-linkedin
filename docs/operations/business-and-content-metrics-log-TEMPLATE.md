# Business and content metrics — operator log template (US-053 / US-054 / US-055)

**Purpose:** Lightweight durable place to record period values for US-053 traffic/reach/audience-growth metrics, US-054 outcome metrics (conversations, opportunities, high-performing topic/format notes), and US-055 collection completeness / theme-variant comparison / effective-format labels — without a worker DB, analytics API, CRM, or metrics dashboard.
**Normative definitions:** [business-and-content-metrics.md](business-and-content-metrics.md) (US-053/US-054 families §§3–8; US-055 procedure §§14–16; blocked vocabulary §11).
**Usage:** Copy a period block into an operator-owned log (markdown under `docs/operations/` **only if** it contains no secrets, or a private spreadsheet). Do not commit credentials, cookies, personal analytics tokens, or third-party PII (use initials, company-only labels, or private tracker IDs).

**Blocked-state vocabulary:** `not configured` | `unavailable` | `not applicable` | `not applicable — none recorded` | `zero (measured)` | `blocked by publication honesty` — see normative doc §11. Do not use numeric `0` for not configured / not applicable / none recorded / incomplete collection.

---

## Period: YYYY-MM

| Field | Value |
|-------|-------|
| Period label | `YYYY-MM` |
| Period start (America/Bogota) | |
| Period end (America/Bogota) | |
| Recorded at (UTC or local) | |
| Recorded by | |

### Eligibility context (supporting only — not impressions)

| Channel | Eligible items in period (title / campaign_id / variant / URL) | Notes |
|---------|----------------------------------------------------------------|-------|
| Published on blog | | |
| Live on LinkedIn | | |
| Manual-post exception (if any) | Document why / where posted | |

### Blog traffic (US-053)

| Metric | Value or state | Source | Notes |
|--------|----------------|--------|-------|
| Page views | | | |
| Unique visitors (if available) | | | |
| Top posts by views | | | |
| Referral / landing (if available) | | | |

### LinkedIn reach and engagement (US-053 — Live on LinkedIn or documented manual exception only)

| Post identity (URN / URL / campaign+variant) | Impressions/reach | Reactions | Comments | Shares/reposts | Engagement rate | State / notes |
|----------------------------------------------|-------------------|-----------|----------|----------------|-----------------|---------------|
| | | | | | | |

### Profile visits and audience growth (US-053)

| Metric | Value or state | Source | Notes |
|--------|----------------|--------|-------|
| Profile views (period) | | | |
| Follower count (period end) | | | |
| Follower count (prior period end) | | | |
| Net follower change | | | Computed: end − prior |

### Recruiter and executive conversations (US-054)

**Period summary state** (pick one): `zero (measured)` | `not applicable — none recorded` | `unavailable` | other — see §11.

| # | Channel (LinkedIn message / email / call / meeting / other) | Optional content/campaign attribution | Brief non-sensitive note |
|---|------------------------------------------------------------|----------------------------------------|--------------------------|
| | | | |

**Conversation count (period):**

### Job and consulting opportunities (US-054)

**Period summary state** (pick one): `zero (measured)` | `not applicable — none recorded` | `unavailable` | other — see §11.

| # | Type (job / consulting / other) | Stage (optional) | Optional content/campaign attribution | Brief non-sensitive note |
|---|---------------------------------|------------------|----------------------------------------|--------------------------|
| | | | | |

**Opportunity count (period):**

Stage labels (optional): `identified` | `exploring` | `interview` | `offer` | `closed-won` | `closed-lost` | `not tracked`.

### High-performing topics and formats (US-054)

Document the US-053 signal used (if any). Do **not** invent ranks from schedule / pending / package-complete. Criteria: normative doc §8.

| Topic or format | Why high-performing (US-053 signal / outcome linkage / qualitative) | Signal used or blocked state | Notes |
|-----------------|---------------------------------------------------------------------|------------------------------|-------|
| | | | |

### Collection completeness (US-055)

**Pass status** (pick one): `complete` | `incomplete` — if incomplete, name unfinished families below. Incomplete collection MUST NOT be written as measured zero.

| Family | Collected? (yes / blocked state / incomplete) | Blocked state if any (§11) | Notes |
|--------|-----------------------------------------------|----------------------------|-------|
| Blog traffic (US-053) | | | |
| LinkedIn reach/engagement (US-053) | | | |
| Profile visits / audience growth (US-053) | | | |
| Conversations (US-054) | | | |
| Opportunities (US-054) | | | |
| High-performing topic/format notes (US-054) | | | |

**Unfinished families (if pass incomplete):**

### Theme and variant comparison (US-055)

Thin operator notes only. Document the signal used. Do **not** invent ranks from `distribution_scheduled` / pending / package-complete / `flow_a_complete`. When no eligible published content: record `not applicable`.

| Axis (theme/topic or variant) | Relative strength note | Signal used or blocked state | Eligibility (Published on blog / Live on LinkedIn / manual exception) |
|-------------------------------|------------------------|------------------------------|-----------------------------------------------------------------------|
| | | | |

**Period comparison summary state** (optional): `notes recorded` | `not applicable` | `unavailable` | other —

### Effective formats (US-055)

Reuse US-054 §8 high-performing criteria — do **not** invent a second criteria table. Document signal or blocked state. Do **not** invent ranks from schedule metadata. US-056 planning feed is out of scope.

| Format (or topic-as-format) | Why effective (§8: US-053 strength / outcome linkage / qualitative) | Signal used or blocked state | Notes |
|-----------------------------|---------------------------------------------------------------------|------------------------------|-------|
| | | | |

**Period effective-format summary state** (optional): `labels recorded` | `not applicable` | `unavailable` | other —

### Period review notes

- What went well:
- What to investigate next month:
- Follow-ups for US-056 (do not invent ad-hoc planning automation here):
