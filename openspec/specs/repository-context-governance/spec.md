# repository-context-governance

## Purpose

Canonical governance for project context documents, authority hierarchy, Cursor/OpenSpec alignment, and drift prevention across `docs/CURRENT-STATE.md`, `docs/CONTEXT-AUTHORITY.md`, `docs/GLOSSARY.md`, `docs/RUNTIME-STATE.md`, and related workflow artifacts.

## Requirements

### Requirement: Canonical current-state document

The repository MUST maintain `docs/CURRENT-STATE.md` as the canonical source for project purpose, business goals, architecture summary, ownership matrix, implemented vs operationally validated vs manual vs incomplete vs deferred roadmap, `last_verified_at_utc`, known spec↔implementation divergences, and pointers to deployment topology. The document MUST distinguish Flow A core implementation from fully unattended Flow A production operation and MUST NOT use ambiguous "Flow A is complete" language without qualifying the completion layer. The document MAY record a last verified baseline revision (e.g., `88cd5bc` at `2026-07-10T00:00:00Z`) with timestamp and MUST NOT treat that SHA as a permanent runtime requirement.

#### Scenario: New session reads current status

- **WHEN** a contributor or Cursor agent opens `docs/CURRENT-STATE.md`
- **THEN** they find separated roadmap sections for operationally validated capabilities, implemented-but-not-validated items, manual steps, incomplete work, and deferred scope without contradicting canonical OpenSpec specs

#### Scenario: Known divergence recorded

- **WHEN** implementation behavior differs from a canonical spec requirement
- **THEN** `docs/CURRENT-STATE.md` records the divergence explicitly and directs resolution through a new OpenSpec change rather than silent interpretation

#### Scenario: Real operational evidence recorded

- **WHEN** `docs/CURRENT-STATE.md` documents Flow A validation
- **THEN** it cites verifiable evidence (e.g., campaign `flow_a_complete`, publication idempotency, calendar reconciliation) and states that public-blog Git commit/push and LinkedIn real API publication remain manual or unvalidated as applicable

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

### Requirement: Canonical glossary

The repository MUST maintain `docs/GLOSSARY.md` defining at minimum: Flow A, Flow A Core, `distribution_scheduled`, `flow_a_complete`, operational smoke pass, fully unattended Flow A, Flow B, `ready`/`queued`/`processed`/`error`, blog handoff, blog files written, blog Git publication, live-site confirmation, site published/live, LinkedIn publication states (`pending`, `queued`, `publishing`, `published`), active OpenSpec change, canonical spec, archived change, reconciliation, and idempotency.

#### Scenario: Campaign state vs product complete

- **WHEN** documentation uses `flow_a_complete`
- **THEN** `docs/GLOSSARY.md` defines it strictly as a campaign lifecycle metadata state and distinguishes it from fully unattended Flow A or site published/live

#### Scenario: Blog handoff vs publication layers

- **WHEN** documentation describes blog output or publication progress
- **THEN** `docs/GLOSSARY.md` separates worker file writes (blog handoff), guarded worker Git commit/push (`blog_git_publication`), optional worker HTTP live-site confirmation (`blog_live_site_publication`), and site published/live as public HTTP reachability

#### Scenario: Git push alone is not site published/live

- **WHEN** documentation describes a successful `blog_git_publication.status` `pushed` without live-site confirmation
- **THEN** `docs/GLOSSARY.md` states that Git push evidence alone MUST NOT be described as site published/live

#### Scenario: Confirmed site published/live

- **WHEN** documentation claims site published/live after US-002 validation
- **THEN** `docs/GLOSSARY.md` defines site published/live as public HTTP reachability that MAY be recorded by `blog_live_site_publication.status` `confirmed` (when enabled, opted in, and operationally validated) or by operator manual verification

#### Scenario: LinkedIn implementation vs API validation

- **WHEN** documentation describes LinkedIn capabilities
- **THEN** `docs/GLOSSARY.md` distinguishes implemented package/scheduling support from operationally validated real LinkedIn API publication

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

### Requirement: OpenSpec injected context alignment

`openspec/config.yaml` injected context MUST describe the post-Flow-A-core state, reference canonical context documents explicitly (`docs/CURRENT-STATE.md`, `docs/CONTEXT-AUTHORITY.md`, `docs/GLOSSARY.md`, accepted ADRs, canonical specs), state authority semantics and implemented/manual/incomplete distinctions, encode the engineering lifecycle and hyphenated slash-command names, and MUST NOT assert obsolete Phase 1 exclusions for capabilities already implemented. It MUST NOT inject all of `docs/context/` or all workflow documents as current context. Bootstrap and historical documents MUST be clearly lower authority.

#### Scenario: New OpenSpec proposal starts

- **WHEN** `openspec instructions` supplies project context for a new change
- **THEN** the context reflects current capabilities and warns against assuming automated Git push, LinkedIn real API publication, or unattended n8n automation

### Requirement: Historical document marking

Bootstrap and superseded context files that retain historical rationale MUST carry a prominent historical/bootstrap banner at the top pointing to canonical documents. Files MUST NOT present stale Phase 0/1 delivery status as current without the banner.

#### Scenario: Reader opens backlog-and-phasing

