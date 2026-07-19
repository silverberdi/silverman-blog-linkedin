# US-074 / US-075 — Flow B policy documentation walk (2026-07-19)

**Change:** `define-simplified-flow-b-us-074-075` (docs-only)  
**Normative policy:** [flow-b-simplified-policy.md](flow-b-simplified-policy.md)

## US-074 acceptance criteria

| Criterion | Result | Evidence |
|-----------|--------|----------|
| Document Flow B path incl. DeepSeek v1, `pending-approval/`, Authority Manager, promote to `ready/`, Flow A | PASS | policy §1 |
| Only mandatory gate = blog approval | PASS | policy §1 |
| No mandatory LinkedIn review after blog OK | PASS | policy §1 |
| P4 non-goals listed (incl. news-spreader, BL-020 not required) | PASS | policy §1 |
| Authority/referent objective | PASS | policy §1 |
| Silverman Authority Manager named; extend not separate app | PASS | policy §1; GLOSSARY |
| Glossary / editorial / ops updated | PASS | GLOSSARY; `#flow-a-vs-flow-b`; this policy |
| Cross-link US-075 / US-076 without runtime impl | PASS | policy §1 cross-links; no `src/` in this change |

## US-075 acceptance criteria

| Criterion | Result | Evidence |
|-----------|--------|----------|
| Eligibility: `pending-approval/` non-publishable; promote to `ready/` | PASS | policy §2 |
| Next-week gap; gap = 0 LinkedIn posts | PASS | policy §3 |
| Friday intent; min_lead 5; DB+UI; n8n→HTTP; fail-closed | PASS | policy §3 |
| max_drafts 2; ISO-week idempotency key | PASS | policy §3 |
| Spill algorithm A | PASS | policy §4 |
| Discovery posture DeepSeek v1 + pluggable; not news | PASS | policy §5 |
| Normative ops + glossary (docs story, not sensor) | PASS | this change |

## Scope check

- No worker routes, no n8n Execute Command, no `src/` mutations in this change.

**Story accepted:** 2026-07-19 (operator verify + US AC contrast).
