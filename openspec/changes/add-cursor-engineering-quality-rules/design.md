## Context

`silverman-blog-linkedin` uses layered context for Cursor: canonical documentation (`docs/CURRENT-STATE.md`, `docs/CONTEXT-AUTHORITY.md`, `docs/GLOSSARY.md`, specs, ADRs), an always-on project rule at `.cursor/rules/silverman-blog-linkedin-project.mdc`, and OpenSpec injected context via `openspec/config.yaml` referencing canonical docs.

The `repository-context-governance` spec already requires the project rule to stay concise, link to canonical docs, encode workflow gates, and prevent ambiguous Flow A language. The project rule (~49 lines) covers purpose, guardrails, editorial scope, and a four-step workflow summary. It does not encode implementation-quality constraints scattered across user rules and tribal knowledge.

Three OpenSpec Cursor skills still prescribe obsolete `/opsx:` colon syntax, conflicting with `.cursor/commands/opsx-*.md`, `docs/CONTEXT-AUTHORITY.md`, and the project rule.

This change adds a second always-on engineering rule, updates CONTEXT-AUTHORITY, aligns skills, and deduplicates the project rule—without touching `openspec/config.yaml` or application code.

## Goals / Non-Goals

**Goals:**

- Create `.cursor/rules/silverman-blog-linkedin-engineering.mdc` (180–240 line target; 280 hard max; `alwaysApply: true`).
- Classify the engineering rule as Cursor execution guidance, not normative product authority.
- Lock complementary ownership between project and engineering rules.
- Add narrow CONTEXT-AUTHORITY entry for the engineering rule.
- Fix obsolete `/opsx:` syntax in skills where inspection finds it (3 files expected).
- Extend `repository-context-governance` delta spec with validation contract.

**Non-Goals:**

- `openspec/config.yaml` changes.
- Application code, tests, CI, deployment scripts, runtime config, or live operations.
- Replacing or substantially rewriting the project rule beyond deduplication.
- Multiple additional always-on rules.
- Embedding full OpenSpec command bodies in rules (commands live in `.cursor/commands/`).
- Rewriting archived OpenSpec artifacts or historical examples.

## Decisions

### D1: Single engineering rule file

**Decision:** One file `.cursor/rules/silverman-blog-linkedin-engineering.mdc`.

**Rationale:** The 16 sections share a single purpose (agent implementation quality). Splitting would multiply always-on prompt tokens and create ordering ambiguity.

### D2: Rule ownership split (locked)

| Concern | Project rule | Engineering rule |
|---------|--------------|------------------|
| Project identity and purpose | ✓ | link only |
| Canonical context links | ✓ primary | ✓ before acting |
| Architecture and product boundaries | ✓ brief | ✓ enforce in API/fs edits |
| Flow A / Flow B semantics | ✓ qualified guardrails | ✓ precise status language |
| High-level safety guardrails | ✓ | cross-reference |
| Editorial/folder layout | ✓ | — |
| Worker capability summary | ✓ brief | link to CURRENT-STATE/specs |
| Inspect-before-edit | — | ✓ |
| Approval-gated OpenSpec lifecycle | pointer only | ✓ full |
| Minimal implementation scope | — | ✓ |
| Python, API, filesystem standards | — | ✓ |
| Testing, warnings, security, Git, deploy | — | ✓ |
| Cursor response behavior | — | ✓ |
| Definition of done | — | ✓ |

**Project rule deduplication:** Replace the detailed "Engineering workflow" four-step block with a concise pointer to the engineering rule. Retain "OpenSpec before code" in Critical guardrails.

### D3: Both rules `alwaysApply: true`

Engineering standards must apply during inspect-only and docs-only tasks (no secrets in docs, qualified language). Project rule remains the first orientation layer.

### D4: Engineering rule authority class (locked)

`.cursor/rules/silverman-blog-linkedin-engineering.mdc` is **Cursor execution guidance**:

- automatically loaded (`alwaysApply: true`)
- subordinate to canonical OpenSpec specs, ADRs, and project context
- **not** normative product authority
- responsible for engineering behavior, approval discipline, and implementation quality

Normative requirements remain in `openspec/specs/`. The delta spec records the engineering rule as a repository governance artifact, not a product capability spec.

### D5: Line budget (locked)

| Parameter | Value |
|-----------|-------|
| Target length | 180–240 lines |
| Hard maximum | 280 lines |
| `alwaysApply` | `true` |

Reduce duplication by linking canonical documents rather than embedding volatile status or large capability inventories. Do not shorten by removing critical engineering constraints.

### D6: Do not modify `openspec/config.yaml` (locked)

The engineering rule is always applied in Cursor. OpenSpec already receives durable context through canonical documents, ADRs, and canonical specs. Injecting the engineering rule into OpenSpec would duplicate instructions and increase drift risk.

### D7: CONTEXT-AUTHORITY narrow update (locked)

Add to `docs/CONTEXT-AUTHORITY.md` (authority hierarchy table or dedicated subsection):

- `.cursor/rules/silverman-blog-linkedin-engineering.mdc` — automatically loaded Cursor execution guidance; subordinate to canonical specs and project context; not normative product authority; governs engineering behavior and approval discipline.

