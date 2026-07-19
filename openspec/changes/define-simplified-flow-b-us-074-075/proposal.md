## Why

P4 Flow B planning is locked, but glossary/policy artifacts still describe a looser or outdated gap model. US-074 and US-075 require a durable normative definition of simplified Flow B (blog-only gate, Silverman Authority Manager, weekly gap policy, `pending-approval/`, DeepSeek v1, spill A, n8n→HTTP) before runtime stories can be implemented safely.

## What Changes

- Publish normative Flow B simplified process + eligibility/gap policy as repo docs (operations policy + glossary/editorial alignment).
- Introduce capability `flow-b-simplified-process` capturing US-074/US-075 documentation contracts (no runtime sensor, settings UI, discovery, or approve endpoints in this change).
- Align product references to **Silverman Authority Manager**, `blog-posts/pending-approval/`, weekly gap defaults, DeepSeek-only v1 with pluggable seam noted for later, spill algorithm A, and n8n Schedule → worker HTTP orchestration intent.

### Goals

- Satisfy **BL-016 / US-074** and **US-075** acceptance criteria as documentation/policy (Story accepted still requires operator review after apply).
- Unblock subsequent OpenSpec changes (US-082 → … → US-081) with unambiguous policy.

### Non-goals

- No worker routes, Postgres settings store, n8n workflow activation, DeepSeek discovery/draft generation, console UI for approve, or LinkedIn spill implementation.
- No enabling other LLM providers beyond documenting the pluggable intent.
- No BL-020 topic CMS; no BL-021 cadence supersession.
- No LAN deploy or publish-pending LinkedIn cron activation (separate operational track).

### Acceptance criteria addressed

- US-074: process boundary, blog-only gate, non-goals, authority objective, Silverman Authority Manager naming, glossary/editorial policy updates, cross-links to US-075/US-082.
- US-075: eligibility (`pending-approval/` vs `ready/`), next-week gap=0, Friday/`min_lead_days`/DB+UI/n8n→HTTP intent, max 2 drafts, ISO-week idempotency key, spill A, discovery posture, normative ops + glossary docs.

### Intentionally excluded

- Runtime AC for US-076–US-082 (follow-on changes).

## Capabilities

### New Capabilities

- `flow-b-simplified-process`: Normative simplified Flow B process, eligibility, weekly gap policy, draft folder contract, and operator-surface naming for documentation and later runtime alignment.

### Modified Capabilities

- (none — documentation/policy capability; existing Flow A publication specs unchanged)

## Impact

- Docs: `docs/GLOSSARY.md`, `docs/operations/` (new Flow B policy), `content-strategy/silverman-editorial-system.md` (already partially aligned; verify), product trio cross-links.
- No `src/` or API contract changes in this change.
- Product: BL-016 US-074/US-075 progress updates only after demonstrated doc outcomes + operator Story accepted.
- Related backlog: **BL-016**; stories **US-074**, **US-075**. Planning authority: [planning-notes-flow-b-simplification.md](../../../docs/product/planning-notes-flow-b-simplification.md).
