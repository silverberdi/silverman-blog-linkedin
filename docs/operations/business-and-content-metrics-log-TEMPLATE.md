# Business and content metrics — operator log template (US-053 / US-054)

**Purpose:** Lightweight durable place to record period values for US-053 traffic/reach/audience-growth metrics and US-054 outcome metrics (conversations, opportunities, high-performing topic/format notes) without a worker DB, analytics API, or CRM.
**Normative definitions:** [business-and-content-metrics.md](business-and-content-metrics.md).
**Usage:** Copy a period block into an operator-owned log (markdown under `docs/operations/` **only if** it contains no secrets, or a private spreadsheet). Do not commit credentials, cookies, personal analytics tokens, or third-party PII (use initials, company-only labels, or private tracker IDs).

**Blocked-state vocabulary:** `not configured` | `unavailable` | `not applicable` | `not applicable — none recorded` | `zero (measured)` | `blocked by publication honesty` — see normative doc §11. Do not use numeric `0` for not configured / not applicable / none recorded.

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

Document the US-053 signal used (if any). Do **not** invent ranks from schedule / pending / package-complete.

| Topic or format | Why high-performing (US-053 signal / outcome linkage / qualitative) | Signal used or blocked state | Notes |
|-----------------|---------------------------------------------------------------------|------------------------------|-------|
| | | | |

### Period review notes

- What went well:
- What to investigate next month:
- Follow-ups for BL-023 (do not invent ad-hoc automation here):
