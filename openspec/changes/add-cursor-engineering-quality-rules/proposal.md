## Why

The existing always-on Cursor project rule (`.cursor/rules/silverman-blog-linkedin-project.mdc`) correctly orients agents to canonical context, architecture guardrails, and a high-level OpenSpec workflow, but it does not encode the repository's engineering quality standards: inspect-before-edit discipline, minimal scope, warning hygiene, Python/API/filesystem/testing conventions, integration safety boundaries, Git/deploy approval gates, or the full Cursor + OpenSpec lifecycle with explicit approval checkpoints. Without a dedicated engineering rule, Cursor sessions tend to over-scope changes, suppress warnings, blur completion layers (handoff vs publication, implementation vs validation), or skip verification steps—especially when implementing across worker, filesystem, and external integrations.

Stale `/opsx:` colon syntax in three OpenSpec Cursor skills undermines lifecycle consistency across commands, skills, rules, and current documentation.

## Goals

- Add `.cursor/rules/silverman-blog-linkedin-engineering.mdc` as concise, actionable, always-applied engineering guidance (180–240 lines target; 280 hard maximum).
- Complement (not duplicate) `.cursor/rules/silverman-blog-linkedin-project.mdc` with a locked ownership split.
- Classify the engineering rule as **Cursor execution guidance**, subordinate to canonical specs and project context—not normative product authority.
- Encode the full engineering lifecycle with explicit approval gates and hyphenated `/opsx-*` commands.
- Encode precise status language, scope discipline, warning minimization without broad suppression, and stop-when-blocked behavior.
- Update `docs/CONTEXT-AUTHORITY.md` with a narrow entry for the engineering rule's authority role.
- Align OpenSpec Cursor skills with hyphenated command syntax where inspection finds obsolete colon forms.
- Update `repository-context-governance` canonical requirements to cover the new engineering rule, rule split, and validation contract.

## Non-Goals

- Modifying `openspec/config.yaml` — the engineering rule is `alwaysApply: true`; OpenSpec already receives durable context through canonical documents, ADRs, and canonical specs; injecting the rule into OpenSpec would duplicate instructions and increase drift risk.
- Changing application behavior, endpoints, Flow A logic, LinkedIn/ComfyUI/n8n/GitHub Pages runtime behavior.
- Adding linters, formatters, CI changes, Python dependency changes, or deployment script changes.
- Activating external integrations or modifying live server state.
- Rewriting `docs/CURRENT-STATE.md` or embedding volatile project status in rules.
- Creating `.cursorrules.md` or splitting into many always-on rules without evidence of bloat failure.
- Rewriting archived OpenSpec changes or historical examples.

## What Changes

### File-action matrix

| Action | Path | Notes |
|--------|------|-------|
| **Create** | `.cursor/rules/silverman-blog-linkedin-engineering.mdc` | Primary deliverable; `alwaysApply: true`; 180–240 line target; ≤280 hard max |
| **Substantive update** | `.cursor/rules/silverman-blog-linkedin-project.mdc` | Cross-link to engineering rule; replace duplicated detailed lifecycle with concise pointer |
| **Substantive update** | `docs/CONTEXT-AUTHORITY.md` | Narrow entry: engineering rule as auto-loaded Cursor execution guidance, subordinate to canonical specs |
| **Conditional narrow update** | `.cursor/skills/openspec-propose/SKILL.md` | **Expected change** — 2 obsolete `/opsx:` references |
| **Conditional narrow update** | `.cursor/skills/openspec-explore/SKILL.md` | **Expected change** — 1 obsolete `/opsx:` reference in example |
| **Conditional narrow update** | `.cursor/skills/openspec-apply-change/SKILL.md` | **Expected change** — 1 obsolete `/opsx:` reference |
| **Conditional narrow update** | `.cursor/skills/openspec-sync-specs/SKILL.md` | Inspect only — no colon syntax found; expected no change |
| **Conditional narrow update** | `.cursor/skills/openspec-archive-change/SKILL.md` | Inspect only — no colon syntax found; expected no change |
| **No change** | `openspec/config.yaml` | Closed decision: do not modify |
| **No change** | Application source, tests, CI, deployment, runtime data | Out of scope |
| **No change** | Canonical functional specs unrelated to `repository-context-governance` | Sync applies only this capability's delta |
| **No change** | Archived OpenSpec changes | Historical only |

### Capability delta

- **Modified capability:** `repository-context-governance` — engineering-rule requirement; modified Cursor always-on context alignment; engineering-rule validation contract; CONTEXT-AUTHORITY engineering-rule entry.

## Rule ownership split (locked)

| Concern | Project rule | Engineering rule |
|---------|--------------|------------------|
| Project identity and purpose | ✓ | link only |
| Canonical context links | ✓ primary | ✓ before acting |
| Architecture and product boundaries | ✓ brief | ✓ enforce in edits |
| Flow A / Flow B semantics | ✓ qualified language | ✓ precise status language |
| High-level safety guardrails | ✓ | cross-reference |
| Inspect-before-edit behavior | — | ✓ |
| Approval-gated OpenSpec lifecycle | pointer only | ✓ full |
| Minimal implementation scope | — | ✓ |
| Python, API, filesystem standards | — | ✓ |
| Testing | — | ✓ |
| Warning discipline | — | ✓ |
| Security | — | ✓ |
| Git | — | ✓ |
| Deployment and live operations | — | ✓ |
| Response behavior | — | ✓ |
| Definition of done | — | ✓ |

The project rule MUST NOT retain a duplicated detailed engineering lifecycle. Replace it with a concise pointer to the engineering rule.

## Engineering rule parameters (locked)

- **Target length:** 180–240 lines
- **Hard maximum:** 280 lines
- **Frontmatter:** `alwaysApply: true`, valid YAML with `description`
- **Authority class:** Cursor execution guidance; subordinate to canonical specs, ADRs, and project context; not normative product authority

## `openspec/config.yaml` decision (locked)

Do **not** modify `openspec/config.yaml` in this change. Rationale: the engineering rule is always applied in Cursor; OpenSpec already receives durable context through canonical documents, ADRs, and canonical specs; injecting the rule into OpenSpec would duplicate instructions and increase drift risk.

## CONTEXT-AUTHORITY update (locked)

Add a narrowly scoped section or table entry to `docs/CONTEXT-AUTHORITY.md` listing `.cursor/rules/silverman-blog-linkedin-engineering.mdc` as:

- automatically loaded Cursor execution guidance
- subordinate to canonical specs and project context
- not normative product authority
- responsible for engineering behavior and approval discipline

Do not embed the engineering rule's full contents in CONTEXT-AUTHORITY.

## Impact

- **Files:** See file-action matrix above.
- **Consumers:** Cursor agents in all sessions; no runtime worker impact.
- **Verification:** See design.md validation plan and tasks.md section 4.

## Unresolved questions

**0** — all decisions closed. Await explicit approval before `/opsx-apply`.
