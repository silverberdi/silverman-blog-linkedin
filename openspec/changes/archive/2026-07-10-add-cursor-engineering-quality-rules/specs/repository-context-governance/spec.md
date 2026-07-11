## MODIFIED Requirements

### Requirement: Canonical authority document

The repository MUST maintain `docs/CONTEXT-AUTHORITY.md` defining document authority hierarchy, document roles, conflict-resolution rules, handling of historical and archived artifacts, and canonical references for Cursor and OpenSpec. Canonical OpenSpec specs MUST be treated as normative requirements. Implementation and tests MUST be treated as evidence of real behavior. Neither layer MUST silently override a discrepancy; discrepancies MUST be resolved through a new OpenSpec change with divergence recorded in `docs/CURRENT-STATE.md`. Bootstrap context and archived changes MUST rank below canonical specs and CURRENT-STATE.

`docs/CONTEXT-AUTHORITY.md` MUST list `.cursor/rules/silverman-blog-linkedin-engineering.mdc` as automatically loaded Cursor execution guidance that is subordinate to canonical specs and project context, is not normative product authority, and governs engineering behavior and approval discipline. It MUST NOT embed the engineering rule's full contents.

#### Scenario: Conflict between bootstrap doc and spec

- **WHEN** a bootstrap context file disagrees with a canonical spec or current implementation
- **THEN** `docs/CONTEXT-AUTHORITY.md` instructs contributors to record the discrepancy in `docs/CURRENT-STATE.md` and resolve it through a new OpenSpec change rather than silent interpretation

#### Scenario: Archived change cited as requirement

- **WHEN** a proposal references an archived OpenSpec change as an active requirement or implementation instruction
- **THEN** `docs/CONTEXT-AUTHORITY.md` and OpenSpec injected context direct authors to canonical specs and `docs/CURRENT-STATE.md` instead

#### Scenario: Engineering rule authority documented

- **WHEN** a contributor or agent reads `docs/CONTEXT-AUTHORITY.md`
- **THEN** they find the engineering rule classified as Cursor execution guidance subordinate to canonical specs, not as normative product authority

### Requirement: Cursor always-on context alignment

The repository MUST maintain two complementary always-applied Cursor rules:

1. **Project context rule** at `.cursor/rules/silverman-blog-linkedin-project.mdc` — project identity and purpose; canonical document links (`docs/CURRENT-STATE.md`, `docs/CONTEXT-AUTHORITY.md`, `docs/GLOSSARY.md`); architecture and product boundaries; Flow A / Flow B semantics; high-level safety guardrails; editorial scope; brief worker capability summary; and a pointer to the engineering rule. It MUST NOT duplicate full CURRENT-STATE inventories, detailed engineering standards, or the complete OpenSpec lifecycle.

2. **Engineering quality rule** at `.cursor/rules/silverman-blog-linkedin-engineering.mdc` — Cursor execution guidance (not normative product authority) covering inspect-before-edit, approval-gated OpenSpec lifecycle, minimal implementation scope, Python/API/filesystem/testing/warning/security/Git/deployment standards, external integration boundaries, Cursor response behavior, full `/opsx-*` lifecycle with explicit approval gates, and definition of done. It MUST link to canonical docs rather than embed volatile status.

Both rules MUST set `alwaysApply: true` in valid YAML frontmatter. Neither rule MUST duplicate the other line-by-line. The project rule MUST link to the engineering rule. Archived OpenSpec changes MUST NOT be treated as active instructions in either rule.

#### Scenario: Agent loads project rule

- **WHEN** Cursor applies the silverman-blog-linkedin project rule
- **THEN** the agent is directed to canonical status and authority documents and to the engineering rule for implementation standards

#### Scenario: Agent implements a code change

- **WHEN** Cursor applies the engineering rule during `/opsx-apply`
- **THEN** the agent follows inspect-before-edit, minimal scope, warning hygiene, approval gates, and qualified completion language without requiring duplicate guardrails in the project rule

#### Scenario: Rule duplication audit

- **WHEN** both Cursor rules are reviewed together
- **THEN** purpose/editorial content lives primarily in the project rule and engineering discipline lives primarily in the engineering rule with cross-links instead of repeated prose

#### Scenario: Project rule lifecycle pointer

- **WHEN** the project rule references OpenSpec workflow
- **THEN** it provides a concise pointer to the engineering rule rather than duplicating the complete lifecycle

### Requirement: Cursor slash-command syntax alignment

Active Cursor skills under `.cursor/skills/openspec-*/SKILL.md` MUST use hyphenated `/opsx-*` command syntax consistent with `.cursor/commands/opsx-*.md`. Skills MUST NOT prescribe `/opsx:` colon variants as canonical syntax. Updates to skills MUST be narrow syntax fixes preserving each skill's responsibility and procedure.

#### Scenario: Skill command syntax audit

- **WHEN** an agent reads OpenSpec Cursor skills for workflow guidance
- **THEN** only hyphenated forms (`/opsx-explore`, `/opsx-propose`, `/opsx-apply`, `/opsx-verify`, `/opsx-sync`, `/opsx-archive`) appear as canonical command syntax

## ADDED Requirements

### Requirement: Cursor engineering quality rule

