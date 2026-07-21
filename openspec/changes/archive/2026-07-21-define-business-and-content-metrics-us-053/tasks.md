## 1. Normative metrics definition

- [x] 1.1 Create `docs/operations/business-and-content-metrics.md` covering: blog traffic metrics (page views, unique visitors when available, top posts by views, referral/landing when available); LinkedIn reach and engagement (impressions/reach, reactions, comments, shares/reposts, engagement rate when computable) with Live-on-LinkedIn eligibility only; profile visits and audience growth (profile views, follower count, net follower change); default calendar-month period + America/Bogota operator dates; intended sources (manual-first); supporting reuse of campaign/calendar/Authority Manager honesty as eligibility context only; blocked-state vocabulary (not configured / unavailable / not applicable / zero measured / blocked by publication honesty); operator tracking procedure + lightweight durable log template; explicit non-goals (no US-054; no BL-023 automation; no analytics platform; no Flow A/B gating; no `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` mutation; no BL-020 close)
- [x] 1.2 Add a lightweight operator metrics log template (same ops doc appendix or sibling file under `docs/operations/`) so “track” has a durable place to record period values without a worker DB or analytics API
- [x] 1.3 Cross-link from product backlog / user-stories BL-022 section (pointer only) and from any adjacent ops policy that operators might confuse with business metrics (e.g. Authority Manager operational chips ≠ US-053 metrics) — do not rewrite Flow A/B specs

## 2. Glossary and status pointers

- [x] 2.1 Add concise `docs/GLOSSARY.md` entries as needed for **business and content metrics**, and distinguish them from Authority Manager **operational metric chips** / campaign lifecycle completion language — do not redefine `flow_a_complete`, handoff vs published, or Live on LinkedIn
- [x] 2.2 Update `docs/CURRENT-STATE.md` to note business and content metrics **definition published** (US-053 docs) and that automated collection / US-054 outcome metrics remain not implemented; do not claim Story accepted; do not close BL-020
- [x] 2.3 Optionally add a one-line help pointer in Authority Manager only if visibility AC still needs it after docs + CURRENT-STATE; default is docs-only (no metrics dashboard)

## 3. Product progress (post-doc, not Story accepted)

- [x] 3.1 Mark US-053 Work started in `docs/product/progress-checklist.md` after definition artifacts exist; leave Story accepted / BL-022 / US-054 unchecked
- [x] 3.2 Do **not** check off US-053 acceptance criteria in `docs/product/user-stories.md` as Story accepted; leave checkboxes for operator review after apply
- [x] 3.3 Confirm no Flow A/B pipeline gating, no required analytics auto-fetch routes, no LinkedIn enablement mutation, and no BL-020 Story accepted / close were introduced by this change

## 4. Verification

- [x] 4.1 Walk US-053 acceptance criteria against the committed docs and record any gap (docs/contract-first; full pytest not required unless optional console pointer ships)
- [x] 4.2 Run `git diff --check` on changed files
- [x] 4.3 Business validation: business owner can open the US-053 ops definition and CURRENT-STATE pointer and recognize blog traffic, LinkedIn reach/engagement, and profile/audience growth metrics plus blocked-state vocabulary — Story accepted remains an explicit operator gate after review
