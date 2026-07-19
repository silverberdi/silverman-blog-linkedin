## Context

Flow A is operational with LinkedIn supervision console. P4 Flow B product decisions are locked in [planning-notes-flow-b-simplification.md](../../../docs/product/planning-notes-flow-b-simplification.md) and US-074–US-082. This change is **documentation/policy only**: establish normative artifacts so later runtime OpenSpec changes do not re-litigate process boundaries.

Stakeholders: content operator (Silverio); implementers applying US-082 onward.

Constraints: ADR-0001 (n8n → HTTP only); blog canonical (ADR-0002); calendar Postgres SoT (US-041 / ADR-0004) unchanged; no application code in this change.

## Goals / Non-Goals

**Goals:**

- Normative ops policy + glossary/editorial alignment for simplified Flow B.
- Encode weekly gap policy, `pending-approval/` eligibility, Authority Manager naming, DeepSeek v1 / pluggable note, spill A, n8n→HTTP intent.
- Provide a capability spec that later runtime changes MUST not contradict.

**Non-Goals:**

- Runtime endpoints, DB settings, n8n workflow files, LLM calls, console UI, filesystem mkdir automation beyond documenting the folder contract.

## Decisions

1. **Docs-only first change** — US-074/075 are definition stories; implementing sensor/UI in the same change would mix unrelated capabilities.
   - Alternative considered: mega-change for all P4 → rejected (too large; violates one coherent capability).

2. **Single new capability `flow-b-simplified-process`** — holds process + eligibility/gap policy requirements as documentation contracts (scenarios verify doc presence and normative statements, not HTTP).
   - Alternative: split two capabilities → unnecessary for docs-only slice.

3. **Canonical ops doc** — `docs/operations/flow-b-simplified-policy.md` as the operator-facing normative policy; glossary + editorial `#flow-a-vs-flow-b` must agree; planning notes remain product planning authority for P4 knobs.
   - Alternative: only update glossary → too thin for US-075 “publish normative policy”.

4. **No delta to Flow A LinkedIn publication specs** — process docs must not alter `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` or publish-due behavior.

## Risks / Trade-offs

- [Risk] Doc drift vs later runtime design → Mitigation: runtime changes MUST cite this capability; resolve conflicts via new OpenSpec change.
- [Risk] Partial glossary updates leave old “daily gap” language → Mitigation: tasks include explicit grep/pass for outdated Flow B gap wording in touched docs.
- [Risk] Operator expects runtime after this change → Mitigation: progress checklist stays Work started / not Story accepted until docs demonstrated; CURRENT-STATE notes “policy defined, runtime not implemented”.

## Migration Plan

1. Apply doc updates on Mac branch.
2. No deploy required for capability; optional doc sync on server is operator preference.
3. Rollback: revert change commit; no data migration.

## Open Questions

- None for this docs slice. Runtime path names (exact HTTP routes for US-080/081) deferred to those changes.
