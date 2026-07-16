## Context

US-015 (`docs/operations/linkedin-variant-review-policy.md`) established Flow A **strategy-driven publication** (all scheduled variants expected to publish unless operator override) and the **optional supervision window** while `publish_state` is `pending`. Operators supervising variants need criteria to answer: *“Is this variant good enough and distinct enough to publish for its intended audience/objective?”*

Editorial canon (`content-strategy/silverman-editorial-system.md`) already defines audience lenses (`#audience-map`), variant objectives and structures (`#linkedin-derivative-package`), no-redundancy rules (`#no-redundancy-rules`), anti-AI posture for derivatives (`#anti-ai-writing-rules`), and distribution sequencing (`#linkedin-distribution-strategy`). US-016 **operationalizes** those rules for the supervision window without re-deriving canon or reopening US-015 defaults.

**Current implementation gap:** `DEFAULT_VARIANT_EDITORIAL_MAP` in `linkedin_package_flow.py` maps `audience` + `tone` into campaign `variants[]`. Canonical `flow-a-automatic-publishing` already expects `objective` per variant; `tone` is voice/style, not publication purpose.

**Constraints:** ADR-0001; US-011; no BL-007 WIP merge; no `linkedin_publication_flow.py` changes; smallest docs-first diff with optional minimal metadata alignment.

## Goals / Non-Goals

**Goals:**

- Publish operator-facing quality and differentiation criteria linked from US-016, US-015 policy, and GLOSSARY.
- Normatively map default variant IDs to primary audience lens + publication objective + differentiation checks.
- Distinguish criteria guidance from US-015 publication defaults and from US-017 enforcement mechanics.
- Communicate criteria-failure guidance vs technical blocks vs deferred capabilities.
- Optionally persist `objective` in `variants[]` metadata so association is visible in campaign JSON.

**Non-Goals:**

- US-017 edit/cancel/defer worker mechanics or supervision console.
- BL-007 auto-queue, n8n publish-pending, deploy scripts.
- New HTTP routes or automated queue-time criteria enforcement.
- Rewriting US-015 policy sections (cross-link updates only).
- BL-006 closure or Flow B implementation.
- Similarity-check automation (`#no-redundancy-rules` future validation).

## Decisions

### D1 — Separate criteria doc vs section in US-015 policy

**Decision:** Create **`docs/operations/linkedin-variant-quality-criteria.md`** as a dedicated US-016 artifact. Update US-015 policy only to cross-link (remove US-016 from deferred out-of-scope list; add “see criteria doc” pointer).

**Rationale:** US-015 policy is already scoped and validated. Quality/differentiation content is substantial (mapping table, checklist, failure semantics). Separation mirrors US-015 discipline and keeps policy readable.

**Rejected:** Large new section inside `linkedin-variant-review-policy.md` — risks blurring publication-default policy with editorial QA criteria.

### D2 — “Objective” vs editorial “tone” / hook / CTA

**Decision:** Use canon definitions consistently:

| Term | Meaning in US-016 |
|------|-------------------|
| **Audience lens** | Primary reader segment from `#audience-map` (e.g. Recruiters, Software architects) |
| **Audience (metadata)** | Human-readable audience string already in `variants[]` — maps to lens |
| **Objective** | Publication purpose — what the variant optimizes for (canon `#linkedin-derivative-package` “Objective” column, e.g. “Signal seniority, scope, hireable judgment”) |
| **Tone** | Voice/style constraint for generation (existing `tone` field) — **not** a substitute for objective |
| **Hook / structure / CTA** | Differentiation dimensions per `#no-redundancy-rules` — evaluated in quality checklist |

**Rationale:** Resolves ambiguity between `tone` in worker metadata and `objective` in flow-a spec. Operator evaluates objective + differentiation; tone supports voice fit.

### D3 — Operator checklist vs normative criteria table

**Decision:** **Both**, with clear hierarchy:

1. **Normative mapping table** (source of truth): variant ID → audience lens → objective → structure sketch → differentiation checks.
2. **Supervision-window checklist** (derived): condensed pass/fail questions operators use while `pending` — references the table and canon anchors.

**Rationale:** Table satisfies traceability and AC2; checklist satisfies AC3 (understandable during supervision). Checklist does not introduce requirements beyond the table.

### D4 — Anti-AI rules: blocking posture for derivatives vs warnings for Flow A blog

**Decision:** Criteria doc states that generated LinkedIn derivatives follow **`#anti-ai-writing-rules` rewrite/blocking posture** (not Flow A blog warning posture). US-016 documents this as **quality criteria for operator judgment** during supervision — not new automated blocking at package or queue time.