Do not embed the engineering rule's full contents. The project rule entry may be cross-referenced for orientation vs discipline.

### D8: Cursor skills command syntax (locked)

Bring `.cursor/skills/openspec-*/SKILL.md` into scope. Inspection results:

| Skill file | Colon syntax found | Expected action |
|------------|-------------------|-----------------|
| `openspec-propose/SKILL.md` | Yes — lines 19, 94 (`/opsx:apply`) | Narrow fix to `/opsx-apply` |
| `openspec-explore/SKILL.md` | Yes — line 203 (`/opsx:explore`) | Narrow fix to `/opsx-explore` |
| `openspec-apply-change/SKILL.md` | Yes — line 25 (`/opsx:apply`) | Narrow fix to `/opsx-apply` |
| `openspec-sync-specs/SKILL.md` | No | Inspect only; no change expected |
| `openspec-archive-change/SKILL.md` | No | Inspect only; no change expected |

Update only obsolete command syntax or workflow references. Preserve each skill's responsibility and procedure. Do not broadly rewrite skill content.

Canonical hyphenated commands: `/opsx-explore`, `/opsx-propose`, `/opsx-apply`, `/opsx-verify`, `/opsx-sync`, `/opsx-archive`.

### D9: Warning minimization without broad suppression

1. Aim for zero **new** warnings attributable to the change.
2. Fix root causes before completion.
3. Allow narrow suppressions only with inline explanation tied to a specific line/issue.
4. Forbid global disables, broad `per-file-ignores`, or tool-config changes to hide failures.
5. Report pre-existing unrelated warnings separately.

### D10: Anti-overengineering

- Default: smallest coherent diff satisfying approved requirements.
- Allow spec-mandated architecture (adapters, idempotency, auth middleware, lifecycle invariants).
- Forbid: speculative frameworks, generic wrappers, unrelated refactors, fallbacks hiding invalid state.

### D11: `/opsx-*` lifecycle alignment

```text
explore when needed
→ /opsx-propose
→ review proposal, design, delta specs, tasks
→ explicit user approval
→ /opsx-apply
→ implementation review
→ /opsx-verify
→ explicit commit approval
→ implementation commit
→ /opsx-sync
→ sync review
→ separate sync commit
→ /opsx-archive
→ archive review
→ separate archive commit
→ explicit push approval
→ explicit deployment approval
→ controlled operational validation
```

Hyphenated commands only. No apply on unapproved proposal. No sync before implementation commit. No archive before sync commit. Verification stale after any post-verify edit.

### D12: Engineering rule section outline

The implementation file MUST contain these H2 sections:

1. Canonical context and authority
2. Precise status language
3. Inspect before editing
4. Scope and anti-overengineering
5. Python standards
6. API and worker standards
7. Filesystem and lifecycle safety
8. External integration rules (ComfyUI, DeepSeek, LinkedIn, GitHub Pages, n8n)
9. Testing standards
10. Warning and quality discipline
11. Documentation and drift prevention
12. Security and secrets
13. Git discipline
14. Deployment and live-operation discipline
15. Cursor response behavior
16. Definition of done

Plus frontmatter and brief intro linking to the project rule.

### D13: File-action matrix (locked)

See `proposal.md` file-action matrix. Implementation MUST NOT modify files outside the matrix.

## Validation plan

At `/opsx-verify` after apply:

| Check | Method |
|-------|--------|
| OpenSpec strict validation | `openspec validate add-cursor-engineering-quality-rules --strict` |
| Frontmatter YAML parses | Both `.mdc` rules |
| `alwaysApply: true` | Both `.mdc` rules |
| Engineering rule line count | 180–240 target; never above 280 |
| Local links resolve | All markdown links in new/modified files |
| No `/opsx:` colon syntax | Grep active rules, commands, skills, current docs (exclude `openspec/changes/archive/`) |
| Lifecycle order consistent | Commands, skills, rules, CONTEXT-AUTHORITY |
| No duplicated complete lifecycle | Project rule has pointer only; engineering rule owns full lifecycle |
| No unqualified "Flow A complete" | Grep new/modified rule text |
| No broad warning suppressions | Grep new rule |
| No speculative abstractions or vague generic rules | Manual review |
| No secret values | Secrets audit on new/modified files |
| `git diff --check` | Pass |
| Exact-scope audit | Only matrix-approved files modified |
| Full pytest | Skip (docs/rules-only change) |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Prompt bloat from two always-on rules | 180–240 line target; link to docs; dedup project workflow |
| Duplication with user rules | Engineering rule is repo-specific; defers to project rule for editorial/purpose |
| Rule drift from specs | Delta spec + CONTEXT-AUTHORITY entry; verify links on rule changes |
| Skills drift after fix | Validation grep across active skills |

## Migration Plan

1. Create engineering rule (primary deliverable).
2. Update project rule cross-link and trim duplicated lifecycle.
3. Update CONTEXT-AUTHORITY narrow entry.
4. Fix skill colon syntax (3 files).
5. Verify per validation plan; `/opsx-verify`.
6. Commit implementation → sync delta spec → archive (separate commits per lifecycle).

No deployment or runtime migration. Cursor picks up new rule on next session.

## Unresolved questions

**0** — all decisions closed.