The repository MUST maintain `.cursor/rules/silverman-blog-linkedin-engineering.mdc` as an always-applied Cursor rule classified as **Cursor execution guidance**—subordinate to canonical OpenSpec specs, ADRs, and project context; not normative product authority. The rule MUST include valid YAML frontmatter with `description` and `alwaysApply: true`. The rule MUST target 180–240 lines and MUST NOT exceed 280 lines. The rule MUST NOT create `.cursorrules.md`. The rule MUST defer to canonical sources (`docs/CURRENT-STATE.md`, `docs/CONTEXT-AUTHORITY.md`, `docs/GLOSSARY.md`, `docs/RUNTIME-STATE.md` when live state matters, `openspec/specs/`, `src/`, `tests/`, accepted ADRs, existing project Cursor rules and commands) rather than embedding volatile project status.

The rule MUST include actionable sections covering at minimum:

1. Canonical context and authority (read before acting; specs normative; code/tests as evidence; resolve discrepancies via OpenSpec; archived changes historical only)
2. Precise status language (qualified Flow A layers; distinguish implemented/tested/deployed/validated/enabled/automatic/manual/incomplete/deferred/unknown; distinguish handoff vs Git commit vs push vs site live; LinkedIn implementation vs validation; n8n import vs unattended automation; `distribution_scheduled` vs `flow_a_complete`)
3. Inspect before editing (read file, callers, specs, tests; classify canonical/generated/operational/historical; check Git status; match conventions; do not invent paths/endpoints/env vars)
4. Scope and anti-overengineering (smallest coherent change; no unrelated refactors; no speculative abstractions; no broad suppressions; document neighbor issues as follow-ups)
5. Python standards (project constraints, typing on public APIs, pathlib, UTC timestamps, boundary validation, structured errors, dry-run immutability, no secret logging)
6. API and worker standards (HTTP-only n8n boundary; no Execute Command; auth/validation/idempotency/dry-run; no secret responses; no hidden Git operations)
7. Filesystem and lifecycle safety (path confinement, atomic writes, lifecycle invariants, no double moves, no false success metadata)
8. External integration rules (ComfyUI, DeepSeek, LinkedIn, GitHub Pages checkout, n8n — each with explicit enablement, dry-run, validation, and no duplicate external posts)
9. Testing standards (behavioral coverage matrix; deterministic fixtures; no real external calls in unit tests; no weakened assertions)
10. Warning and quality discipline (zero new attributable warnings; fix root causes; narrow suppressions only; `git diff --check`)
11. Documentation and drift prevention (update correct canonical doc when capability/topology/activation changes)
12. Security and secrets (never expose secret values; stage-time secrets audit)
13. Git discipline (explicit paths; three commit boundaries: implementation, spec sync, archive; no commit without approval)
14. Deployment and live-operation discipline (separate from implementation; explicit approval; controlled validation with evidence)
15. Cursor response behavior (inspect vs propose vs implement; stop when blocked; verify state not just exit codes)
16. Definition of done (scope, tests, warnings, verify, commit boundaries, sync, archive; completion does not imply deployment)

The rule MUST encode the approved engineering lifecycle using hyphenated commands only: `/opsx-explore`, `/opsx-propose`, `/opsx-apply`, `/opsx-verify`, `/opsx-sync`, `/opsx-archive`. It MUST state that post-verify modifications make verification stale and that commit, push, deploy, activation, publication, and live mutation require explicit approval.

#### Scenario: New engineering rule file created

- **WHEN** the change is applied
- **THEN** `.cursor/rules/silverman-blog-linkedin-engineering.mdc` exists with valid frontmatter, all required sections, and line count within 180–280 bounds

#### Scenario: Agent follows warning discipline

- **WHEN** an agent completes work under the engineering rule
- **THEN** it resolves new warnings from the change, avoids global suppression, and runs `git diff --check` before declaring done

#### Scenario: Agent uses precise status language

- **WHEN** the engineering rule guides status reporting
- **THEN** the agent does not use unqualified "Flow A complete" and distinguishes blog handoff from site published/live and LinkedIn implementation from operational validation

#### Scenario: Lifecycle command syntax

- **WHEN** the engineering rule documents OpenSpec workflow commands
- **THEN** only hyphenated `/opsx-*` forms appear as canonical syntax

### Requirement: Engineering rule validation contract

Changes that add or modify Cursor engineering rules MUST be verifiable without full application test suites unless executable code changes. Verification MUST include:

- `openspec validate <change> --strict`
- Cursor rule frontmatter validation for both `.mdc` rules (`description`, `alwaysApply: true`)
- Engineering rule line count: 180–240 target; never above 280
- Referenced path existence checks for all local links in new/modified files
- Comparison against `.cursor/rules/silverman-blog-linkedin-project.mdc` for duplication and conflict
- Grep audit for obsolete `/opsx:` colon syntax across active rules, commands, skills, and current documentation (excluding archived OpenSpec changes)
- Lifecycle order consistency across commands, skills, rules, and `docs/CONTEXT-AUTHORITY.md`
- Confirmation project and engineering rules do not both contain the complete lifecycle
- Grep audit for unqualified "Flow A complete" in new/modified rules
- Grep audit for broad warning suppression instructions
- Manual review for speculative abstractions or vague generic rules
- Secrets audit on new/modified rule and doc files
- `git diff --check`
- Exact-scope audit confirming only approved files were modified
- Confirmation `openspec/config.yaml` was not modified

#### Scenario: Verify engineering rule change

- **WHEN** `/opsx-verify add-cursor-engineering-quality-rules` runs after apply
- **THEN** strict OpenSpec validation passes and all rule-specific audits complete without requiring full `pytest` unless executable code changed