**Rationale:** Matches editorial canon. US-016 is docs/spec-first; automated rewrite enforcement remains future generation/validation work. Operator who detects AI-sounding patterns should edit or defer (US-017 mechanics).

### D5 — “Blocked state” when criteria fail

**Decision:** Criteria failure is **editorial guidance**, not a new worker `publish_state` or queue gate in US-016:

| Condition | Classification | Operator implication |
|-----------|----------------|----------------------|
| Variant passes criteria | Normal supervision | Proceed per US-015 strategy unless other override |
| Variant fails quality/differentiation | **Criteria failure** (documented) | Operator SHOULD edit, defer, or cancel during supervision — **US-017 mechanics to persist override** |
| `pending` before `scheduled_at_utc` | Normal supervision window | Not a failure (US-015) |
| Enablement off / `failed` / OAuth | Technical block | Existing publication semantics |
| US-017 / console absent | Deferred capability | Criteria still apply to human judgment; absence is not worker defect |

**Rationale:** Preserves US-015 strategy-driven defaults. Criteria inform optional supervision; they do not silently convert Flow A into mandatory approval.

### D6 — Metadata extension for audience + objective (AC2)

**Decision:** **Yes — minimal worker change.** Add `objective` to `DEFAULT_VARIANT_EDITORIAL_MAP` and `_variant_metadata_entry()` output. Keep existing `audience` and `tone` fields. Optionally add `audience_lens` (canon lens name, e.g. `recruiters`) for machine-readable association — single string from mapping table.

**Rationale:** `flow-a-automatic-publishing` already requires `objective` in `variants[]`; implementation currently diverges. Persisting `objective` makes AC2 visible in campaign metadata without console UI. Smallest diff: one map + one metadata builder — no publication flow changes.

**Rejected:** Documentation-only AC2 — insufficient for “outcome visible” when operator inspects `metadata/campaigns/*.json`.

**Rejected:** Full `audience_lens` worker loading from canon at runtime — defer; static map mirrors existing `DEFAULT_VARIANT_EDITORIAL_MAP` pattern.

### D7 — Default variant mapping (normative)

| Variant ID | Primary audience lens | Publication objective | Differentiation focus |
|------------|----------------------|---------------------|------------------------|
| `executive-recruiter` | Recruiters + C-level | Signal seniority, scope, hireable judgment in 60-second read | Business outcome framing; distinct hook from technical variants |
| `technical-architect` | Software architects | Teach the design move; name trade-offs | Constraint → pattern arc; deepest technical angle |
| `engineering-leadership` | Engineering managers | Team/delivery implications of the architectural choice | Leadership stakes; coaching angle |
| `short-provocative` | Senior ICs + enthusiasts | One sharp insight; pattern interrupt | Shortest form; boldest opening; no blog-summary opener |

Sibling variants in the same package MUST differ on hook, objective angle, structure, and CTA phrasing per `#no-redundancy-rules`.

### D8 — Tests

**Decision:** Add `tests/test_linkedin_variant_quality_criteria.py` mirroring US-015 policy test style (file exists, required headings/phrases, cross-links). If metadata change applied, extend existing package metadata tests to assert `objective` present for default variants.

### D9 — No new HTTP surface

**Decision:** No worker routes. ADR-0001 preserved. No `linkedin_publication_flow.py` edits.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Operators treat criteria failure as mandatory block | Explicit D5 table: criteria guide supervision; US-015 defaults unchanged |
| Criteria doc duplicates editorial canon | Criteria doc references canon anchors; editorial-canon delta requires consumption not duplication |
| `objective` metadata change affects downstream consumers | Additive field only; keep `tone`; align with existing flow-a spec |
| Criteria without US-017 leave no persisted override | Document defer to US-017; operator uses judgment + draft edits manually until then |

## Migration Plan

1. Apply docs + delta specs + tests.
2. Optional: deploy worker with `objective` in new packages only (existing campaigns unchanged until regenerate).
3. No enablement, n8n, or BL-007 changes.
4. Update CURRENT-STATE / product progress after AC walkthrough.

## Open Questions

1. **Similarity check automation** for hook/CTA overlap — remain deferred per canon “Validation (future)”.
2. **`audience_lens` field** — include in initial apply if trivial; otherwise document as follow-up when canon runtime loading lands.
3. **US-017** — whether criteria failure sets a future `review_state` — deferred; criteria doc references intended operator actions only.