- **WHEN** a contributor opens `docs/context/backlog-and-phasing.md`
- **THEN** a visible banner indicates the file is historical/bootstrap and links to `docs/CURRENT-STATE.md` for current roadmap

### Requirement: Context drift prevention

When an approved change modifies capability implementation status, runtime topology, activation state, completion criteria, ownership boundaries, OpenSpec workflow, deployment procedures, or external integration readiness, the same change (or an immediate follow-up documentation change) MUST update `docs/CURRENT-STATE.md` and, when present, `docs/RUNTIME-STATE.md`.

#### Scenario: Capability becomes operationally validated

- **WHEN** a change completes operational validation of a previously unvalidated capability
- **THEN** `docs/CURRENT-STATE.md` roadmap sections are updated to reflect the new validation status with a `last_verified_at_utc` timestamp

### Requirement: Engineering command syntax standardization

Repository documentation MUST use hyphenated Cursor slash commands matching `.cursor/commands/opsx-*.md` filenames (`/opsx-propose`, `/opsx-apply`, `/opsx-sync`, `/opsx-archive`, `/opsx-explore`, `/opsx-verify`). Documentation MUST NOT prescribe unsupported colon variants (e.g., `/opsx:propose`) as canonical.

#### Scenario: Workflow documentation lists commands

- **WHEN** engineering workflow is documented in CONTEXT-AUTHORITY or OpenSpec config
- **THEN** command names match installed `.cursor/commands/` wrappers

### Requirement: Verification command wrapper

The repository MUST provide `.cursor/commands/opsx-verify.md` as a project-specific Cursor command wrapper (not a native OpenSpec CLI command). The wrapper MUST invoke `openspec validate <change-name> --strict`, inspect artifact and task completion, run change-required tests, assess spec-to-implementation traceability, detect modifications after a prior verification, state that any code or artifact modification makes a previous verification stale, follow the repository commit → sync → archive sequence, and NEVER recommend archive before approved implementation and sync commits.

#### Scenario: Operator verifies change before commit

- **WHEN** an operator runs `/opsx-verify align-project-context-and-current-state`
- **THEN** the wrapper runs strict validation and reports artifact/task completion status before recommending commit

#### Scenario: Post-verification modification

- **WHEN** any artifact or code file is modified after a successful verification
- **THEN** the wrapper reports the prior verification as stale and requires re-verification

### Requirement: Runtime state manifest separation

`docs/RUNTIME-STATE.md` MUST be a volatile point-in-time operational snapshot, NOT architectural authority. It MUST include `verified_at_utc`, evidence source per fact, and `unknown` for unverified facts. It MUST NOT contain secrets. It MUST be updated after deploys, activation changes, real smoke tests, external-integration validation, or confirmed deployed-revision changes. It MUST NOT be injected indiscriminately into every OpenSpec proposal and MUST be consulted only when live operational state is relevant.

#### Scenario: Reader consults runtime flags

- **WHEN** a contributor needs current LinkedIn publication guard status
- **THEN** they consult `docs/RUNTIME-STATE.md` or live verification, not ADRs or archived operations records

### Requirement: Workflow document split

The repository MUST split mixed workflow responsibilities from `docs/workflows/phase-1-target-flow.md` into `docs/workflows/flow-a-target-flow.md` (Flow A automation) and `docs/workflows/linkedin-draft-review-flow.md` (human LinkedIn review). `docs/workflows/phase-1-target-flow.md` MUST become a historical compatibility stub explaining the split and linking both current documents.

#### Scenario: Reader follows old workflow link

- **WHEN** a contributor opens `docs/workflows/phase-1-target-flow.md`
- **THEN** they see a compatibility stub directing them to the split documents

### Requirement: Executable script scope boundary

Context governance changes MUST NOT modify executable defaults, logic, or expected-commit behavior in `scripts/flow_a_readiness.py`. Documentation, comments, and help text MAY be corrected. Updates to `DEFAULT_EXPECTED_COMMITS` MUST be performed only via a dedicated OpenSpec change scoped to Flow A readiness defaults (for example `correct-stale-flow-a-readiness-defaults`), not incidental context-alignment work.

#### Scenario: Readiness script defaults reviewed during context governance

- **WHEN** a context-governance-only change is applied
- **THEN** `scripts/flow_a_readiness.py` executable defaults and expected-commit behavior are unchanged

#### Scenario: Readiness defaults updated by dedicated change

- **WHEN** change `correct-stale-flow-a-readiness-defaults` is applied and synced
- **THEN** `DEFAULT_EXPECTED_COMMITS` reflects the documented operational baseline, the known-divergence row for stale defaults is removed from `docs/CURRENT-STATE.md`, and operator docs describe the new milestones

### Requirement: Anti-pattern prevention in canonical context

Canonical context documents MUST prevent: archived changes treated as active instructions; unqualified "Flow A complete" language; worker checkout writes described as site published/live; implemented LinkedIn support described as operationally validated API publication; and n8n workflow existence described as unattended automation.

#### Scenario: New proposal author reads CURRENT-STATE

- **WHEN** a contributor assesses Flow A completion status
- **THEN** they find qualified completion layers distinguishing campaign lifecycle, core validation, unattended operation, blog handoff, and site publication
