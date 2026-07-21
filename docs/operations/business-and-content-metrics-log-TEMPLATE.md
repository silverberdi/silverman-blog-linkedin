# Business and content metrics — operator log template (US-053)

**Purpose:** Lightweight durable place to record period values for US-053 metrics without a worker DB or analytics API.  
**Normative definitions:** [business-and-content-metrics.md](business-and-content-metrics.md).  
**Usage:** Copy a period block into an operator-owned log (markdown under `docs/operations/` **only if** it contains no secrets, or a private spreadsheet). Do not commit credentials, cookies, or personal analytics tokens.

**Blocked-state vocabulary:** `not configured` | `unavailable` | `not applicable` | `zero (measured)` | `blocked by publication honesty` — see normative doc §7. Do not use numeric `0` for not configured / not applicable.

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

### Blog traffic

| Metric | Value or state | Source | Notes |
|--------|----------------|--------|-------|
| Page views | | | |
| Unique visitors (if available) | | | |
| Top posts by views | | | |
| Referral / landing (if available) | | | |

### LinkedIn reach and engagement (Live on LinkedIn or documented manual exception only)

| Post identity (URN / URL / campaign+variant) | Impressions/reach | Reactions | Comments | Shares/reposts | Engagement rate | State / notes |
|----------------------------------------------|-------------------|-----------|----------|----------------|-----------------|---------------|
| | | | | | | |

### Profile visits and audience growth

| Metric | Value or state | Source | Notes |
|--------|----------------|--------|-------|
| Profile views (period) | | | |
| Follower count (period end) | | | |
| Follower count (prior period end) | | | |
| Net follower change | | | Computed: end − prior |

### Period review notes

- What went well:
- What to investigate next month:
- Follow-ups for US-054 / BL-023 (do not invent ad-hoc automation here):
